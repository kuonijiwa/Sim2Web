"""Case configuration: one declarative file replaces per-case processing scripts.

A configuration file (YAML or JSON) states *what* is in the input model and
*which* review products should be generated.  Every option that differed
between the original case scripts is an explicit, documented setting here, so
that a new model can be prepared without writing Python.

The loader is strict: unknown keys raise :class:`ConfigError`, so that a
misspelt option is never silently ignored.
"""
from __future__ import annotations

import glob
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

SCHEMA_ID = "sim2web-config/1"
#: Configuration schemas still read (the software was called SimWebView before 0.2).
LEGACY_SCHEMA_IDS = ("simwebview-config/1",)

#: Supported stress-component orders.  Six-component symmetric tensors are
#: stored in solver-specific orders; the order must be declared, not guessed.
STRESS_ORDERS = {
    "XX,YY,ZZ,XY,XZ,YZ": "Itasca (FLAC3D, 3DEC) VTU exports used in the examples",
    "XX,YY,ZZ,XY,YZ,XZ": "Voigt order (e.g. Abaqus-type exports)",
    "XX,YY,ZZ,XY,YZ,ZX": "Voigt-like order with ZX shear (same as XZ)",
}
#: ``fields.stress.order`` value that takes the order from the file's ComponentName attributes.
FROM_FILE = "from_file"


class ConfigError(ValueError):
    """Raised for invalid or inconsistent configuration files."""


# --------------------------------------------------------------------------- #
# Configuration sections
# --------------------------------------------------------------------------- #
@dataclass
class StageSpec:
    """One simulation state (for example, one construction stage)."""

    file: str
    name: str = ""
    label: str = ""


@dataclass
class InputConfig:
    stages: list[StageSpec] = field(default_factory=list)
    #: Alternative to ``stages``: a glob pattern relative to the config file.
    glob: str = ""
    #: ``natural`` sorts ``stage_2`` before ``stage_10``; ``name`` is lexical.
    sort: str = "natural"


@dataclass
class OutputConfig:
    #: Static-site directory, relative to the configuration file.
    dir: str = "site"
    #: Sub-directory inside ``dir`` that holds the index and VTP products.
    cache: str = "model_cache"
    #: Copy the packaged browser viewer next to the data products.
    viewer: bool = True


@dataclass
class VectorField:
    name: str = ""
    unit: str = ""


@dataclass
class StressField:
    name: str = ""
    #: Comma-separated component order of the six-component input array, or
    #: ``from_file`` to use the ``ComponentName`` attributes written in the VTU.
    order: str = FROM_FILE
    #: When the VTU names the components and ``order`` is given explicitly, a
    #: disagreement stops the build.  Disable only to reproduce old results.
    check_file_order: bool = True
    unit: str = ""
    #: Free-text statement of the sign convention, copied into the index.
    sign_convention: str = ""
    #: Compare the declared unit with the unit implied by the vertical stress
    #: gradient (unit weight 5-30 kN/m3) and warn when they disagree.
    unit_check: bool = True


@dataclass
class CategoryField:
    name: str
    label: str = ""
    #: Optional mapping from raw source value to a display label.
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class ExtraField:
    """Additional scalar array retained without modification."""

    name: str
    association: str = "cell"  # "cell" or "point"
    label: str = ""
    unit: str = ""


@dataclass
class FieldsConfig:
    displacement: VectorField = field(default_factory=VectorField)
    stress: StressField = field(default_factory=StressField)
    categories: list[CategoryField] = field(default_factory=list)
    extra: list[ExtraField] = field(default_factory=list)


