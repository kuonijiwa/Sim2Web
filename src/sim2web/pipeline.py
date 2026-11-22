"""Build pipeline: configuration in, static review package out.

``build(cfg)`` performs, for every stage of the configuration:

1. read the VTU and derive declared fields (:mod:`sim2web.fields`);
2. attach source identifiers;
3. classify void (excavated) cells (:mod:`sim2web.regions`);
4. extract the exterior surface, the excavation boundary and the sections
   (:mod:`sim2web.geometry`);
5. apply the output contract, convert to Float32 and write VTP files;
6. write a deterministic ``index.json`` (schema ``sim2web-index/2``) and a
   separate ``build_report.json`` with timings and diagnostics.

``index.json`` contains no timestamps or absolute paths, so repeated builds of
the same inputs produce byte-identical packages.
"""
from __future__ import annotations

import json
import platform
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pyvista as pv

from . import __version__
from .config import CaseConfig
from .fields import (FIELD_ORDER, OutputContract, attach_source_ids, category_output_name, derive_fields,
                     field_metadata, principal_values)
from .geometry import (count_regions, excavation_boundary, exterior_surface, format_position, inner_boundary, label_regions,
                       partition,
                       section_discontinuous, section_per_group, section_positions, section_whole,
                       split_internal_faces, triangle_quality, with_display_points)
from .regions import identify_void
from .writer import sha256_file, write_vtp

INDEX_SCHEMA = "sim2web-index/2"


@dataclass
class StageResult:
    index: dict
    report: dict


@dataclass
class BuildResult:
    output_dir: Path
    index_path: Path
    report_path: Path
    stages: list[StageResult] = field(default_factory=list)


class _Timer:
    def __init__(self):
        self.times: dict[str, float] = {}

    def __call__(self, name):
        timer = self

        class _Ctx:
            def __enter__(self):
                self.t = time.perf_counter()

            def __exit__(self, *exc):
                timer.times[name] = timer.times.get(name, 0.0) + time.perf_counter() - self.t

        return _Ctx()


class _Publisher:
    """Applies the output contract and writes one product."""

    def __init__(self, cfg: CaseConfig, contract: OutputContract, stage_dir: Path, cache_dir: Path, quality: bool):
        self.cfg, self.contract, self.stage_dir, self.cache_dir = cfg, contract, stage_dir, cache_dir
        self.ranges: dict[str, list[float]] = {}
        self.values: dict[str, list[np.ndarray]] = {}
        self.quality = quality
        self.quality_reports: dict[str, dict] = {}

    def __call__(self, mesh, relative: str, is_section: bool) -> dict:
        path = self.stage_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        self.contract.prune(mesh)
        self.contract.to_float32(mesh)
        self.contract.finalize(mesh, is_section, self.ranges)
        write_vtp(mesh, path)
        for name in set(mesh.point_data) | set(mesh.cell_data):
            in_cell = name in mesh.cell_data and (self.contract.is_category(name) or self.contract.is_cell_authoritative(name))
            arr = np.asarray(mesh.cell_data[name] if in_cell else mesh.point_data.get(name, mesh.cell_data.get(name)))
            if arr.ndim == 1 and np.issubdtype(arr.dtype, np.number):
                self.values.setdefault(name, []).append(arr)
        if self.quality:
            self.quality_reports[relative] = triangle_quality(mesh)
        rel_to_cache = path.relative_to(self.cache_dir.parent).as_posix()
        return {"file": rel_to_cache, "bytes": path.stat().st_size, "sha256": sha256_file(path),
                "points": int(mesh.n_points), "cells": int(mesh.n_cells),
                "point_arrays": sorted(mesh.point_data.keys()), "cell_arrays": sorted(mesh.cell_data.keys())}

    def percentiles(self) -> dict[str, dict]:
        out = {}
        for name, arrays in self.values.items():
            v = np.concatenate([a.astype(np.float64) for a in arrays])
            out[name] = {"p5": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95))}
        return out


