# Sim2Web 论文插图 r10

2026-11-22，Windows 工作站。依据 CODEX_TASK_r10_figures.md 制作。浏览器核对索引在本次开始时已指向 A、C、D。逐条统计 r4 原始记录得到 A 180、C 180、D 270，共 630 次成功。对应记录位于 paper_evidence/comparison_paraview_glance/windows_r4/cases/ 各算例的 sim2web_browser.json。

## 图 1 · 处理与发布流程

沿用批准的工作流图。图示输入、Sim2Web 构建、可发布静态包和独立验证之间的关系。原矢量 PDF 使用 Liberation Sans，正文 8 pt，标题 9 pt。PNG 转存为 RGB 并保留 600 dpi。

## 图 2 · 算例 D 工作台与发布结果

(a) 工作台第 3 步“几何与开挖”的步骤栏与诊断栏。(b) 算例 D 的发布查看器，外表面不透明度 35%，开挖面 100%，位移模量 |u| [4.841852915e-05, 0.005555023806] m，Viridis 8 色带，方位 228.0°，俯视 35.0°。按 r10 说明保留 r9 批准版，SHA-256 完全一致，诊断正文约 5.00 pt，色标刻度 5.97 pt。沿用的图 2 指标和图注说明见 ../r9/print_check.json 及 ../r9/REPORT_fig2.md。

## 图 3 · 完整的五施工步网页查看器

Chrome 1440 × 900 CSS px，deviceScaleFactor 3。算例 A 的 IV-2 施工步，最小主应力 σ3 [-8.665175247, -4.004510689] MPa，Jet 8 色带，方位 255.0°，俯视 22.0°。开挖图层可见，不透明度 35%。X = 38 m，滑块显示第 33/77 个切面。实际点选剖面，读数为 Source_Cell_ID 1160199，最小主应力 −6.857 MPa。原生控件与图例字号实测为 3.41–4.06 pt，低于约 5 pt。编号在合成图中绘制，字号 9 pt 粗体。

1. 施工步选择框（IV-2）。
2. 物理量选择框（最小主应力）。
3. 图层列表（开挖面）。
4. X 剖面轴选择和位置滑块。
5. 点选读数与 Source_Cell_ID。
6. 色标。

## 图 4 · A–F 发布结果

各分图均为平行投影，Jet 8 色带。下表保留供复核的实际色限，图中刻度至多三位有效数字。B、E 的包以 Pa 记录，合成色标时将标签换算为 MPa。颜色、断点及源应力数组沿用各自发布包。A 的原生点选也核对到 Source_Cell_ID 1160199，σ3 = −6.857 MPa，读数排在分图下方。

| 算例 | 字段 | 显示色限 | 剖面 | 方位 / 俯视 / 滚转 |
|---|---|---|---|---|
| A | σ3 (MPa) | [-8.703127909, -4.034004283] MPa | X = 38 m | 255° / 22° / 0° |
| B | σ1 (MPa) | [-1.990911875, 0.02046005273] MPa | Y = -185 m | 225° / 32° / -5° |
| C | &#124;u&#124; (m) | [0, 0.01423980203] m | X = 830 m | 240° / 58° / 20° |
| D | u_y (m) | [-0.00164439542, 0.001503035688] m | 无 | 225° / 61° / -60° |
| E | σ3 (MPa) | [-2.068770025, -0.2796225656] MPa | Y = 30 m | 240° / 58° / 5° |
| F | &#124;u&#124; (m) | [0.0001206894303, 0.004404990375] m | Y = 370 m | 240° / 58° / 20° |

## 图 5 · 算例 A 主应力对比

取 IV-2 的 983,438 个非零应力单元。横轴为依据分量名排列计算的主应力，纵轴为直接交给 vtkTensorPrincipalInvariants 的对应结果，单位均为 MPa。文件分量序为 XX、YY、ZZ、XY、XZ、YZ。公共色标为每个六边形单元 1–291,332 个样本，采用对数映射。

| 分图 | 主应力 | 最大绝对误差（MPa） | 占参考范围 | 只在通用结果中受拉的单元 |
|---|---|---:|---:|---:|
| (a) | σ1 maximum | 7.21517 | 56.540% | 14,711 |
| (b) | σ2 intermediate | 10.57792 | 76.130% | 7 |
| (c) | σ3 minimum | 3.83764 | 8.500% | 0 |

