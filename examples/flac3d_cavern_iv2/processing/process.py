# -*- coding: utf-8 -*-
import os
import json
import glob
from pathlib import Path
import numpy as np
import pyvista as pv
import vtk  # Native VTK writer for Zlib compression
from scipy.spatial import KDTree

# =============================================================================
# Portable case configuration. Numerical processing below is unchanged.
# =============================================================================
CASE_ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(CASE_ROOT.parents[1] / "src"))
from geosimvis.field_contract import attach_source_ids, prepare_output, public_field
INPUT_DIR = CASE_ROOT / "input"
WEB_PUBLIC_DIR = str(CASE_ROOT / "output")
CACHE_FOLDER_NAME = "model_cache"
SLICE_STEP = 5  
EPS = 1e-8

CUSTOM_SLICES = {
    'x': [0, 54, 108, 162, 189, 234], 
    'y': [],                
    'z': []         
}
# =============================================================================

OUTPUT_DIR = os.path.join(WEB_PUBLIC_DIR, CACHE_FOLDER_NAME)

class DualModelProcessor3D:
    def __init__(self):
        self.publication_ranges = {}
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        print(f"Output directory: {OUTPUT_DIR}")

    def precalculate_fields(self, mesh):
        """Compute physical components, including principal stresses."""
        # 1. Process groups while retaining CellData
        for k in list(mesh.cell_data.keys()):
            if mesh.cell_data[k].dtype.kind in {'U', 'S', 'O'} or 'group' in k.lower():
                unique_vals, indices = np.unique(mesh.cell_data[k], return_inverse=True)
                mesh.cell_data[f"{k}_ID"] = indices

        # 2. Process displacement
        disp_key = next((k for k in mesh.point_data.keys() if 'dis' in k.lower()), None)
        if not disp_key:
            disp_key = next((k for k in mesh.cell_data.keys() if 'dis' in k.lower()), None)
        
        if disp_key:
            data = mesh.point_data[disp_key] if disp_key in mesh.point_data else mesh.cell_data[disp_key]
            target = mesh.point_data if disp_key in mesh.point_data else mesh.cell_data
            target['TotalDisplacement'] = np.linalg.norm(data, axis=1)
            target['X_Disp'], target['Y_Disp'], target['Z_Disp'] = data.T

        # 3. Process stress
        stress_key = next((k for k in mesh.cell_data.keys() if any(x in k.lower() for x in ['stress', 'sig'])), None)
        if stress_key and mesh.cell_data[stress_key].ndim == 2:
            s = mesh.cell_data[stress_key]
            if s.shape[1] >= 3:
                mesh.cell_data["Stress_XX"] = s[:, 0]
                mesh.cell_data["Stress_YY"] = s[:, 1]
                mesh.cell_data["Stress_ZZ"] = s[:, 2]
            if s.shape[1] >= 6:
                N = s.shape[0]
                tensor = np.zeros((N, 3, 3))
                tensor[:, 0, 0], tensor[:, 1, 1], tensor[:, 2, 2] = s[:, 0], s[:, 1], s[:, 2]
                tensor[:, 0, 1] = tensor[:, 1, 0] = s[:, 3]
                tensor[:, 1, 2] = tensor[:, 2, 1] = s[:, 4]
                tensor[:, 0, 2] = tensor[:, 2, 0] = s[:, 5]
                eigvals = np.linalg.eigvalsh(tensor)
                mesh.cell_data["Stress_Min_Principal"] = eigvals[:, 0]
                mesh.cell_data["Stress_Mid_Principal"] = eigvals[:, 1]
                mesh.cell_data["Stress_Max_Principal"] = eigvals[:, 2]
        return mesh

    def optimize_and_save(self, mesh, out_path):
        """
        Compression without mesh decimation:
        1. Retain fields required by the frontend.
        2. Convert Float64 arrays to Float32 to reduce their storage size.
        3. Enable VTK level-9 Zlib compression.
        """
        # Use a combined allowlist to retain stress fields in point_data
        keep_fields = [
            'TotalDisplacement', 'X_Disp', 'Y_Disp', 'Z_Disp',
            'Stress_XX', 'Stress_YY', 'Stress_ZZ', 
            'Stress_Max_Principal', 'Stress_Mid_Principal', 'Stress_Min_Principal'
        ]
        
        # Remove unused point arrays
        for k in list(mesh.point_data.keys()):
            if k not in keep_fields and not ('group' in k.lower() or '_id' in k.lower()):
                del mesh.point_data[k]
                
        # Remove unused cell arrays
        for k in list(mesh.cell_data.keys()):
            if k not in keep_fields and not ('group' in k.lower() or '_id' in k.lower()):
                del mesh.cell_data[k]

        # 2. Convert Float64 arrays to Float32
        mesh.points = np.asarray(mesh.points, dtype=np.float32)
        
        for k in list(mesh.point_data.keys()):
            arr = mesh.point_data[k]
            if arr.dtype == np.float64:
                mesh.point_data[k] = arr.astype(np.float32)
                
        for k in list(mesh.cell_data.keys()):
            arr = mesh.cell_data[k]
            if arr.dtype == np.float64:
                mesh.cell_data[k] = arr.astype(np.float32)

        # 3. Write using native VTK compression
        writer = vtk.vtkXMLPolyDataWriter()
        prepare_output(mesh, out_path, self.publication_ranges)
        writer.SetFileName(out_path)
        writer.SetInputData(mesh)
        writer.SetDataModeToAppended()    # Appended data mode for the web reader
        writer.SetCompressorTypeToZLib()  # Enable Zlib compression
        writer.SetCompressionLevel(9)     # Use compression level 9
        writer.Write()

    def extract_cavity_and_slices(self, mesh, out_dir):
        """Extract inner surfaces and sections, retaining cell and point data."""
        stress_key = next((k for k in mesh.cell_data.keys() if any(x in k.lower() for x in ['stress', 'sig'])), None)
        if stress_key:
            cell_null = np.all(np.abs(mesh.cell_data[stress_key]) < EPS, axis=1)
        else:
            return None, None

        # Map stresses to points while retaining original cell groups
        solid_mesh = mesh.extract_cells(~cell_null).cell_data_to_point_data(pass_cell_data=True)
        null_mesh = mesh.extract_cells(cell_null)

        if null_mesh.n_cells == 0: return None, None

        # Extract the cavern surface and merge coincident points with clean()
        solid_surf = solid_mesh.extract_surface()
        null_surf = null_mesh.extract_surface()
        tree = KDTree(null_surf.points)
        dists, _ = tree.query(solid_surf.points)
        cavity_surface = solid_surf.extract_points(dists < 1e-5).extract_surface().clean()
        
        # Calculate section bounds
        b = solid_mesh.bounds
        locs = {
            'x': np.arange(int(b[0]), int(b[1]), SLICE_STEP),
            'y': np.arange(int(b[2]), int(b[3]), SLICE_STEP),
            'z': np.arange(int(b[4]), int(b[5]), SLICE_STEP)
        }
        for axis in ['x', 'y', 'z']:
            if axis in CUSTOM_SLICES and CUSTOM_SLICES[axis]:
                locs[axis] = np.unique(np.concatenate((locs[axis], CUSTOM_SLICES[axis])))

        slice_paths = {'x': [], 'y': [], 'z': []}
        base_rel_path = f"{CACHE_FOLDER_NAME}/{os.path.basename(out_dir)}"

        for axis, values in locs.items():
            for val in values:
                origin = [val if axis=='x' else 0, val if axis=='y' else 0, val if axis=='z' else 0]
                slice_mesh = solid_mesh.slice(normal=axis, origin=origin)
                if slice_mesh.n_points > 10:
                    val_str = f"{val:.1f}".rstrip('0').rstrip('.')
                    slice_name = f"slice_{axis}_{val_str}.vtp"
                    out_path = os.path.join(out_dir, slice_name)
                    
                    # Clean duplicate section points and save compressed output
                    self.optimize_and_save(slice_mesh.clean(), out_path)
                    
                    slice_paths[axis].append(f"{base_rel_path}/{slice_name}")
        
        return cavity_surface, slice_paths

    def process(self, filename):
        print(f"Processing: {filename}")
        mesh = pv.read(filename)
        name = os.path.splitext(os.path.basename(filename))[0]
        out_dir = os.path.join(OUTPUT_DIR, name)
        os.makedirs(out_dir, exist_ok=True)

        mesh = self.precalculate_fields(mesh)
        attach_source_ids(mesh)
        cavity_surface, slice_paths = self.extract_cavity_and_slices(mesh, out_dir)
        
        if cavity_surface is None: return None

        cavity_rel_path = f"{CACHE_FOLDER_NAME}/{name}/cavity_surface.vtp"
        
        # Save the compressed cavern surface
        self.optimize_and_save(cavity_surface, os.path.join(out_dir, "cavity_surface.vtp"))

        # Collect scalar point and cell fields for index.json
        fields = set()
        for k, v in cavity_surface.point_data.items():
            if v.ndim == 1 and public_field(k): fields.add(k)
        for k, v in cavity_surface.cell_data.items():
            if v.ndim == 1 and public_field(k): fields.add(k)

        return {
            "cavity": cavity_rel_path,
            "slices": slice_paths,
            "fields": sorted(fields),
            "global_ranges": self.publication_ranges
        }

if __name__ == "__main__":
    extractor = DualModelProcessor3D()
    index_data = {}
    for fp in glob.glob(os.path.join(str(INPUT_DIR), "*.vtu")):
        res = extractor.process(fp)
        if res: index_data[Path(fp).stem] = res

    with open(os.path.join(OUTPUT_DIR, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    print("\nCavern processing complete; stress fields retained.")