def build_stage(cfg: CaseConfig, spec, cache_dir: Path, quality: bool = True, log=print) -> StageResult:
    t = _Timer()
    with t("read"):
        mesh = pv.read(spec.file)
    source = {"file": Path(spec.file).name, "sha256": sha256_file(spec.file), "bytes": Path(spec.file).stat().st_size,
              "points": int(mesh.n_points), "cells": int(mesh.n_cells)}
    log(f"[{spec.name}] {source['points']} points, {source['cells']} cells")
    contract = OutputContract(cfg)
    order, order_source = cfg.resolve_stress_order(spec.file) if cfg.fields.stress.name else (None, "")
    if order:
        log(f"[{spec.name}] stress order {','.join(order)} ({order_source})")
    unit_check = None
    if cfg.fields.stress.name and cfg.fields.stress.unit_check:
        from .checks import stress_unit_check

        unit_check = stress_unit_check(mesh, cfg.fields.stress.name, order.index("ZZ"), cfg.fields.stress.unit)
        unit_check["association"] = "point" if cfg.fields.stress.name in mesh.point_data else "cell"
        if unit_check.get("status") == "ok" and not unit_check.get("declared_consistent", True):
            log(f"[{spec.name}] WARNING: stress unit '{cfg.fields.stress.unit}' is not consistent with the vertical "
                f"stress gradient ({unit_check['gradient_per_m']:.4g} per m); consistent: "
                f"{unit_check['consistent_units'] or 'none'}")
    with t("fields"):
        summary = derive_fields(mesh, cfg, order)
        contract.stress_association = summary.stress_association or "cell"
        attach_source_ids(mesh)
    geo = cfg.geometry
    with t("classify"):
        void = identify_void(mesh, cfg)
    log(f"[{spec.name}] void cells: {void.n_void} ({void.method})")
    if geo.primary == "excavation" and void.n_void == 0 and geo.excavation.strategy != "removed_zones":
        raise RuntimeError(f"[{spec.name}] primary product is the excavation surface, but no void cells were found")

    stage_dir = cache_dir / spec.name
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True)
    publish = _Publisher(cfg, contract, stage_dir, cache_dir, quality)

    group_array = category_output_name(geo.groups.field) if geo.groups.field else None
    regions = None
    with t("partition"):
        part = partition(mesh, void.mask, group_array, geo.groups.constant_fallback)
        needs_regions = (geo.exterior.internal_faces != "keep"
                         or (geo.excavation.enabled and geo.excavation.strategy == "removed_zones"))
        if cfg.sections.preserve_discontinuities:
            regions = label_regions(part.solid)
        elif needs_regions:
            regions = count_regions(part.solid)
        if regions is not None:
            log(f"[{spec.name}] connected mesh regions (blocks): {regions}")
        whole_display = with_display_points(part.solid)
    internal_mode = geo.exterior.internal_faces
    if internal_mode == "auto":
        internal_mode = "drop" if (regions or 1) > 1 else "keep"
        log(f"[{spec.name}] internal faces: auto -> {internal_mode}")
    layers = []
    boundary_info = {}
    if geo.excavation.enabled:
        with t("excavation"):
            if geo.excavation.strategy == "removed_zones":
                boundary = inner_boundary(whole_display, geo.excavation.contact_tolerance)
                if boundary is not None and (regions or 1) > 1:
                    # mesh interfaces without shared gridpoints are boundaries of
                    # the topology but have rock on both sides: not excavation
                    boundary, _, n_hidden = split_internal_faces(boundary, part.solid, "geometric")
                    boundary_info["internal_faces_removed"] = n_hidden
                    log(f"[{spec.name}] interface faces removed from the excavation surface: {n_hidden}")
                    if boundary.n_cells:
                        boundary = boundary.clean()
            else:
                boundary = excavation_boundary(whole_display, part.void, geo.excavation.contact_tolerance)
        if boundary is not None and boundary.n_cells > 0:
            boundary_info = {**boundary_info, "faces": int(boundary.n_cells), "area": float(boundary.area),
                             "connected_regions": int(boundary.connectivity().cell_data["RegionId"].max() + 1)}
            with t("write"):
                info = publish(boundary, "excavation_surface.vtp", False)
            layers.append({"id": "excavation", "label": "Excavation surface", "kind": "excavation",
                           "role": "primary" if geo.primary == "excavation" else "supplementary", **info})
    if geo.exterior.enabled:
        with t("exterior"):
            exterior = exterior_surface(part, geo.exterior.split_by_group)
            internal = None
            if internal_mode != "keep":
                exterior, internal, n_internal = split_internal_faces(exterior, part.solid,
                                                                      geo.exterior.internal_faces_method)
                boundary_info["internal_contact_faces"] = n_internal
                log(f"[{spec.name}] internal block-contact faces removed from the exterior: {n_internal}")
        with t("write"):
            info = publish(exterior, "exterior_surface.vtp", False)
        layers.insert(0, {"id": "exterior", "label": "Exterior surface", "kind": "exterior",
                          "role": "primary" if geo.primary == "exterior" else "supplementary", **info})
        if internal is not None and internal_mode == "layer" and internal.n_cells:
            with t("write"):
                info = publish(internal, "internal_faces.vtp", False)
            layers.append({"id": "internal", "label": "Internal block contacts", "kind": "internal_faces",
                           "role": "supplementary", "default_visible": False, **info})

    sections = {}
    per_group_used = geo.display_averaging == "per_group" and part.group_codes is not None
    if cfg.sections.enabled:
        with t("sections"):
            positions = section_positions(part.solid.bounds, cfg.sections)
            per_group = geo.display_averaging == "per_group" and part.group_codes is not None
            per_group = per_group and not cfg.sections.preserve_discontinuities
            blocks = [with_display_points(b) for b in part.blocks] if per_group else None
            recompute = cfg.sections.magnitude == "vector_norm" and bool(cfg.fields.displacement.name)
            point_stress = summary.stress_association == "point"
            for axis, values in positions.items():
                entries = []
                for value in values:
                    if cfg.sections.preserve_discontinuities:
                        cut = section_discontinuous(whole_display, axis, value, cfg.sections.min_points)
                    elif per_group:
                        cut = section_per_group(blocks, axis, value, cfg.sections.min_points)
                    else:
                        cut = section_whole(whole_display, axis, value, cfg.sections.min_points)
                    if cut is None:
                        continue
                    if recompute and {"X_Disp", "Y_Disp", "Z_Disp"} <= set(cut.point_data.keys()):
                        vec = np.column_stack([np.asarray(cut.point_data[c], dtype=np.float64)
                                               for c in ("X_Disp", "Y_Disp", "Z_Disp")])
                        cut.point_data["TotalDisplacement"] = np.linalg.norm(vec, axis=1)
                    if point_stress and cfg.fields.stress.name in cut.point_data.keys():
                        # nodal stress: principal values from the interpolated tensor, not
                        # interpolated eigenvalues (which are not linear in the components)
                        eig = principal_values(np.asarray(cut.point_data[cfg.fields.stress.name], dtype=np.float64),
                                               summary.stress_order)
                        for k, name in enumerate(("Stress_Min_Principal", "Stress_Mid_Principal",
                                                  "Stress_Max_Principal")):
                            cut.point_data[name] = eig[:, k]
                    info = publish(cut, f"sections/slice_{axis}_{format_position(value)}.vtp", True)
                    entries.append({"value": float(value), **info})
                sections[axis] = entries
    n_sections = sum(len(v) for v in sections.values())
    log(f"[{spec.name}] layers: {[l['id'] for l in layers]}, sections: {n_sections}")

    constant = geo.groups.constant_fallback if part.group_codes is not None and not geo.groups.field else ""
    meta = field_metadata(cfg, summary, constant)
    present = set(publish.ranges)
    pct = publish.percentiles()
    stage_fields = {}
    for name in sorted(present, key=lambda n: (FIELD_ORDER.index(n) if n in FIELD_ORDER else 99, n)):
        if name not in meta:
            continue
        lo, hi = publish.ranges[name]
        stage_fields[name] = {"min": lo, "max": hi, **pct.get(name, {})}

    index = {"id": spec.name, "label": spec.label or spec.name, "source": source,
             "void": {"method": void.method, "cells": void.n_void},
             "mesh_regions": regions, "internal_faces": internal_mode,
             "stress_component_order": {"order": ",".join(order), "source": order_source} if order else None,
             "layers": layers, "sections": sections,
             "section_rules": {"placement": cfg.sections.placement, "spacing": cfg.sections.spacing,
                               "displacement_magnitude": cfg.sections.magnitude,
                               "preserve_discontinuities": cfg.sections.preserve_discontinuities,
                               "point_stress_principal": ("from interpolated tensor"
                                                          if summary.stress_association == "point" else None),
                               "display_averaging": geo.display_averaging if per_group_used else "whole_solid"},
             "fields": stage_fields}
    total_bytes = sum(p.stat().st_size for p in stage_dir.rglob("*") if p.is_file())
    report = {"stage": spec.name, "seconds": t.times, "output_bytes": total_bytes,
              "primary_bytes": next((l["bytes"] for l in layers if l["role"] == "primary"), None),
              "section_count": n_sections, "void_diagnostics": void.diagnostics, "stress_unit_check": unit_check,
              "excavation_boundary": boundary_info, "triangle_quality": publish.quality_reports}
    return StageResult(index=index, report={**report, "_meta": meta})


