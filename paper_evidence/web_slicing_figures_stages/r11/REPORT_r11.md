# Sim2Web 论文插图 r11

2026-11-23，Windows 工作站。按稿件文件夹中的任务说明和版式草图重做图 2–7，图 1 沿用现有版本。
已在实际发布查看器的 Colour map 下拉列表中核对 Turbo，并在截图中检查当前色谱为 Turbo、色带数为 8。因此无需添加色谱预设，本次提交集中在论文证据目录。

| 下载的输入 | SHA-256 |
|---|---|
| CODEX_TASK_r11_figure_redesign.md | e02fbe8c7b979cd90b5dcaf14fb833c05aa47e33fba69c1d809326c49f3ceef9 |
| figure_wireframes.png | b7e6bcc0455a43d4e96e0a8550c72db47267e42e4c5d2f92671d044ef182de7b |

## 图 2 · 算例 D 工作台与发布结果

(a) EXC12_dis 的工作台六个步骤和通过验证后的诊断栏。第 3 步“Geometry and excavation”为当前步骤。六步名义印刷字号 6.45 pt，诊断正文 5.48 pt。

| 诊断 | 截图中的文字 |
|---|---|
| Model | 548,417 cells, 332,510 points |
| Stress component order | Read from the file: XX, YY, ZZ, XY, XZ, YZ |
| Stress unit | MPa: implied unit weight 14.6 kN/m³ |
| Excavation surface (EXC12_dis) | 17,004 faces, 6,418 m² |
| Mesh interfaces (EXC12_dis) | 85,215 faces with rock on both sides left out of the excavation surface |
| Internal faces (EXC12_dis) | 89,901 block-contact faces removed from the exterior |
| Validation | Every published value matches the source model |

(b) 同一构建的 EXC12_dis，位移模量 |u| 的 P5–P95 为 [4.841852915e-05, 0.005555023812] m，Turbo 8 档，方位 / 俯视 / 滚转 228° / 35° / -48°，平行投影，无剖面。外表面 20%（#D9D9D9）、开挖面 100%（turbo）。灰色地表取自原始外表面在 z = 11 m 的 1,405 个面。Sim2Web 0.2.0 的原构建耗时 60.23 s。独立验证检查 114 个产品，精确值不符 0，验证通过。

## 图 3 · 算例 A 完整发布查看器

五施工步包的 IV-2。1600 × 900 CSS px，deviceScaleFactor 3。保留 16:9 完整窗口、应用控件和原生图例，无编号标注。左栏从上到下显示施工步、物理量、图层和剖面控制，右栏显示点选详情及色标。
平行投影，方位 / 俯视 / 滚转 211° / 31° / 0°。剖面 100%（turbo）、开挖面 100%（turbo）。最小主应力 σ3 的 P5–P95 为 [-8.665175247, -4.004510689] MPa，Turbo 8 档。剖面滑块显示 X = 38.0 m · 33 / 77 · 708 KiB。实际点选剖面得到 Source_Cell_ID 320050、σ3 = -6.329 MPa。关闭渲染器的光照着色以显示完整色带，按截图中的几何投影框取景。界面字体沿用应用样式，名义印刷字号 3.07–3.65 pt，色标也保留应用原有的边界刻度。

## 图 4 · A–F 发布结果

三行两列。均为平行投影，Turbo 8 档，短标题和三刻度。B、E 的值按原包的 Pa 渲染，合成色标换算为 MPa。D 提高俯视角展示开挖内部，灰色上下文是原始外表面 z = 11 m 的地表多边形。C 显示外表面。A 的探针读数集中在图 3。

| 算例 | 字段 | 色标实际范围 | 剖面 | 方位 / 俯视 / 滚转 | 图层与不透明度 |
|---|---|---|---|---|---|
| A | σ3 (MPa) | [-8.703127909, -4.034004283] MPa | X = 38 m | 216° / 30° / 0° | 剖面 100%（turbo）、开挖面 100%（turbo） |
| B | σ1 (MPa) | [-1.990911875, 0.02046005273] MPa | Y = -185 m | 225° / 32° / -5° | 外表面 20%（#D9D9D9）、开挖面 100%（turbo）、剖面 100%（turbo） |
| C | &#124;u&#124; (m) | [1.438477248e-05, 0.001442155219] m | 无 | 298° / 33° / -26° | 外表面 100%（turbo） |
| D | u_y (m) | [-0.00164439542, 0.001503035688] m | 无 | 228° / 43° / -58° | 外表面 20%（#D9D9D9）、开挖面 100%（turbo） |
| E | σ3 (MPa) | [-2.068770025, -0.2796225656] MPa | 无 | 240° / 32° / 5° | 外表面 100%（turbo） |
| F | &#124;u&#124; (m) | [0.0001206894303, 0.004404990375] m | Y = 370 m | 275° / 32° / -26° | 外表面 20%（#D9D9D9）、剖面 100%（turbo） |

## 图 5 · 算例 A 主应力核对

