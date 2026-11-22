"""Field contract: derived quantities, array roles, provenance and output rules.

Array roles
-----------
``quantitative point``  displacement components and magnitude (PointData).
``quantitative cell``   stress components, principal stresses, extra cell arrays
                        (CellData; displayed with exact per-cell colours).
``categorical cell``    integer codes ``<name>_ID`` of declared category arrays
                        (CellData; never interpolated).
``display-only point``  cell-to-point averages of quantitative cell arrays,
                        renamed ``<name>_DisplayOnly`` and excluded from the
                        quantitative field list.
``provenance``          ``Source_Cell_ID`` on every product cell and
                        ``Source_Point_ID`` on vertices that are source nodes.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

POINT_ID = "Source_Point_ID"
CELL_ID = "Source_Cell_ID"
DISPLAY_SUFFIX = "_DisplayOnly"
CATEGORY_SUFFIX = "_ID"

DISPLACEMENT_FIELDS = ["TotalDisplacement", "X_Disp", "Y_Disp", "Z_Disp"]
STRESS_COMPONENT_FIELDS = ["Stress_XX", "Stress_YY", "Stress_ZZ"]
PRINCIPAL_FIELDS = ["Stress_Min_Principal", "Stress_Mid_Principal", "Stress_Max_Principal"]
STRESS_FIELDS = STRESS_COMPONENT_FIELDS + PRINCIPAL_FIELDS

_COMPONENT_INDEX = {"XX": (0, 0), "YY": (1, 1), "ZZ": (2, 2), "XY": (0, 1), "YZ": (1, 2), "XZ": (0, 2), "ZX": (0, 2)}


def category_output_name(name: str) -> str:
    return f"{name}{CATEGORY_SUFFIX}"


# --------------------------------------------------------------------------- #
# Derived quantities
# --------------------------------------------------------------------------- #
def symmetric_tensor(components: np.ndarray, order: list[str]) -> np.ndarray:
    """Assemble ``(N, 3, 3)`` symmetric tensors from six components in ``order``."""
    s = np.asarray(components)
    if s.ndim != 2 or s.shape[1] < 6:
        raise ValueError(f"Expected an (N, 6) stress array, got shape {s.shape}")
    tensor = np.zeros((s.shape[0], 3, 3))
    for column, name in enumerate(order[:6]):
        i, j = _COMPONENT_INDEX[name]
        tensor[:, i, j] = s[:, column]
        tensor[:, j, i] = s[:, column]
    return tensor


def principal_values(components: np.ndarray, order: list[str]) -> np.ndarray:
    """Return algebraically ordered principal values ``(min, mid, max)``.

    The ordering is algebraic.  With the usual geomechanics convention of
    compression-negative stress, the *most compressive* principal stress is
    ``Stress_Min_Principal``.
    """
    return np.linalg.eigvalsh(symmetric_tensor(components, order))


@dataclass
class FieldSummary:
    displacement_association: str | None
    stress_association: str | None
    categories: dict[str, list[str]]
    stress_order: list[str] | None = None


def derive_fields(mesh, cfg, stress_order: list[str] | None = None) -> FieldSummary:
    """Add derived arrays to ``mesh`` in place, in a fixed, documented order.

    1. ``<category>_ID`` integer codes for every declared category, from the
       sorted unique source values (codes are therefore stable and reproducible);
    2. displacement magnitude and components;
    3. stress normal components and algebraic principal stresses.
    """
    fcfg = cfg.fields
    categories: dict[str, list[str]] = {}
    for cat in fcfg.categories:
        if cat.name not in mesh.cell_data:
            raise KeyError(f"Declared category '{cat.name}' is not a cell array of the input")
        values, codes = np.unique(mesh.cell_data[cat.name], return_inverse=True)
        mesh.cell_data[category_output_name(cat.name)] = codes
        categories[cat.name] = [str(v) for v in values]

    disp_assoc = None
    if fcfg.displacement.name:
        container, disp_assoc = _locate(mesh, fcfg.displacement.name)
        data = container[fcfg.displacement.name]
        if data.ndim != 2 or data.shape[1] < 3:
            raise ValueError(f"Displacement '{fcfg.displacement.name}' must have three components")
        container["TotalDisplacement"] = np.linalg.norm(data, axis=1)
        container["X_Disp"], container["Y_Disp"], container["Z_Disp"] = data.T[:3]

    stress_assoc = None
    if fcfg.stress.name:
        container, stress_assoc = _locate(mesh, fcfg.stress.name)
        s = container[fcfg.stress.name]
        if s.ndim != 2 or s.shape[1] < 6:
            raise ValueError(f"Stress '{fcfg.stress.name}' must have six components")
        order = stress_order or cfg.stress_order
        if order is None:
            raise ValueError("Resolve the stress component order first (cfg.resolve_stress_order)")
        for name, comp in zip(STRESS_COMPONENT_FIELDS, ("XX", "YY", "ZZ")):
            container[name] = s[:, order.index(comp)]
        eig = principal_values(s, order)
        container["Stress_Min_Principal"] = eig[:, 0]
        container["Stress_Mid_Principal"] = eig[:, 1]
        container["Stress_Max_Principal"] = eig[:, 2]

    for extra in fcfg.extra:
        container = mesh.cell_data if extra.association == "cell" else mesh.point_data
        if extra.name not in container:
            raise KeyError(f"Extra {extra.association} array '{extra.name}' is not in the input")
        if np.asarray(container[extra.name]).ndim != 1:
            raise ValueError(f"Extra array '{extra.name}' must be scalar")
    return FieldSummary(disp_assoc, stress_assoc, categories, order if fcfg.stress.name else None)


def _locate(mesh, name):
    if name in mesh.cell_data:
        return mesh.cell_data, "cell"
    if name in mesh.point_data:
        return mesh.point_data, "point"
    raise KeyError(f"Array '{name}' is neither PointData nor CellData of the input")


def attach_source_ids(mesh) -> None:
    """Number source nodes and cells; call before any selection or filter."""
    mesh.point_data[POINT_ID] = np.arange(mesh.n_points, dtype=np.int64)
    mesh.cell_data[CELL_ID] = np.arange(mesh.n_cells, dtype=np.int64)


# --------------------------------------------------------------------------- #
# Output contract
# --------------------------------------------------------------------------- #
class OutputContract:
    """Decides which arrays a written product keeps and in which role."""

    def __init__(self, cfg):
        self.categories = set(cfg.category_names)
        self.category_codes = {category_output_name(n) for n in self.categories}
        self.extra_cell = {e.name for e in cfg.fields.extra if e.association == "cell"}
        self.extra_point = {e.name for e in cfg.fields.extra if e.association == "point"}
        self.quantitative = set(DISPLACEMENT_FIELDS) | set(STRESS_FIELDS) | self.extra_cell | self.extra_point
        constant = cfg.geometry.groups.constant_fallback
        if constant:
            self.category_codes.add(constant)
        #: "cell" for zone/element stress (Itasca), "point" for nodal stress (most FE codes)
        self.stress_association = "cell"

    def is_category(self, name: str) -> bool:
        return name in self.categories or name in self.category_codes

    def is_cell_authoritative(self, name: str) -> bool:
        if name.startswith("Stress_"):
            return self.stress_association == "cell"
        return name in self.extra_cell

    def prune(self, mesh) -> None:
        """Remove arrays that are not part of the published contract."""
        keep = self.quantitative | self.categories | self.category_codes | {POINT_ID, CELL_ID}
        for container in (mesh.point_data, mesh.cell_data):
            for name in list(container.keys()):
                if name not in keep and not name.endswith(DISPLAY_SUFFIX):
                    del container[name]

    def to_float32(self, mesh) -> None:
        mesh.points = np.asarray(mesh.points, dtype=np.float32)
        for container in (mesh.point_data, mesh.cell_data):
            for name in list(container.keys()):
                if container[name].dtype == np.float64:
                    container[name] = container[name].astype(np.float32)

    def finalize(self, mesh, is_section: bool, ranges: dict) -> None:
        """Apply role rules and accumulate scalar ranges of quantitative arrays.

        * averaged categories and averaged cell IDs are removed from PointData;
        * point copies of cell-authoritative arrays become ``*_DisplayOnly``;
        * ``Source_Point_ID`` is removed from sections, whose vertices are
          interpolated and are not source nodes;
        * every remaining array must be finite.
        """
        for name in list(mesh.point_data):
            if self.is_category(name) or name == CELL_ID or (name == POINT_ID and is_section):
                del mesh.point_data[name]
            elif self.is_cell_authoritative(name) and not name.endswith(DISPLAY_SUFFIX):
                mesh.point_data[name + DISPLAY_SUFFIX] = mesh.point_data[name].copy()
                del mesh.point_data[name]
        if CELL_ID not in mesh.cell_data:
            raise ValueError("Source cell provenance was lost before writing")
        for container in (mesh.point_data, mesh.cell_data):
            for name in list(container):
                if name.startswith("vtkOriginal"):
                    del container[name]
        for name in sorted(set(mesh.point_data) | set(mesh.cell_data)):
            if name in (POINT_ID, CELL_ID) or name.endswith(DISPLAY_SUFFIX):
                continue
            in_cell = name in mesh.cell_data and (self.is_category(name) or self.is_cell_authoritative(name))
            container = mesh.cell_data if in_cell else mesh.point_data
            if name not in container:
                continue
            values = np.asarray(container[name])
            if values.ndim != 1 or not np.issubdtype(values.dtype, np.number):
                continue
            if not np.all(np.isfinite(values)):
                raise ValueError(f"Nonfinite output scalar {name}")
            lo, hi = float(values.min()), float(values.max())
            previous = ranges.get(name, [lo, hi])
            ranges[name] = [min(lo, previous[0]), max(hi, previous[1])]


# --------------------------------------------------------------------------- #
# Metadata for the browser index
# --------------------------------------------------------------------------- #
_DEFAULT_LABELS = {
    "TotalDisplacement": "Displacement magnitude",
    "X_Disp": "X displacement",
    "Y_Disp": "Y displacement",
    "Z_Disp": "Z displacement",
    "Stress_XX": "Normal stress σxx",
    "Stress_YY": "Normal stress σyy",
    "Stress_ZZ": "Normal stress σzz",
    "Stress_Max_Principal": "Maximum principal stress (algebraic)",
    "Stress_Mid_Principal": "Intermediate principal stress",
    "Stress_Min_Principal": "Minimum principal stress (algebraic)",
}

FIELD_ORDER = ["TotalDisplacement", "X_Disp", "Y_Disp", "Z_Disp", "Stress_Max_Principal",
               "Stress_Mid_Principal", "Stress_Min_Principal", "Stress_XX", "Stress_YY", "Stress_ZZ"]


def field_metadata(cfg, summary: FieldSummary, constant_group: str = "") -> dict[str, dict]:
    """Describe every quantitative and categorical field for the viewer."""
    meta: dict[str, dict] = {}
    f = cfg.fields
    if f.displacement.name:
        for name in DISPLACEMENT_FIELDS:
            meta[name] = {"label": _DEFAULT_LABELS[name], "unit": f.displacement.unit, "association": "point",
                          "kind": "continuous", "source": f.displacement.name}
    if f.stress.name:
        for name in STRESS_FIELDS:
            meta[name] = {"label": _DEFAULT_LABELS[name], "unit": f.stress.unit,
                          "association": summary.stress_association or "cell",
                          "kind": "continuous", "source": f.stress.name,
                          "component_order": ",".join(summary.stress_order or cfg.stress_order or []),
                          "sign_convention": f.stress.sign_convention}
    for extra in f.extra:
        meta[extra.name] = {"label": extra.label or extra.name, "unit": extra.unit,
                            "association": extra.association, "kind": "continuous", "source": extra.name}
    for cat in f.categories:
        values = summary.categories.get(cat.name, [])
        meta[category_output_name(cat.name)] = {
            "label": cat.label or cat.name, "unit": "", "association": "cell", "kind": "categorical",
            "source": cat.name,
            "categories": [{"code": i, "value": v, "label": cat.labels.get(v, v)} for i, v in enumerate(values)],
        }
    if constant_group:
        meta[constant_group] = {"label": "Group (constant)", "unit": "", "association": "cell",
                                "kind": "categorical", "source": "",
                                "categories": [{"code": 0, "value": "0", "label": "0"}]}
    return meta


def is_section_path(path: str | Path) -> bool:
    return Path(path).name.startswith("slice_")
