# Field semantics

| Field family | Authoritative association | Rendering |
|---|---|---|
| displacement components/magnitude | PointData | continuous |
| stress tensor components/principal stresses | CellData | exact cell colors |
| optional stress copy on points | PointData | display-only interpolation |
| material/group identifiers | CellData | categorical/discrete |

The viewers prefer exact stress CellData.  Categorical identifiers are never
interpolated.  Float64-to-Float32 conversions, where made by an existing case
processor for browser size, are measured in the closure field audit and are not
described as lossless.

Displacement is labelled in metres.  Stress display units are case-specific:
the cavern case retains its supplied MPa convention; the FLAC3D and 3DEC slope
cases use Pa.  The processing scripts do not rescale values.
