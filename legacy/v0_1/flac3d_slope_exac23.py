# -*- coding: utf-8 -*-
import os
import json
import glob
from pathlib import Path
import numpy as np
import pyvista as pv
import vtk  # Native VTK writer for Zlib compression
import shutil
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
SLICE_STEP = 10
EPS = 1e-8
# =============================================================================

OUTPUT_DIR = os.path.join(WEB_PUBLIC_DIR, CACHE_FOLDER_NAME)

class GeotechnicalAdvancedProcessor:
    def __init__(self):
        self.publication_ranges = {}
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        print(f"Input directory: {os.path.abspath(INPUT_DIR if os.path.exists(INPUT_DIR) else '.')}")
        print(f"Output directory: {OUTPUT_DIR}")
        
    def precalculate_fields(self, mesh):
        """Compute displacement components and principal stresses."""
        # 1. Encode material and plastic-state groups as numeric IDs
        for k in list(mesh.cell_data.keys()):
            if mesh.cell_data[k].dtype.kind in {'U', 'S', 'O'} or any(x in k.lower() for x in ['group', 'material', 'state', 'plastic']):
                unique_vals, indices = np.unique(mesh.cell_data[k], return_inverse=True)
                mesh.cell_data[f"{k}_ID"] = indices

        # 2. Process displacement from point or cell data
        disp_key = next((k for k in mesh.point_data.keys() if 'dis' in k.lower()), None)
        if not disp_key:
            disp_key = next((k for k in mesh.cell_data.keys() if 'dis' in k.lower()), None)
            
        if disp_key:
            data = mesh.point_data[disp_key] if disp_key in mesh.point_data else mesh.cell_data[disp_key]
            target = mesh.point_data if disp_key in mesh.point_data else mesh.cell_data
            target['TotalDisplacement'] = np.linalg.norm(data, axis=1)
            target['X_Disp'], target['Y_Disp'], target['Z_Disp'] = data.T

        # 3. Compute stress tensor eigenvalues
        stress_key = next((k for k in mesh.cell_data.keys() if any(x in k.lower() for x in ['stress', 'sig'])), None)
        if not stress_key:
            stress_key = next((k for k in mesh.point_data.keys() if any(x in k.lower() for x in ['stress', 'sig'])), None)

        if stress_key:
            container = mesh.cell_data if stress_key in mesh.cell_data else mesh.point_data
            s = container[stress_key]
            if s.ndim == 2:
                if s.shape[1] >= 3:
                    container["Stress_XX"] = s[:, 0]
                    container["Stress_YY"] = s[:, 1]
                    container["Stress_ZZ"] = s[:, 2]
                if s.shape[1] >= 6:
                    N = s.shape[0]
                    tensor = np.zeros((N, 3, 3))
                    tensor[:, 0, 0], tensor[:, 1, 1], tensor[:, 2, 2] = s[:, 0], s[:, 1], s[:, 2]
                    tensor[:, 0, 1] = tensor[:, 1, 0] = s[:, 3]
                    tensor[:, 1, 2] = tensor[:, 2, 1] = s[:, 4]
                    tensor[:, 0, 2] = tensor[:, 2, 0] = s[:, 5]
                    eigvals = np.linalg.eigvalsh(tensor)
                    container["Stress_Min_Principal"] = eigvals[:, 0]
                    container["Stress_Mid_Principal"] = eigvals[:, 1]
                    container["Stress_Max_Principal"] = eigvals[:, 2]
        return mesh

    def optimize_and_save(self, mesh, out_path):
        """Store Float32 data with VTK level-9 Zlib compression."""
        keep_fields = [
            'TotalDisplacement', 'X_Disp', 'Y_Disp', 'Z_Disp',
            'Stress_XX', 'Stress_YY', 'Stress_ZZ', 
            'Stress_Max_Principal', 'Stress_Mid_Principal', 'Stress_Min_Principal'
        ]
        for k in list(mesh.point_data.keys()):
            if k not in keep_fields and not any(x in k.lower() for x in ['id', 'group', 'material', 'state', 'plastic']):
                del mesh.point_data[k]
        for k in list(mesh.cell_data.keys()):
            if k not in keep_fields and not any(x in k.lower() for x in ['id', 'group', 'material', 'state', 'plastic']):
                del mesh.cell_data[k]

        mesh.points = np.asarray(mesh.points, dtype=np.float32)
        for k in list(mesh.point_data.keys()):
            if mesh.point_data[k].dtype == np.float64:
                mesh.point_data[k] = mesh.point_data[k].astype(np.float32)
        for k in list(mesh.cell_data.keys()):
            if mesh.cell_data[k].dtype == np.float64:
                mesh.cell_data[k] = mesh.cell_data[k].astype(np.float32)

        writer = vtk.vtkXMLPolyDataWriter()
        prepare_output(mesh, out_path, self.publication_ranges)
        writer.SetFileName(out_path)
        writer.SetInputData(mesh)
        writer.SetDataModeToAppended()    
        writer.SetCompressorTypeToZLib()  
        writer.SetCompressionLevel(9)     
        writer.Write()

    def process_file(self, filename):
        print(f"\nReading model: {filename}")
        mesh = pv.read(filename)
        
        # Use the input basename to avoid unintended nested output folders
        base_name = os.path.splitext(os.path.basename(filename))[0]
        out_dir = os.path.join(OUTPUT_DIR, base_name)
        
        if os.path.exists(out_dir): 
            shutil.rmtree(out_dir)
        os.makedirs(out_dir, exist_ok=True)

        # 1. Compute physical fields
        mesh = self.precalculate_fields(mesh)
        attach_source_ids(mesh)

        # 2. Identify null cells using the FLAC3D zero-stress convention
        stress_key = next((k for k in mesh.cell_data.keys() if any(x in k.lower() for x in ['stress', 'sig'])), None)
        if stress_key:
            cell_null = np.all(np.abs(mesh.cell_data[stress_key]) < EPS, axis=1)
            print(f"  FLAC3D scan complete; cavity cells: {np.sum(cell_null)} (excavated).")
        else:
            cell_null = np.zeros(mesh.n_cells, dtype=bool)

        # Separate solid and void meshes
        solid_mesh = mesh.extract_cells(~cell_null)
        null_mesh = mesh.extract_cells(cell_null)

        # 3. Extract the excavation interface layer
        cavity_surface = None
        if null_mesh.n_cells > 0:
            print("  Cavity cells detected; extracting the contact boundary...")
            solid_surf = solid_mesh.cell_data_to_point_data(pass_cell_data=True).extract_surface()
            null_surf = null_mesh.extract_surface()
            tree = KDTree(null_surf.points)
            dists, _ = tree.query(solid_surf.points)
            # Expand solid point candidates within 1 mm of void points to incident faces
            cavity_surface = solid_surf.extract_points(dists < 1e-3).extract_surface().clean()
            self.optimize_and_save(cavity_surface, os.path.join(out_dir, "cavity_surface.vtp"))

        # 4. Locate the material/group field
        material_key = next((k for k in solid_mesh.cell_data.keys() if any(x in k.lower() for x in ['material', 'group', 'slot'])), None)
        if not material_key:
            solid_mesh.cell_data["Material_ID"] = np.zeros(solid_mesh.n_cells, dtype=int)
            material_key = "Material_ID"
        else:
            if not material_key.endswith("_ID") and f"{material_key}_ID" in solid_mesh.cell_data:
                material_key = f"{material_key}_ID"
        
        mat_data = solid_mesh.cell_data[material_key]
        mat_ids = np.unique(mat_data)

        # 5. Extract solid-group surfaces without merging vertices between groups
        print("  Extracting solid-group surfaces...")
        full_surface_parts = []
        for mid in mat_ids:
            sub_block = solid_mesh.extract_cells(mat_data == mid)
            if sub_block.n_cells > 0:
                surf_part = sub_block.cell_data_to_point_data(pass_cell_data=True).extract_surface()
                full_surface_parts.append(surf_part)
                
        final_full_surface = pv.merge(full_surface_parts, merge_points=False)
        self.optimize_and_save(final_full_surface, os.path.join(out_dir, "full_model.vtp"))

        # 6. Generate sections separately for each solid part
        print("  Generating sections from separate solid groups...")
        b = solid_mesh.bounds
        locs = {
            'x': np.arange(int(b[0]), int(b[1]), SLICE_STEP),
            'y': np.arange(int(b[2]), int(b[3]), SLICE_STEP),
            'z': np.arange(int(b[4]), int(b[5]), SLICE_STEP)
        }

        slice_paths = {'x': [], 'y': [], 'z': []}
        base_rel_path = f"{CACHE_FOLDER_NAME}/{base_name}"

        # Extract nonempty solid parts before slicing
        solid_blocks = []
        for mid in mat_ids:
            block = solid_mesh.extract_cells(mat_data == mid)
            if block.n_cells > 0:
                solid_blocks.append(block.cell_data_to_point_data(pass_cell_data=True))

        for axis, values in locs.items():
            for val in values:
                origin = [val if axis=='x' else 0, val if axis=='y' else 0, val if axis=='z' else 0]
                
                parts = []
                for block in solid_blocks:
                    p = block.slice(normal=axis, origin=origin)
                    if p.n_points > 10:
                        parts.append(p)
                        
                if parts:
                    final_slice = pv.merge(parts, merge_points=False).clean()
                    slice_name = f"slice_{axis}_{int(val)}.vtp"
                    out_path = os.path.join(out_dir, slice_name)
                    
                    self.optimize_and_save(final_slice, out_path)
                    slice_paths[axis].append(f"{base_rel_path}/{slice_name}")

        # Collect displayable scalar fields
        fields = set()
        for k, v in final_full_surface.point_data.items():
            if v.ndim == 1 and public_field(k): fields.add(k)
        for k, v in final_full_surface.cell_data.items():
            if v.ndim == 1 and public_field(k): fields.add(k)

        print(f"  Processing complete; sections generated: {sum(len(v) for v in slice_paths.values())} (combined material groups).")
        return {
            "full": f"{base_rel_path}/full_model.vtp",
            "cavity": f"{base_rel_path}/cavity_surface.vtp" if cavity_surface else None,
            "slices": slice_paths,
            "fields": sorted(fields),
            "global_ranges": self.publication_ranges
        }

    def run(self):
        # Scan INPUT_DIR first; fall back to the current directory if unavailable
        target_dir = INPUT_DIR if (INPUT_DIR and os.path.exists(INPUT_DIR)) else "."
        search_pattern = os.path.join(target_dir, "*.vtu")
        vtu_files = glob.glob(search_pattern)
        
        if not vtu_files:
            print(f"No VTU models found in [{os.path.abspath(target_dir)}].")
            return
            
        import re
        def sort_key(s):
            match = re.search(r'\d+', os.path.basename(s))
            return int(match.group()) if match else 0
            
        vtu_files = sorted(vtu_files, key=sort_key)
            
        stages_data = {}
        stage_order = []
        for fp in vtu_files:
            res = self.process_file(fp)
            if res:
                # Use the model filename as the JSON key
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
        print("\nSurface and section extraction complete.")

if __name__ == "__main__":
    processor = GeotechnicalAdvancedProcessor()
    processor.run()
