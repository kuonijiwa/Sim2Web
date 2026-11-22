# Table 6. Sectioning in the browser on the Windows workstation

A / C means Case A followed by Case C. MB uses decimal bytes. Browser memory is peak CDP JS heap / peak summed Chrome working set. First view uses the median of five cold browser launches. Switch latencies are median / p95 for 50 changes after one ten-position warm-up sweep.

## LAN

| Item | Browser-side slicing | Server-side slicing (trame) | Sim2Web build-time sections |
|---|---|---|---|
| Transfer before first section (MB) | A 31.77 / C 11.97 | Local A 3.72 / C 3.44<br>Remote A 2.15 / C 2.05 | A 4.81 / C 3.22 |
| Time to first section (s) | A 0.977 / C 0.746 | Local A 0.673 / C 0.718<br>Remote A 0.906 / C 0.875 | A 1.262 / C 1.131 |
| Browser memory peak (MB) | A 7.79 / 793.33 / C 7.15 / 798.59 | Local A 11.04 / 734.09 / C 10.80 / 749.60<br>Remote A 7.28 / 1137.42 / C 7.28 / 1137.06 | A 17.03 / 847.15 / C 17.03 / 863.52 |
| Server memory peak (MB) | A — / C — | Local A 666.91 / C 322.16<br>Remote A 667.62 / C 596.28 | A — / C — |
| Server start + model ready (s) | A — / C — | Local A 9.235 / C 4.656<br>Remote A 9.743 / C 4.650 | A — / C — |
| Per-section switch (ms) | A 31.3 / 32.1 / C 31.0 / 31.7 | Local A 71.5 / 82.0 / C 43.1 / 68.9<br>Remote A 618.0 / 634.1 / C 599.8 / 613.5 | A 31.0 / 31.8 / C 31.1 / 32.1 |
| Server CPU for 50 switches (s) | A — / C — | Local A 2.297 / C 1.422<br>Remote A 4.125 / C 3.406 | A — / C — |
| Server needed | Static hosting suffices | Running VTK/trame service | Static hosting suffices |
| Section position | Arbitrary | Arbitrary | Fixed during the build |
| Values checked | JS cuts vs vtkCutter | Server vtkCutter arrays vs independent reference export | sim2web validate |

## Site 4G

| Item | Browser-side slicing | Server-side slicing (trame) | Sim2Web build-time sections |
|---|---|---|---|
| Transfer before first section (MB) | A 31.77 / C 11.97 | Local A 3.72 / C 3.44<br>Remote A 2.15 / C 2.06 | A 4.81 / C 3.22 |
| Time to first section (s) | A 14.318 / C 5.817 | Local A 2.452 / C 2.325<br>Remote A 1.861 / C 1.853 | A 3.029 / C 2.220 |
| Browser memory peak (MB) | A 7.06 / 816.48 / C 7.06 / 800.99 | Local A 11.16 / 760.71 / C 11.15 / 781.82<br>Remote A 7.30 / 1130.75 / C 7.27 / 1136.68 | A 17.35 / 864.51 / C 17.27 / 847.74 |
| Server memory peak (MB) | A — / C — | Local A 667.44 / C 322.09<br>Remote A 667.04 / C 600.25 | A — / C — |
| Server start + model ready (s) | A — / C — | Local A 9.243 / C 4.632<br>Remote A 9.225 / C 4.655 | A — / C — |
| Per-section switch (ms) | A 31.3 / 31.8 / C 31.1 / 31.9 | Local A 91.7 / 107.6 / C 74.5 / 91.8<br>Remote A 648.6 / 714.0 / C 618.9 / 644.8 | A 31.1 / 32.1 / C 30.7 / 31.8 |
| Server CPU for 50 switches (s) | A — / C — | Local A 2.141 / C 1.391<br>Remote A 4.406 / C 3.500 | A — / C — |
| Server needed | Static hosting suffices | Running VTK/trame service | Static hosting suffices |
| Section position | Arbitrary | Arbitrary | Fixed during the build |
| Values checked | JS cuts vs vtkCutter | Server vtkCutter arrays vs independent reference export | sim2web validate |

The trame entries count WebSocket payload bytes plus CDP HTTP response bytes. WebSocket framing and TCP overhead are excluded.
Sim2Web's stock LRU served warmed repetitions in this protocol. See results.json for the first, unwarmed sweep and the exact cached flags.