使用 IV-2 的 983,438 个非零应力单元重新计算。横轴是按 XX、YY、ZZ、XY、XZ、YZ 分量顺序计算的参考主应力，纵轴是通用 VTK 过滤器所得主应力，均为 MPa。方形坐标轴、虚线表示 1∶1，浅色区表示通用结果大于零。公共 Turbo 对数色标从 1 到 291,332 个样本/六边形，三处刻度采用最小值、几何中值和最大值。轴标题 8 pt，刻度和误差框 7 pt。

| 主应力 | 共同绘图范围（MPa） | 最大绝对误差（MPa） | 占参考范围 | 只在通用结果中受拉的单元 |
|---|---|---:|---:|---:|
| σ1 maximum | [-12.6324, 2.11111] | 7.21517 | 56.540% | 14,711 |
| σ2 intermediate | [-24.3438, 0.12869] | 10.57792 | 76.130% | 7 |
| σ3 minimum | [-45.15, -0.00101483] | 3.83764 | 8.500% | 0 |

## 图 6 · 算例 C 内部面去除

上排两个不透明全模型由 PyVista 0.46.3 渲染，平行投影，方位 / 俯视 / 滚转 298° / 31° / -30°，相机、范围和配色完全相同。位移模量 |u| 的 P5–P95 为 [1.438477248e-05, 0.001442155219] m，使用 Matplotlib Turbo 均匀采样 8 色带。使用 r4 记录及留存表面文件，(a) 917,062 面、187,591,097 B（187.6 MB），(b) 21,293 面、2,620,417 B（2.6 MB），相差 43.07 倍。红框覆盖相同的投影视域，下排在同方向放大 3.33 倍，仅绘制深灰色线框（#45494D，0.7 线宽，46% 不透明度）。左边为保留的内部接触面和外部边线，右边为去除后外部边线。上排渲染图的非背景像素中，最大通道差不超过 20/255 的占 99.99964%。该比较在叠加红框前进行。面数和文件大小见 comparison_paraview_glance/windows_r4/comparison_results.json。

## 图 7 · 算例 A 施工步

箭头串联 I-1、II-2、IV-2，只显示不透明开挖面。面数分别为 20,142 / 27,837 / 49,677。共用平行投影相机和裁切框，方位 / 俯视 / 滚转 239° / 30° / 0°，无剖面。最小主应力 σ3 使用五施工步开挖面合并后的 P5–P95 [-12.24739528, -1.102368563] MPa，Turbo 8 档。

## 截图样式和取景设置

图 2 的工作台沿用原字体和措辞，截图时调整纵向内边距和最小行高。规则如下。

```css
.steps .step { min-height: 32px !important; padding-block: 4px !important; }
.diagnostics li { padding-block: 3px !important; margin-block: 2px !important; }
```

图 2(b)、4 和 7 隐藏查看器控制栏与原生色标，在合成图上绘制色标。规则如下。

```css
.panel, .right { display: none !important; }
```

图 3 无 CSS 注入。截图服务器仅在本地运行时关闭方向标，在截图实例内同步关闭模型光照，保留原生界面和真实点选事件。透明背景图层设置为 #D9D9D9、20%。D 的灰色地表取自构建产品中的地表面，源文件和发布产品未改写。图 5、6 分别通过 Matplotlib、PyVista 绘制。

## 印刷规格和运行记录

所有 PNG 为 16.5 cm 宽、RGB、600 dpi。图 5 PDF 也是 16.5 cm 宽，字体为 Arial，核对无嵌入栅格图。
逐图有效 DPI、单位、色限、带数、相机参数和 SHA-256 见 print_check.json。

| 图 | 尺寸（cm） | 最小有效 DPI | 最小文字（pt） | PNG（MB） |
|---|---|---:|---:|---:|
| 2 | 16.50 × 11.29 | 624.8 | 5.48 | 1.109 |
| 3 | 16.50 × 9.28 | 738.9 | 3.07 | 1.442 |
| 4 | 16.50 × 16.02 | 1113.6 | 7.00 | 1.663 |
| 5 | 16.50 × 5.62 | 600.0 | 7.00 | 0.344 |
| 6 | 16.50 × 11.22 | 854.0 | 7.00 | 6.482 |
| 7 | 16.50 × 4.17 | 1252.7 | 7.00 | 0.674 |

COMMANDS.csv 记录制作命令、退出码、耗时及日志。首次图 2 截图向 Playwright 传入了 URL 对象，改为实际 URL 字符串后通过。首次图 5 命令的 PowerShell 参数与自动变量重名，修正后成功。