def build(cfg: CaseConfig, quality: bool = True, copy_viewer: bool | None = None, log=print) -> BuildResult:
    """Build the static review package described by ``cfg``."""
    started = time.perf_counter()
    out = cfg.output_dir
    cache = cfg.cache_dir
    cache.mkdir(parents=True, exist_ok=True)
    stages = cfg.resolved_stages()
    if not stages:
        raise RuntimeError("No input stages were found")
    results = [build_stage(cfg, spec, cache, quality=quality, log=log) for spec in stages]

    meta: dict = {}
    for r in results:
        meta.update(r.report.pop("_meta"))
    global_ranges: dict[str, dict] = {}
    for r in results:
        for name, rng in r.index["fields"].items():
            g = global_ranges.setdefault(name, {"min": rng["min"], "max": rng["max"]})
            g["min"], g["max"] = min(g["min"], rng["min"]), max(g["max"], rng["max"])
    used = [n for n in meta if n in global_ranges]
    v = cfg.viewer
    index = {
        "schema": INDEX_SCHEMA,
        "generator": {"name": "sim2web", "version": __version__},
        "title": cfg.title or v.title,
        "description": cfg.description,
        "solver": cfg.solver,
        "config_sha256": cfg.sha256,
        "viewer": {"title": v.title or cfg.title, "subtitle": v.subtitle,
                   "default_field": v.default_field or (used[0] if used else ""),
                   "default_axis": v.default_axis or next(iter(cfg.sections.axes), ""),
                   "colormap": v.colormap, "bands": v.bands, "background": v.background,
                   "range_mode": v.range_mode, "length_unit": v.length_unit},
        "fields": {n: meta[n] for n in sorted(used, key=lambda n: (FIELD_ORDER.index(n) if n in FIELD_ORDER else 99, n))},
        "ranges": global_ranges,
        "stages": [r.index for r in results],
    }
    index_path = cache / "index.json"
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if copy_viewer if copy_viewer is not None else cfg.output.viewer:
        from .site import ViewerNotBuilt, install_viewer

        try:
            install_viewer(out)
        except ViewerNotBuilt as exc:
            log(f"WARNING: data products written, but the viewer was not copied. {exc}")

    report = {"sim2web": __version__, "python": platform.python_version(), "platform": platform.platform(),
              "pyvista": pv.__version__, "vtk": pv.vtk_version_info and ".".join(map(str, pv.vtk_version_info)),
              "numpy": np.__version__, "config_sha256": cfg.sha256, "seconds_total": time.perf_counter() - started,
              "stages": [r.report for r in results]}
    report_path = cache / "build_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    log(f"Index written to {index_path}")
    return BuildResult(out, index_path, report_path, results)
