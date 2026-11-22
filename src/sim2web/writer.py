"""Writing VTP products for static browser delivery."""
from __future__ import annotations

import hashlib
from pathlib import Path

import vtk


def write_vtp(mesh, path: str | Path, compression_level: int = 9) -> None:
    """Write XML PolyData in appended mode with zlib compression.

    Appended binary data is read directly by the vtk.js XML reader.
    """
    writer = vtk.vtkXMLPolyDataWriter()
    writer.SetFileName(str(path))
    writer.SetInputData(mesh)
    writer.SetDataModeToAppended()
    writer.SetCompressorTypeToZLib()
    writer.SetCompressionLevel(compression_level)
    if writer.Write() != 1:
        raise OSError(f"VTK failed to write {path}")


def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()
