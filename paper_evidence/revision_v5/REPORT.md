# Sim2Web r6 验证交付

在同一台 Windows 工作站测量公开算例 A、C 的浏览器端剖切、trame 几何和图像交付、Sim2Web 构建时剖面。LAN 和模拟 Site 4G 共 16 组，完成 80 次冷启动和 800 次计时切换。浏览器端与 vtkCutter 对照的剖面通过 6/6。

算例 A 的浏览器端剖切在 4G 下 5/5 次冷启动显示首帧，首帧用时中位数 14.318 s，完整体网格 gzip 载荷 31.60 MB。

4G 下 A 的 trame 几何和图像交付首帧中位数分别为 2.452 s 和 1.861 s，两种交付方式均需运行 VTK 服务。

4G 下 A 的 Sim2Web 首帧总传输 4.81 MB，重复切换中位数 31.1 ms，重复轮次可复用内存里的 VTP。

在 LAN 上，算例 A 的浏览器端剖切和 Sim2Web 重复切换中位数分别为 31.3 ms 和 31.0 ms，本次 trame 远程图像模式等待对应图像到达的中位数为 618.0 ms。

浏览器端和服务端剖切支持任意位置，Sim2Web 的剖面位置在构建时固定，发布后若要加入新位置就需要重新构建。

## 表 6

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

## 公平性

| 公平性检查 | 结果 | 依据 |
|---|---|---|
| 同位置、位移场、色图、窗口和相机 | 是 | 每案从发布索引等距取十个 x 位置。只显示位移模长剖面，均用 jet 八色阶、同案 full range、相同 x 向正交相机和 1600×900 窗口。LAN 和 4G 的末位置实拍与浏览器端并排核对，轮廓重合度见 `frame_check.json`。 |
| 首次加载为新 profile 和冷 HTTP 缓存 | 是 | Chrome 进程逐次新起，CDP 禁用 HTTP 缓存。服务端先加载模型，服务启动和模型准备时间单计。 |
| 重复测试的应用缓存机制等同 | 否 | Sim2Web 保留其默认 VTP 内存 LRU。B 重切，trame 重切并传输。原始记录附首次扫过位置的延迟和 W 的 cached 字段。 |
| 同一帧完成定义 | 是 | 剖面绘制完成或对应剖面编号的服务端图像成功解码后等待两个浏览器动画帧。trame 切换同时核对了服务端修订号。 |
| Site 4G 作用到 trame WebSocket | 是 | 本机 256 KiB 双向回显验证 Chrome CDP 会限速，正式试验不额外叠加帧代理。 |
| 使用可比 GPU | 是 | 浏览器端为 Chrome WebGL 报告的 Intel UHD / ANGLE D3D11。S-remote 的实际模型绘制在服务进程，Chromium 只解码公开样例图像。 |

## 异常和补测

旧图 LFS 对象下载返回 404。Worker 请求计数修正后重新执行了浏览器端正确性和正式测试。截图发现 Sim2Web 裁剪范围和 trame 本地相机投影存在差异，两种基准的相机校正后重新测量。远程 trame 用编号色块核对 JPEG，剔除上一张剖面的延迟帧。算例 C 的 Float32 传输导致少量原始坐标顶点无法在 1 mm 容差内匹配，按传输精度重切参考后双向全部匹配。所有试验退出码与日志位置见 COMMANDS.csv，详见 `web_slicing/REPORT.md`。

## 图 1

`figures/fig1_architecture.svg`、`figures/fig1_architecture.pdf`、`figures/fig1_architecture.png`（600 dpi）和可编辑的 `figures/draw_figure1.py`。最终印刷尺寸 16.5 × 7.0 cm，最小字号 8.1 pt。