@dataclass
class ExcavationConfig:
    enabled: bool = False
    #: ``labels``: cells whose category value contains a token;
    #: ``stress``: all six stress components below ``null_threshold``;
    #: ``labels_then_stress``: labels if any match, otherwise stress;
    #: ``field``: a boolean/integer cell array that is nonzero for void cells;
    #: ``removed_zones``: the excavated zones were deleted before export, so the
    #: excavation surface is taken as the boundary faces of the solid that do
    #: not lie on the planes of the model's bounding box (flat outer
    #: boundaries assumed; see docs/CONFIGURATION.md).
    strategy: str = "labels_then_stress"
    null_threshold: float = 1.0e-8
    label_fields: list[str] = field(default_factory=list)
    label_tokens: list[str] = field(default_factory=lambda: ["null", "excavated"])
    void_field: str = ""
    #: Solid-surface vertices closer than this to a void-surface vertex are
    #: treated as lying on the excavation boundary (model length units).
    contact_tolerance: float = 1.0e-3
    #: Retained cells with max |stress| below ``near_null_factor * null_threshold``
    #: are reported as a diagnostic: they are the cells most likely to be
    #: misclassified by a stress criterion.
    near_null_factor: float = 100.0
    #: Fail the build when no void cells are found.
    required: bool = False


@dataclass
class ExteriorConfig:
    enabled: bool = True
    #: Extract one surface per group so that internal group boundaries are kept.
    split_by_group: bool = True
    #: Discontinuous (block) models expose every block face, including faces in
    #: contact with a neighbouring block.  ``keep`` (v0.1) retains them, ``drop``
    #: keeps only faces without a coincident counterpart, and ``layer`` writes
    #: the internal contact faces as a separate supplementary layer.
    #: ``auto`` (default) drops them when the solid consists of more than one
    #: connected mesh region (block models, zones generated without merged
    #: gridpoints) and otherwise keeps the surface unchanged.
    internal_faces: str = "auto"
    #: How internal faces are recognised: ``geometric`` (faces enclosed by the
    #: solid on both sides; also finds non-conforming contacts) or
    #: ``coincident`` (faces matching another face vertex for vertex).
    internal_faces_method: str = "geometric"


@dataclass
class GroupsConfig:
    #: Cell array (a declared category) that partitions the solid; empty = none.
    field: str = ""
    #: Legacy compatibility (v0.1 Case C): write a constant integer category of
    #: this name when no group field exists.  Leave empty for new models.
    constant_fallback: str = ""


@dataclass
class GeometryConfig:
    #: Which product is the primary browser object: ``exterior`` or ``excavation``.
    primary: str = "exterior"
    exterior: ExteriorConfig = field(default_factory=ExteriorConfig)
    excavation: ExcavationConfig = field(default_factory=ExcavationConfig)
    groups: GroupsConfig = field(default_factory=GroupsConfig)
    #: Cell-to-point averaging used for *display-only* point copies on exterior
    #: surfaces and sections: ``per_group`` avoids averaging across group
    #: boundaries; ``whole_solid`` averages across the complete retained solid.
    display_averaging: str = "per_group"


@dataclass
class SectionsConfig:
    enabled: bool = True
    axes: list[str] = field(default_factory=lambda: ["x", "y", "z"])
    spacing: float = 10.0
    #: ``integer_grid``: ``int(min), int(min)+spacing, ... < max``;
    #: ``interior``: ``min+spacing, ... < max`` (spacing reduced to span/10 for
    #: spans at most twice the spacing);
    #: ``explicit``: only the positions listed in ``positions``.
    placement: str = "integer_grid"
    #: Additional (or, with ``explicit``, the only) positions per axis.
    positions: dict[str, list[float]] = field(default_factory=dict)
    #: Sections (or per-group parts) with this many points or fewer are skipped.
    min_points: int = 10
    #: Displacement magnitude on section vertices.  ``vector_norm`` (default)
    #: takes the norm of the interpolated displacement vector, consistent with
    #: the element interpolation of u.  ``interpolated`` linearly interpolates
    #: the nodal magnitudes (v0.1 behaviour), which differs where the direction
    #: of u varies along a cut edge.
    magnitude: str = "vector_norm"
    #: Keep coincident vertices of *different* connected mesh regions (for
    #: example 3DEC blocks) apart, so that displacement jumps across joints are
    #: not averaged away by point merging.  v0.1 merged them.
    preserve_discontinuities: bool = False