| 步骤 | 命令 | 退出码 | 耗时（秒） |
|---|---|---:|---:|
| r11_capture_47 | `node paper_evidence/web_slicing_figures_stages/r11/capture_figures.mjs C:/swv_r7_20261121/view_states_local.json examples/flac3d_cavern_stages/site C:/swv_fig2_native_20261122/project/site http://127.0.0.1:18811 C:/swv_r11_20261123/captures 47` | 0 | 17.109 |
| r11_capture_3 | `node paper_evidence/web_slicing_figures_stages/r11/capture_figures.mjs C:/swv_r7_20261121/view_states_local.json examples/flac3d_cavern_stages/site C:/swv_fig2_native_20261122/project/site http://127.0.0.1:18811 C:/swv_r11_20261123/captures 3` | 0 | 6.404 |
| r11_capture_2 | `node paper_evidence/web_slicing_figures_stages/r11/capture_figures.mjs C:/swv_r7_20261121/view_states_local.json examples/flac3d_cavern_stages/site C:/swv_fig2_native_20261122/project/site http://127.0.0.1:18811 C:/swv_r11_20261123/captures 2` | 1 | 3.180 |
| r11_capture_2_retry | `node paper_evidence/web_slicing_figures_stages/r11/capture_figures.mjs C:/swv_r7_20261121/view_states_local.json examples/flac3d_cavern_stages/site C:/swv_fig2_native_20261122/project/site http://127.0.0.1:18811 C:/swv_r11_20261123/captures 2` | 0 | 6.539 |
| r11_case_c | `C:/swv_r4_20261121/venv/Scripts/python.exe paper_evidence/web_slicing_figures_stages/r11/render_case_c.py C:/swv_r4_20261121/pv_baselines_corrected/C/surface.vtp C:/swv_r4_20261121/model_runs/C/site/model_cache/slopemodel/exterior_surface.vtp C:/swv_r11_20261123/plots` | 0 | 8.982 |
| r11_hexbin | `C:/swv_r4_20261121/venv/Scripts/python.exe paper_evidence/web_slicing_figures_stages/r11/plot_principal.py examples/flac3d_cavern_iv2/input/IV-2.vtu C:/swv_r11_20261123/plots` | 1 | 2.992 |
| r11_hexbin_final | `C:/swv_r4_20261121/venv/Scripts/python.exe paper_evidence/web_slicing_figures_stages/r11/plot_principal.py examples/flac3d_cavern_iv2/input/IV-2.vtu C:/swv_r11_20261123/plots` | 0 | 14.885 |
| r11_case_c_final | `C:/swv_r4_20261121/venv/Scripts/python.exe paper_evidence/web_slicing_figures_stages/r11/render_case_c.py C:/swv_r4_20261121/pv_baselines_corrected/C/surface.vtp C:/swv_r4_20261121/model_runs/C/site/model_cache/slopemodel/exterior_surface.vtp C:/swv_r11_20261123/plots` | 0 | 9.683 |
| r11_capture_final | `node paper_evidence/web_slicing_figures_stages/r11/capture_figures.mjs C:/swv_r7_20261121/view_states_local.json examples/flac3d_cavern_stages/site C:/swv_fig2_native_20261122/project/site http://127.0.0.1:18811 C:/swv_r11_20261123/captures 247` | 0 | 19.848 |
| r11_compose | `C:/swv_r4_20261121/venv/Scripts/python.exe paper_evidence/web_slicing_figures_stages/r11/compose_figures.py C:/swv_r11_20261123` | 0 | 13.384 |
| r11_hexbin_three_ticks | `C:/swv_r4_20261121/venv/Scripts/python.exe paper_evidence/web_slicing_figures_stages/r11/plot_principal.py examples/flac3d_cavern_iv2/input/IV-2.vtu C:/swv_r11_20261123/plots` | 0 | 9.674 |
| r11_case_c_framing | `C:/swv_r4_20261121/venv/Scripts/python.exe paper_evidence/web_slicing_figures_stages/r11/render_case_c.py C:/swv_r4_20261121/pv_baselines_corrected/C/surface.vtp C:/swv_r4_20261121/model_runs/C/site/model_cache/slopemodel/exterior_surface.vtp C:/swv_r11_20261123/plots` | 0 | 7.393 |
| r11_capture_4_framing | `node paper_evidence/web_slicing_figures_stages/r11/capture_figures.mjs C:/swv_r7_20261121/view_states_local.json examples/flac3d_cavern_stages/site C:/swv_fig2_native_20261122/project/site http://127.0.0.1:18811 C:/swv_r11_20261123/captures 4` | 0 | 9.951 |
| r11_compose_final | `C:/swv_r4_20261121/venv/Scripts/python.exe paper_evidence/web_slicing_figures_stages/r11/compose_figures.py C:/swv_r11_20261123` | 0 | 12.346 |
| r11_verify | `C:/swv_r4_20261121/venv/Scripts/python.exe paper_evidence/web_slicing_figures_stages/r11/verify_figures.py C:/swv_r11_20261123/delivery; node --check paper_evidence/web_slicing_figures_stages/r11/capture_figures.mjs; git diff --exit-code 2eb347c -- src/ viewer/src/ paper_evidence/web_slicing_figures_stages/r10/fig1_architecture.png paper_evidence/web_slicing_figures_stages/r10/fig1_architecture.pdf` | 0 | 1.074 |
