# -*- coding: utf-8 -*-
import os
import json
import glob
import re
import shutil
from pathlib import Path
import numpy as np
import pyvista as pv
import vtk
from scipy.spatial import KDTree

# =============================================================================
# Portable case configuration. Numerical processing below is unchanged.
# =============================================================================
# Frozen v0.1 reference processor, kept only for regression tests.
# Usage: python legacy/v0_1/<case>.py <case_root>   (reads <case_root>/input,
# writes <case_root>/output/model_cache).  Numerical code below is unchanged.
import sys
CASE_ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(Path(__file__).resolve().parent))
from geosimvis.field_contract import attach_source_ids, prepare_output, public_field
INPUT_DIR = str(CASE_ROOT / "input")
WEB_PUBLIC_DIR = str(CASE_ROOT / "output")
CACHE_FOLDER_NAME = "model_cache"
SLICE_STEP = 10     # Default section spacing; reduced for spans at most twice this spacing
EPS = 1e-6          # Tolerance for zero-stress detection
# =============================================================================

OUTPUT_DIR = os.path.join(WEB_PUBLIC_DIR, CACHE_FOLDER_NAME)

class GeotechnicalAdvancedProcessor:
    def __init__(self):
        self.publication_ranges = {}
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        print(f"Input directory: {os.path.abspath(INPUT_DIR if os.path.exists(INPUT_DIR) else '.')}")
        print(f"Output directory: {OUTPUT_DIR}")
        
    def precalculate_fields(self, mesh):
        """Compute displacement components and principal stresses for 3DEC/FLAC3D."""
        
        # 1. Encode material/group fields as IDs (group, material, block, region, slot)
        for k in list(mesh.cell_data.keys()):
            if mesh.cell_data[k].dtype.kind in {'U', 'S', 'O'} or any(
                x in k.lower() for x in ['group', 'material', 'state', 'plastic', 'block', 'region', 'zone', 'slot']
            ):
                unique_vals, indices = np.unique(mesh.cell_data[k], return_inverse=True)
                mesh.cell_data[f"{k}_ID"] = indices

        # 2. Process displacement (usually PointData in 3DEC)
        disp_key = next((k for k in mesh.point_data.keys() if 'dis' in k.lower()), None)
        if not disp_key:
            disp_key = next((k for k in mesh.cell_data.keys() if 'dis' in k.lower()), None)
            
        if disp_key:
            container = mesh.point_data if disp_key in mesh.point_data else mesh.cell_data
            data = container[disp_key]
            container['TotalDisplacement'] = np.linalg.norm(data, axis=1)
            container['X_Disp'] = data[:, 0]
            container['Y_Disp'] = data[:, 1]
            container['Z_Disp'] = data[:, 2]

        # 3. Compute principal stresses from 3DEC/FLAC3D stress tensors
        stress_key = next((k for k in mesh.cell_data.keys() if any(x in k.lower() for x in ['stress', 'sig'])), None)
        if not stress_key:
            stress_key = next((k for k in mesh.point_data.keys() if any(x in k.lower() for x in ['stress', 'sig'])), None)

        if stress_key:
            container = mesh.cell_data if stress_key in mesh.cell_data else mesh.point_data
            s = container[stress_key]
            if s.ndim == 2:
                # Extract normal stress components
                if s.shape[1] >= 3:
                    container["Stress_XX"] = s[:, 0]
                    container["Stress_YY"] = s[:, 1]
                    container["Stress_ZZ"] = s[:, 2]
                
                # Compute eigenvalues using component order XX, YY, ZZ, XY, XZ, YZ
                if s.shape[1] >= 6:
                    N = s.shape[0]
                    tensor = np.zeros((N, 3, 3))
                    tensor[:, 0, 0], tensor[:, 1, 1], tensor[:, 2, 2] = s[:, 0], s[:, 1], s[:, 2]
                    tensor[:, 0, 1] = tensor[:, 1, 0] = s[:, 3]  # XY
                    tensor[:, 0, 2] = tensor[:, 2, 0] = s[:, 4]  # XZ
                    tensor[:, 1, 2] = tensor[:, 2, 1] = s[:, 5]  # YZ
                    
                    eigvals = np.linalg.eigvalsh(tensor)
                    container["Stress_Min_Principal"] = eigvals[:, 0]
                    container["Stress_Mid_Principal"] = eigvals[:, 1]
                    container["Stress_Max_Principal"] = eigvals[:, 2]
        return mesh

    def optimize_and_save(self, mesh, out_path):
        """Store Float32 VTP data with VTK level-9 Zlib compression."""
        keep_fields = [
            'TotalDisplacement', 'X_Disp', 'Y_Disp', 'Z_Disp',
            'Stress_XX', 'Stress_YY', 'Stress_ZZ', 
            'Stress_Max_Principal', 'Stress_Mid_Principal', 'Stress_Min_Principal'
        ]
        
        # Remove unused fields
        for container in [mesh.point_data, mesh.cell_data]:
            for k in list(container.keys()):
                if k not in keep_fields and not any(
                    x in k.lower() for x in ['id', 'group', 'material', 'state', 'plastic', 'block', 'region', 'slot']
                ):
                    del container[k]

        # Convert floating-point arrays to Float32 to reduce storage size
        mesh.points = np.asarray(mesh.points, dtype=np.float32)
        for container in [mesh.point_data, mesh.cell_data]:
            for k in list(container.keys()):
                if container[k].dtype == np.float64:
                    container[k] = container[k].astype(np.float32)

        writer = vtk.vtkXMLPolyDataWriter()
        prepare_output(mesh, out_path, self.publication_ranges)
        writer.SetFileName(out_path)
        writer.SetInputData(mesh)
        writer.SetDataModeToAppended()    
        writer.SetCompressorTypeToZLib()  
        writer.SetCompressionLevel(9)     
        writer.Write()

    def process_file(self, filename):
        print(f"\nReading 3DEC/FLAC3D model: {filename}")
        mesh = pv.read(filename)
        
        base_name = os.path.splitext(os.path.basename(filename))[0]
        out_dir = os.path.join(OUTPUT_DIR, base_name)
        
        if os.path.exists(out_dir): 
            shutil.rmtree(out_dir)
        os.makedirs(out_dir, exist_ok=True)

        # 1. Compute physical fields
        mesh = self.precalculate_fields(mesh)
        attach_source_ids(mesh)

        # 2. Identify cavity cells from group labels or FLAC3D zero-stress values
        cell_null = np.zeros(mesh.n_cells, dtype=bool)
        for k in mesh.cell_data.keys():
            if any(x in k.lower() for x in ['group', 'material', 'block', 'region', 'state', 'slot']):
                vals = mesh.cell_data[k].astype(str)
                cell_null |= np.char.find(np.char.lower(vals), 'null') >= 0
                cell_null |= np.char.find(np.char.lower(vals), 'excavated') >= 0

        if not np.any(cell_null):
            stress_key = next((k for k in mesh.cell_data.keys() if any(x in k.lower() for x in ['stress', 'sig'])), None)
            if stress_key:
                cell_null = np.all(np.abs(mesh.cell_data[stress_key]) < EPS, axis=1)

        print(f"  Model scan complete; cavity cells: {np.sum(cell_null)} (excavated/void).")

        solid_mesh = mesh.extract_cells(~cell_null)
        null_mesh = mesh.extract_cells(cell_null)

        # 3. Extract the excavation interface
        cavity_surface = None
        if null_mesh.n_cells > 0:
            print("  Cavity cells detected; extracting the contact boundary...")
            solid_surf = solid_mesh.cell_data_to_point_data(pass_cell_data=True).extract_surface()
            null_surf = null_mesh.extract_surface()
            tree = KDTree(null_surf.points)
            dists, _ = tree.query(solid_surf.points)
            cavity_surface = solid_surf.extract_points(dists < 1e-3).extract_surface().clean()
            self.optimize_and_save(cavity_surface, os.path.join(out_dir, "cavity_surface.vtp"))

        # 4. Locate the group field
        material_key = next((k for k in solid_mesh.cell_data.keys() if any(
            x in k.lower() for x in ['material', 'group', 'slot', 'block', 'region']
        )), None)
        
        if not material_key:
            solid_mesh.cell_data["Material_ID"] = np.zeros(solid_mesh.n_cells, dtype=int)
            material_key = "Material_ID"
        else:
            if not material_key.endswith("_ID") and f"{material_key}_ID" in solid_mesh.cell_data:
                material_key = f"{material_key}_ID"
        
        mat_data = solid_mesh.cell_data[material_key]
        mat_ids = np.unique(mat_data)

        # 5. Extract solid-group surfaces
        print("  Extracting solid-group surfaces...")
        full_surface_parts = []
        for mid in mat_ids:
            sub_block = solid_mesh.extract_cells(mat_data == mid)
            if sub_block.n_cells > 0:
                surf_part = sub_block.cell_data_to_point_data(pass_cell_data=True).extract_surface()
                full_surface_parts.append(surf_part)
                
        final_full_surface = pv.merge(full_surface_parts, merge_points=False)
        self.optimize_and_save(final_full_surface, os.path.join(out_dir, "full_model.vtp"))

        # 6. Generate sections with model-bound-aware spacing
        print("  Generating sections...")
        b = solid_mesh.bounds  # [xmin, xmax, ymin, ymax, zmin, zmax]
        
        def get_slice_locs(min_val, max_val, default_step):
            span = max_val - min_val
            if span <= 0:
                return []
            # Reduce spacing for small model spans
            step = default_step if span > default_step * 2 else max(span / 10.0, 0.1)
            return np.arange(min_val + step, max_val, step)

        locs = {
            'x': get_slice_locs(b[0], b[1], SLICE_STEP),
            'y': get_slice_locs(b[2], b[3], SLICE_STEP),
            'z': get_slice_locs(b[4], b[5], SLICE_STEP)
        }

        slice_paths = {'x': [], 'y': [], 'z': []}
        base_rel_path = f"{CACHE_FOLDER_NAME}/{base_name}"

        solid_blocks = []
        for mid in mat_ids:
            block = solid_mesh.extract_cells(mat_data == mid)
            if block.n_cells > 0:
                # Map point and cell fields before slicing
                solid_blocks.append(block.cell_data_to_point_data(pass_cell_data=True))

        for axis, values in locs.items():
            for val in values:
                origin = [val if axis == 'x' else 0, val if axis == 'y' else 0, val if axis == 'z' else 0]
                parts = []
                for block in solid_blocks:
                    p = block.slice(normal=axis, origin=origin)
                    if p.n_points > 0:
                        parts.append(p)
                        
                if parts:
                    final_slice = pv.merge(parts, merge_points=False).clean()
                    slice_name = f"slice_{axis}_{float(val):.2f}.vtp"
                    out_path = os.path.join(out_dir, slice_name)
                    
                    self.optimize_and_save(final_slice, out_path)
                    slice_paths[axis].append(f"{base_rel_path}/{slice_name}")

        # 7. Collect scalar fields and their global min/max ranges
        fields_info = {}
        for container in [final_full_surface.point_data, final_full_surface.cell_data]:
            for k, v in container.items():
                if v.ndim == 1 and np.issubdtype(v.dtype, np.number) and public_field(k):
                    # Exclude internal VTK fields
                    if k in ['vtkOriginalCellIds', 'vtkOriginalPointIds']:
                        continue
                    v_min = float(np.nanmin(v))
                    v_max = float(np.nanmax(v))
                    
                    if k in fields_info:
                        fields_info[k]["min"] = min(fields_info[k]["min"], v_min)
                        fields_info[k]["max"] = max(fields_info[k]["max"], v_max)
                    else:
                        fields_info[k] = {"min": v_min, "max": v_max}

        print(f"  Processing complete; sections generated: {sum(len(v) for v in slice_paths.values())} .")
        return {
            "full": f"{base_rel_path}/full_model.vtp",
            "cavity": f"{base_rel_path}/cavity_surface.vtp" if cavity_surface else None,
            "slices": slice_paths,
            "fields": {k: {"min": r[0], "max": r[1]} for k, r in self.publication_ranges.items()},
            "global_ranges": self.publication_ranges
        }

    def run(self):
        target_dir = INPUT_DIR if (INPUT_DIR and os.path.exists(INPUT_DIR)) else "."
        search_pattern = os.path.join(target_dir, "*.vtu")
        vtu_files = glob.glob(search_pattern)
        
        if not vtu_files:
            print(f"No VTU models found in [{os.path.abspath(target_dir)}].")
            return
            
        def sort_key(s):
            match = re.search(r'\d+', os.path.basename(s))
            return int(match.group()) if match else 0
            
        vtu_files = sorted(vtu_files, key=sort_key)
            
        stages_data = {}
        stage_order = []
        for fp in vtu_files:
            res = self.process_file(fp)
            if res:
                base_name = os.path.splitext(os.path.basename(fp))[0]
                stages_data[base_name] = res
                stage_order.append(base_name)

        index_data = {
            "DefaultModel": {
                "stages": stages_data,
                "stage_order": stage_order
            }
        }

        with open(os.path.join(OUTPUT_DIR, "index.json"), "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        print("\n3DEC/FLAC3D section and scalar-range extraction complete.")

if __name__ == "__main__":
    processor = GeotechnicalAdvancedProcessor()
    processor.run()