@dataclass
class ViewerConfig:
    title: str = ""
    subtitle: str = ""
    default_field: str = ""
    default_axis: str = ""
    colormap: str = "jet"
    bands: int = 8
    background: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    #: Display range for continuous fields: ``full`` or ``p5_p95``.
    range_mode: str = "full"
    #: Unit of the model coordinates, shown with section positions.
    length_unit: str = "m"


@dataclass
class CaseConfig:
    schema: str = SCHEMA_ID
    title: str = ""
    description: str = ""
    solver: str = ""
    input: InputConfig = field(default_factory=InputConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    fields: FieldsConfig = field(default_factory=FieldsConfig)
    geometry: GeometryConfig = field(default_factory=GeometryConfig)
    sections: SectionsConfig = field(default_factory=SectionsConfig)
    viewer: ViewerConfig = field(default_factory=ViewerConfig)

    #: Directory against which relative paths are resolved (not serialized).
    base_dir: Path = field(default=Path("."), repr=False, compare=False)
    source_text: str = field(default="", repr=False, compare=False)

    # ------------------------------------------------------------------ #
    @property
    def output_dir(self) -> Path:
        return (self.base_dir / self.output.dir).resolve()

    @property
    def cache_dir(self) -> Path:
        return self.output_dir / self.output.cache

    @property
    def stress_order(self) -> list[str] | None:
        """Declared order, or ``None`` when it is taken from the file."""
        if self.fields.stress.order.strip().lower() == FROM_FILE:
            return None
        return [c.strip().upper() for c in self.fields.stress.order.split(",")]

    def resolve_stress_order(self, path: str | Path) -> tuple[list[str], str]:
        """Component order for one stage file and how it was established."""
        from .vtkxml import component_names

        s = self.fields.stress
        in_file = component_names(path).get(s.name)
        declared = self.stress_order
        name = Path(path).name
        if declared is None:
            if not in_file:
                raise ConfigError(f"fields.stress.order is 'from_file', but {name} does not name the components "
                                  f"of '{s.name}'; declare the order explicitly")
            if ",".join(in_file) not in STRESS_ORDERS:
                raise ConfigError(f"{name} declares unsupported stress order {','.join(in_file)}")
            return in_file, "file ComponentName attributes"
        if in_file and in_file != declared:
            if s.check_file_order:
                raise ConfigError(
                    f"fields.stress.order is {','.join(declared)}, but {name} declares {','.join(in_file)} "
                    f"for '{s.name}'. Use 'order: from_file' or the file's order; set check_file_order: false "
                    f"only to reproduce results made with the other order.")
            return declared, "configuration (differs from file; check disabled)"
        if in_file:
            return declared, "configuration, matches file"
        return declared, "configuration (file names no components)"

    @property
    def category_names(self) -> list[str]:
        return [c.name for c in self.fields.categories]

    def resolved_stages(self) -> list[StageSpec]:
        """Return stages with absolute file paths and non-empty names."""
        stages: list[StageSpec] = []
        if self.input.stages:
            for spec in self.input.stages:
                path = (self.base_dir / spec.file).resolve()
                name = spec.name or path.stem
                stages.append(StageSpec(file=str(path), name=name, label=spec.label or name))
        else:
            matches = [Path(p) for p in glob.glob(str(self.base_dir / self.input.glob))]
            key = _natural_key if self.input.sort == "natural" else (lambda p: p.name)
            for path in sorted(matches, key=key):
                stages.append(StageSpec(file=str(path.resolve()), name=path.stem, label=path.stem))
        names = [s.name for s in stages]
        if len(set(names)) != len(names):
            raise ConfigError(f"Stage names must be unique: {names}")
        return stages

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("base_dir", None)
        data.pop("source_text", None)
        return data

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.source_text.encode("utf-8")).hexdigest()


