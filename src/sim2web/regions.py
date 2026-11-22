"""Identification of excavated (void) cells and diagnostics for that choice.

Numerical models represent excavation in different ways: FLAC3D null zones
carry zero stress, some exports carry an explicit group label, and other
workflows supply a dedicated flag array.  The strategy is therefore declared
in the case configuration; this module applies it and reports the evidence a
user needs to judge whether the classification is plausible.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class VoidResult:
    mask: np.ndarray
    method: str
    diagnostics: dict = field(default_factory=dict)

    @property
    def n_void(self) -> int:
        return int(self.mask.sum())


def max_abs_stress(mesh, stress_name: str) -> np.ndarray:
    return np.max(np.abs(np.asarray(mesh.cell_data[stress_name])), axis=1)


def label_void_mask(mesh, label_fields, tokens) -> tuple[np.ndarray, list[str]]:
    """Cells whose label (case-insensitive) contains any token."""
    mask = np.zeros(mesh.n_cells, dtype=bool)
    used = []
    for name in label_fields:
        if name not in mesh.cell_data:
            continue
        values = np.char.lower(np.asarray(mesh.cell_data[name]).astype(str))
        hit = np.zeros(mesh.n_cells, dtype=bool)
        for token in tokens:
            hit |= np.char.find(values, token.lower()) >= 0
        if hit.any():
            used.append(name)
        mask |= hit
    return mask, used


def stress_void_mask(mesh, stress_name: str, threshold: float) -> np.ndarray:
    """Cells whose six stress components are all below ``threshold`` in magnitude."""
    if stress_name not in mesh.cell_data:
        raise ValueError(f"A stress-based void criterion needs cell (zone) stress; '{stress_name}' is nodal. "
                         "Use strategy labels, field or removed_zones.")
    return np.all(np.abs(np.asarray(mesh.cell_data[stress_name])) < threshold, axis=1)


def identify_void(mesh, cfg) -> VoidResult:
    """Apply the configured strategy and collect diagnostics."""
    exc = cfg.geometry.excavation
    stress = cfg.fields.stress.name
    label_fields = exc.label_fields or cfg.category_names
    if not exc.enabled:
        return VoidResult(np.zeros(mesh.n_cells, dtype=bool), "disabled")

    if exc.strategy == "removed_zones":
        result = VoidResult(np.zeros(mesh.n_cells, dtype=bool), "removed_zones (no void cells in the export)")
        result.diagnostics = void_diagnostics(mesh, result.mask, cfg)
        return result
    if exc.strategy == "field":
        mask = np.asarray(mesh.cell_data[exc.void_field]).astype(bool)
        method = f"field:{exc.void_field}"
    elif exc.strategy == "labels":
        mask, used = label_void_mask(mesh, label_fields, exc.label_tokens)
        method = f"labels:{','.join(used) or 'none-matched'}"
    elif exc.strategy == "stress":
        mask = stress_void_mask(mesh, stress, exc.null_threshold)
        method = "stress"
    else:  # labels_then_stress
        mask, used = label_void_mask(mesh, label_fields, exc.label_tokens)
        method = f"labels:{','.join(used)}"
        if not mask.any():
            mask = stress_void_mask(mesh, stress, exc.null_threshold)
            method = "stress (no label matched)"

    result = VoidResult(mask, method)
    result.diagnostics = void_diagnostics(mesh, mask, cfg)
    if exc.required and not mask.any():
        raise RuntimeError("geometry.excavation.required is true but no void cells were identified")
    return result


def void_diagnostics(mesh, mask: np.ndarray, cfg) -> dict:
    """Evidence for judging the void classification.

    * counts of void and retained cells;
    * a log10 histogram of max |stress| for retained and void cells, which
      should be separated by a clear gap when a stress criterion is used;
    * the number of retained cells with max |stress| below
      ``near_null_factor * null_threshold`` (cells at risk of misclassification);
    * agreement with label-based classification when labels are available.
    """
    exc = cfg.geometry.excavation
    diag: dict = {"void_cells": int(mask.sum()), "retained_cells": int((~mask).sum()),
                  "strategy": exc.strategy, "null_threshold": exc.null_threshold,
                  "contact_tolerance": exc.contact_tolerance}
    stress = cfg.fields.stress.name
    if stress and stress in mesh.cell_data:
        m = max_abs_stress(mesh, stress)
        positive = m[m > 0]
        floor = float(np.log10(positive.min())) if positive.size else 0.0
        logm = np.log10(np.where(m > 0, m, 10 ** (floor - 1)))
        edges = np.arange(np.floor(logm.min()), np.ceil(logm.max()) + 1.0, 1.0)
        if edges.size < 2:
            edges = np.array([np.floor(logm.min()), np.floor(logm.min()) + 1.0])
        diag["max_abs_stress_log10_bins"] = edges.tolist()
        diag["histogram_retained"] = np.histogram(logm[~mask], bins=edges)[0].tolist()
        diag["histogram_void"] = np.histogram(logm[mask], bins=edges)[0].tolist()
        diag["zero_stress_cells"] = int((m == 0).sum())
        retained = m[~mask]
        diag["retained_min_max_abs_stress"] = float(retained.min()) if retained.size else None
        void = m[mask]
        diag["void_max_max_abs_stress"] = float(void.max()) if void.size else None
        limit = exc.near_null_factor * exc.null_threshold
        diag["near_null_retained_cells"] = int((retained < limit).sum())
        diag["near_null_limit"] = limit
        if retained.size and void.size and void.max() > 0:
            diag["separation_decades"] = float(np.log10(max(retained.min(), 1e-300)) - np.log10(void.max()))
    label_fields = exc.label_fields or cfg.category_names
    if label_fields:
        lmask, used = label_void_mask(mesh, label_fields, exc.label_tokens)
        if used:
            inter = int((lmask & mask).sum())
            union = int((lmask | mask).sum())
            diag["label_agreement"] = {"label_fields": used, "label_void_cells": int(lmask.sum()),
                                       "jaccard": inter / union if union else 1.0,
                                       "label_only": int((lmask & ~mask).sum()),
                                       "criterion_only": int((mask & ~lmask).sum())}
    return diag