## 图 6 · 算例 C 去除内部面前后

PyVista 0.46.3 渲染，平行投影，方位 298.1°，俯视 27.3°，平行尺度 411 m。两图保留 Y ≥ 375 m 的部分以露出内部结构，面不透明度均为 62%，使用同样的细深色网格边。共享位移模量色限 [1.438477248e-05, 0.001442155219] m，Jet 8 色带。截切用于展示，图中面数和大小对应 r4 整张表面文件。

| 分图 | 表面 | 面数 | 字节数 | 图中文字 |
|---|---|---:|---:|---|
| (a) | ParaView Extract Surface | 917,062 | 187,591,097 | 917,062 faces · 187.6 MB |
| (b) | Sim2Web 去除内部接触面 | 21,293 | 2,620,417 | 21,293 faces · 2.6 MB |

数据来自 paper_evidence/comparison_paraview_glance/windows_r4/comparison_results.json 的算例 C 对照记录。实际渲染使用 r4 留存的 C/surface.vtp 和 slopemodel/exterior_surface.vtp，文件大小与记录相符。

## 图 7 · 算例 A 的施工步

依次为 I-1、II-2、IV-2。仅显示开挖面，方位 239.0°，俯视 26.4°，三图相机一致。最小主应力 σ3 [-12.24739528, -1.102368563] MPa，取全部五个施工步开挖面数据合并后的 P5–P95，共享 Jet 8 色带。

## 截图 CSS

图 3 使用原生界面，未注入 CSS。图 4、7 注入同一条规则，用合成图绘制色标。图 6 由 PyVista 渲染。

**图 4、7**

```css
.panel, .right { display: none !important; }
```

图 2 左栏原始截图没有 CSS 注入。右栏继承 r9 已批准图片中的规则。

**图 2 右栏（r9）**

```css
.panel { display: none !important; }
.right { right: 16px !important; top: 50% !important; bottom: auto !important; transform: translateY(-50%); }
.legend { box-shadow: none !important; width: 205px !important; padding: 12px 11px 18px !important; background: #fff !important; }
.legend-title { font-size: 21px !important; line-height: 1.12; }
.legend-sub { font-size: 17px !important; line-height: 1.16; white-space: nowrap; }
.bands { font-size: 20.5px !important; line-height: 1.1; }
.band-row { height: 30px !important; gap: 7px !important; }
.band-row .tick { transform: translateY(-5px) !important; white-space: nowrap; }
.band-row .swatch.tall { height: 30px !important; }
.band-row.last { height: 8px !important; }
```

## 印刷核验

各图宽 16.5 cm，PNG 为 RGB，写入 600 dpi。原生界面字体按实测报告。合成图使用 Arial 或 Liberation Sans，外置分图标签 9 pt 粗体、色标标题 7.5–8 pt、刻度 7 pt、轴标题 8 pt、标注 7.5 pt。图 1、5 另附矢量 PDF。有效分辨率、相机参数、原始色限和 SHA-256 见 print_check.json。

| 图 | PNG 尺寸（px） | 最小分图有效 dpi | 最小文字（pt） | 文件大小（MB） |
|---|---|---:|---:|---:|
| 1 | 3897 × 1511 | 600.0 | 8.00 | 0.274 |
| 2 | 3898 × 2268 | 720.6 | 3.35 | 1.741 |
| 3 | 3898 × 2436 | 665.0 | 3.41 | 1.325 |
| 4 | 3898 × 3350 | 1137.7 | 7.00 | 2.216 |
| 5 | 3897 × 1618 | 600.0 | 7.00 | 0.332 |
| 6 | 3898 × 1945 | 619.0 | 7.00 | 3.047 |
| 7 | 3898 × 1224 | 1090.6 | 7.00 | 0.669 |

## 命令、退出码与耗时

COMMANDS.csv 提供工作目录、开始时间和本地日志名称。图 4 最初两次定位未命中探针，改用保存的相机投影定位后通过。图 6 首次渲染遇到 PyVista 的 Plotter 上下文管理器兼容问题，调整关闭方式后重新渲染。图 5 初稿报告 Arial 缺少 Unicode 下标字形，终稿用基线数字重新导出。