def _natural_key(path: Path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", path.name)]


# --------------------------------------------------------------------------- #
# Strict loading
# --------------------------------------------------------------------------- #
def _build(cls, data: Any, where: str):
    if not is_dataclass(cls):
        return data
    if not isinstance(data, dict):
        raise ConfigError(f"{where}: expected a mapping, got {type(data).__name__}")
    hints = get_type_hints(cls)
    known = {f.name for f in fields(cls) if f.name not in ("base_dir", "source_text")}
    unknown = set(data) - known
    if unknown:
        raise ConfigError(f"{where}: unknown option(s) {sorted(unknown)}; allowed: {sorted(known)}")
    kwargs = {}
    for name, value in data.items():
        kwargs[name] = _coerce(hints[name], value, f"{where}.{name}")
    try:
        return cls(**kwargs)
    except TypeError as exc:  # missing required field
        raise ConfigError(f"{where}: {exc}") from None


def _coerce(tp, value, where):
    origin = get_origin(tp)
    if is_dataclass(tp):
        return _build(tp, value, where)
    if origin is list:
        (item,) = get_args(tp)
        if not isinstance(value, list):
            raise ConfigError(f"{where}: expected a list")
        return [_coerce(item, v, f"{where}[{i}]") for i, v in enumerate(value)]
    if origin is dict:
        _, item = get_args(tp)
        if not isinstance(value, dict):
            raise ConfigError(f"{where}: expected a mapping")
        return {str(k): _coerce(item, v, f"{where}.{k}") for k, v in value.items()}
    if tp is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConfigError(f"{where}: expected a number")
        return float(value)
    if tp is int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError(f"{where}: expected an integer")
        return value
    if tp is bool:
        if not isinstance(value, bool):
            raise ConfigError(f"{where}: expected true/false")
        return value
    if tp is str:
        if value is None:          # "key:" or "--set key=" means empty text
            return ""
        if not isinstance(value, (str, int, float)):
            raise ConfigError(f"{where}: expected text")
        return str(value)
    return value


def _validate(cfg: CaseConfig) -> None:
    if cfg.schema in LEGACY_SCHEMA_IDS:
        cfg.schema = SCHEMA_ID
    if cfg.schema != SCHEMA_ID:
        raise ConfigError(f"schema must be '{SCHEMA_ID}', got '{cfg.schema}'")
    if bool(cfg.input.stages) == bool(cfg.input.glob):
        raise ConfigError("input: give exactly one of 'stages' or 'glob'")
    if cfg.input.sort not in ("natural", "name"):
        raise ConfigError("input.sort must be 'natural' or 'name'")
    if cfg.fields.stress.name and cfg.stress_order is not None:
        order = ",".join(cfg.stress_order)
        if order not in STRESS_ORDERS:
            raise ConfigError(f"fields.stress.order '{order}' is not 'from_file' or one of {sorted(STRESS_ORDERS)}")
    geo = cfg.geometry
    if geo.primary not in ("exterior", "excavation"):
        raise ConfigError("geometry.primary must be 'exterior' or 'excavation'")
    if geo.primary == "excavation" and not geo.excavation.enabled:
        raise ConfigError("geometry.primary is 'excavation' but geometry.excavation.enabled is false")
    if geo.primary == "exterior" and not geo.exterior.enabled:
        raise ConfigError("geometry.primary is 'exterior' but geometry.exterior.enabled is false")
    if geo.display_averaging not in ("per_group", "whole_solid"):
        raise ConfigError("geometry.display_averaging must be 'per_group' or 'whole_solid'")
    exc = geo.excavation
    if exc.strategy not in ("labels", "stress", "labels_then_stress", "field", "removed_zones"):
        raise ConfigError("geometry.excavation.strategy must be labels|stress|labels_then_stress|field|removed_zones")
    if exc.enabled and exc.strategy in ("stress", "labels_then_stress") and not cfg.fields.stress.name:
        raise ConfigError("a stress-based excavation strategy needs fields.stress.name")
    if exc.enabled and exc.strategy == "field" and not exc.void_field:
        raise ConfigError("geometry.excavation.strategy 'field' needs void_field")
    if exc.null_threshold < 0 or exc.contact_tolerance <= 0:
        raise ConfigError("null_threshold must be >= 0 and contact_tolerance > 0")
    if geo.groups.field and geo.groups.field not in cfg.category_names:
        raise ConfigError(f"geometry.groups.field '{geo.groups.field}' must be a declared category")
    sec = cfg.sections
    if any(a not in ("x", "y", "z") for a in sec.axes):
        raise ConfigError("sections.axes may contain only x, y, z")
    if sec.placement not in ("integer_grid", "interior", "explicit"):
        raise ConfigError("sections.placement must be integer_grid|interior|explicit")
    if sec.placement != "explicit" and sec.spacing <= 0:
        raise ConfigError("sections.spacing must be positive")
    if geo.exterior.internal_faces_method not in ("geometric", "coincident"):
        raise ConfigError("geometry.exterior.internal_faces_method must be geometric|coincident")
    if geo.exterior.internal_faces not in ("auto", "keep", "drop", "layer"):
        raise ConfigError("geometry.exterior.internal_faces must be auto|keep|drop|layer")
    if sec.magnitude not in ("vector_norm", "interpolated"):
        raise ConfigError("sections.magnitude must be 'vector_norm' or 'interpolated'")
    if any(a not in ("x", "y", "z") for a in sec.positions):
        raise ConfigError("sections.positions keys must be x, y or z")
    for extra in cfg.fields.extra:
        if extra.association not in ("cell", "point"):
            raise ConfigError(f"fields.extra '{extra.name}': association must be cell or point")
    if cfg.viewer.range_mode not in ("full", "p5_p95"):
        raise ConfigError("viewer.range_mode must be 'full' or 'p5_p95'")
    if cfg.viewer.bands < 1:
        raise ConfigError("viewer.bands must be >= 1")


_KEY_PART = re.compile(r"^([A-Za-z_][\w-]*)((?:\[\d+\])*)$")


def apply_overrides(data: dict, overrides: list[str]) -> dict:
    """Apply ``dotted.key=value`` overrides; values are parsed as YAML scalars.

    List entries are addressed by index: ``input.stages[0].file=a.vtu``.
    """
    import yaml

    for item in overrides or []:
        if "=" not in item:
            raise ConfigError(f"override '{item}' must look like key.path=value")
        key, raw = item.split("=", 1)
        steps: list = []
        for part in key.strip().split("."):
            m = _KEY_PART.match(part)
            if not m:
                raise ConfigError(f"override '{item}': cannot read '{part}'")
            steps.append(m.group(1))
            steps += [int(i) for i in re.findall(r"\[(\d+)\]", m.group(2))]
        node = data
        for here, nxt in zip(steps[:-1], steps[1:]):
            if isinstance(here, int):
                if not isinstance(node, list) or here >= len(node):
                    raise ConfigError(f"override '{item}': index [{here}] is out of range")
                node = node[here]
            else:
                if not isinstance(node, dict):
                    raise ConfigError(f"override '{item}': '{here}' is not a section")
                node = node.setdefault(here, [] if isinstance(nxt, int) else {})
        last = steps[-1]
        if isinstance(last, int):
            if not isinstance(node, list) or last >= len(node):
                raise ConfigError(f"override '{item}': index [{last}] is out of range")
            node[last] = yaml.safe_load(raw)
        else:
            if not isinstance(node, dict):
                raise ConfigError(f"override '{item}': '{last}' cannot be set here")
            node[last] = yaml.safe_load(raw)
    return data


def load_config(path: str | Path, overrides: list[str] | None = None) -> CaseConfig:
    """Load and validate a YAML or JSON case configuration.

    ``overrides`` (``["sections.spacing=5", ...]``) are applied before
    validation and are included in the configuration hash.
    """
    path = Path(path).resolve()
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        import yaml

        data = yaml.safe_load(text)
    data = apply_overrides(data or {}, overrides or [])
    cfg = config_from_dict(data, base_dir=path.parent)
    cfg.source_text = text + "".join(f"\n# override: {o}" for o in overrides or [])
    return cfg


def config_from_dict(data: dict[str, Any], base_dir: str | Path = ".") -> CaseConfig:
    cfg = _build(CaseConfig, data, "config")
    cfg.base_dir = Path(base_dir).resolve()
    if not cfg.source_text:
        cfg.source_text = json.dumps(data, sort_keys=True)
    _validate(cfg)
    return cfg
