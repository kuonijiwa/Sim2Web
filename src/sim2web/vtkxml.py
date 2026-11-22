"""Light-weight reading of VTK XML metadata without loading the data.

VTK XML files may name the components of a multi-component array
(``ComponentName0="XX" ...``).  When the exporter writes these names they are
the most direct evidence of the component order, so Sim2Web reads them and
checks them against the configuration.
"""
from __future__ import annotations

import mmap
import re
from pathlib import Path

_TAG = re.compile(rb"<DataArray\b[^>]*>")
_ATTR = re.compile(rb'(\w+)="([^"]*)"')


def data_array_attributes(path: str | Path) -> list[dict[str, str]]:
    """Attributes of every ``<DataArray>`` tag in a VTK XML file.

    Inline base64 data contains no ``<`` and appended raw data follows the
    ``<AppendedData`` marker, so scanning for tags is safe and fast.
    """
    out = []
    with open(path, "rb") as stream:
        with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
            end = data.find(b"<AppendedData")
            region = data[: end if end >= 0 else len(data)]
            for match in _TAG.finditer(region):
                attrs = {k.decode(): v.decode(errors="replace") for k, v in _ATTR.findall(match.group(0))}
                out.append(attrs)
    return out


def component_names(path: str | Path) -> dict[str, list[str]]:
    """``{array name: [component names]}`` for arrays that declare them."""
    names: dict[str, list[str]] = {}
    for attrs in data_array_attributes(path):
        n = int(attrs.get("NumberOfComponents", "1") or 1)
        comps = [attrs.get(f"ComponentName{i}") for i in range(n)]
        if attrs.get("Name") and n > 1 and all(comps):
            names[attrs["Name"]] = [c.strip().upper() for c in comps]
    return names