复现截图时，capture_viewers.mjs 读取 view_states.json 和 stage_states.json。view_states.json 的站点路径相对于仓库根目录，需先用 examples 下的配置构建相应站点。图 6 渲染脚本读取上述两份 r4 表面文件。图 1 另附原始绘图脚本。

| 步骤 | 命令 | 退出码 | 耗时（s） |
|---|---|---:|---:|
| r10_fig3_capture | `node capture_viewers.mjs <r7-states> examples/flac3d_cavern_stages/site <r8-camera> C:/swv_r10_20261122/captures 3` | 0 | 7.042 |
| r10_fig7_capture | `node capture_viewers.mjs <r7-states> examples/flac3d_cavern_stages/site <r8-camera> C:/swv_r10_20261122/captures 7` | 0 | 8.138 |
| r10_fig4_capture | `node capture_viewers.mjs <r7-states> examples/flac3d_cavern_stages/site <r8-camera> C:/swv_r10_20261122/captures 4` | 1 | 7.227 |
| r10_fig4_capture_retry | `node capture_viewers.mjs <r7-states> examples/flac3d_cavern_stages/site <r8-camera> C:/swv_r10_20261122/captures 4` | 1 | 4.222 |
| r10_fig4_capture_projected | `node capture_viewers.mjs <r7-states> examples/flac3d_cavern_stages/site <r8-camera> C:/swv_r10_20261122/captures 4` | 0 | 10.200 |
| r10_fig6_render | `python render_contacts.py <r4 ParaView C surface> <r4 Sim2Web C exterior> <figure 4 capture ranges> <r10 render folder>` | 1 | 4.284 |
| r10_fig5_plot | `python plot_principal.py examples/flac3d_cavern_iv2/input/IV-2.vtu <r10 plot folder>` | 0 | 10.898 |
| r10_00_verify_benchmarks | `Check the corrected README links and sum every archived comparison verification` | 0 | 0.149 |
| r10_fig1_sources | `Copy the original editable Figure 1 v2 source from its verified Drive archive` | 0 | 0.041 |
| r10_fig6_render_retry | `python render_contacts.py <r4 ParaView C surface> <r4 Sim2Web C exterior> <figure 4 capture ranges> <r10 render folder>` | 0 | 5.042 |
| r10_fig5_typography | `python plot_principal.py examples/flac3d_cavern_iv2/input/IV-2.vtu <r10 plots>` | 0 | 9.138 |
| r10_fig6_translucency | `python render_contacts.py <r4 C before/after VTP> <fig4 ranges> <r10 plots>` | 0 | 5.439 |
| r10_compose_master | `python compose_figures.py C:/swv_r10_20261122 paper_evidence/web_slicing_figures_stages/r9` | 0 | 6.848 |
| r10_fig6_percentiles | `python render_contacts.py <r4 Case C before/after VTP> <fig4 metadata> <plots> using the package P5–P95 range` | 0 | 5.248 |
| r10_compose_final | `python compose_figures.py C:/swv_r10_20261122 paper_evidence/web_slicing_figures_stages/r9` | 0 | 6.660 |
| r10_verify_outputs | `C:/swv_r4_20261121/venv/Scripts/python.exe - (Pillow image, SHA-256, DPI, vector PDF and retained r9 validation); node --check paper_evidence/web_slicing_figures_stages/r10/capture_viewers.mjs; git diff --exit-code HEAD -- src/ viewer/src/` | 1 | 0.584 |
| r10_fig5_vector | `C:/swv_r4_20261121/venv/Scripts/python.exe paper_evidence/web_slicing_figures_stages/r10/plot_principal.py examples/flac3d_cavern_iv2/input/IV-2.vtu C:/swv_r10_20261122/plots` | 0 | 15.382 |
| r10_compose_vector | `C:/swv_r4_20261121/venv/Scripts/python.exe paper_evidence/web_slicing_figures_stages/r10/compose_figures.py C:/swv_r10_20261122 paper_evidence/web_slicing_figures_stages/r9` | 0 | 6.275 |
| r10_verify_final | `C:/swv_r4_20261121/venv/Scripts/python.exe C:/swv_r10_20261122/verify_outputs.py; node --check paper_evidence/web_slicing_figures_stages/r10/capture_viewers.mjs; git diff --exit-code HEAD -- src/ viewer/src/` | 0 | 0.666 |
