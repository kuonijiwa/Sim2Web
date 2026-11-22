# Sim2Web r4 Windows 验证

## 0. 取件、校验与安装

工作目录 `G:\成果\papers\02\`，工作站为 Windows 11 中文版 10.0.26300、Intel Core i7‑10750H、15.8 GiB RAM、Intel UHD Graphics / NVIDIA Quadro P620。Python 3.12.14、NumPy 1.26.4、PyVista 0.46.3、VTK 9.5.0、Node 24.19.0、Chrome 160.0.8157.0、ParaView 5.13.3。时间均为 JST。测量期间有并行任务，尤其是长时间的工作台和基准操作，时长是实际记录的单次 wall clock，分析比较需考虑当时负载。

从指定 Drive 文件夹获取 r4 bundle、任务说明和中文稿，先校验 bundle 再 fetch。实算 SHA-256 为 `8bd3c4a70347db69d287ae5e61c7ff2e3e8c7609b7f93a33eb9b65091922981b`。bundle 先决提交 `fb39f8b` 已存在，仓库检出 `refactor/sim2web` 的 `722176f4049ce651dc283ec3665aeb73e9eca884`。废弃文件未使用，r3 的 `d3e54a7` 留在原分支。主检出 `src/` 无差异，D/F 的模型始终引用仓库外文件。

`sim2web` 和别名 `simwebview` 均正常。实际用旧 `simwebview.yaml` 和旧别名构建了外表面（禁用剖面与打包，退出 0），也用 Chromium 打开原 r3 网页包并等待实际首帧（退出 0）。r4 截图脚本初次探测超时，原因是旧包前端公开的是 `__SIMWEBVIEW__`。在外置脚本里改探测钩子后复测通过。OpenGeoSys 始终留在 r3 独立环境，其 6.5.9.dirty 运行检查和 OGS VTU SHA 已记录。

## 1. 测试

| 检查 | 结果 | 证据 |
|---|---|---|
| 原仓库工作目录 Python 测试 | 46 通过、6 失败、6 跳过。Windows VTK 的 Exodus 读取器在中文路径下打不开文件。 | `logs/014_pytest.log` |
| 同提交、英语目录重跑 | 52 通过、6 跳过。复制了原测试 fixture，核对 SHA 相同，并补齐测试读取的三份原始配置。 | `logs/040_copy_tests_ascii.log`–`logs/041_pytest_ascii.log`、`logs/056_pytest_ascii_complete.log` |
| Viewer / Workbench 前端测试 | 8 通过 / 7 通过 | `logs/019_viewer_tests.log`、`logs/020_workbench_tests.log` |
| 真实数据回归 A/B/C | 6 通过，52 被 marker 排除 | `logs/016_realdata.log` |

原 Windows 失败保留为 r4 测试结果。独立候选分支 `codex/r4-exodus-windows` 只修改 Exodus 读取层。UTF-8 路径的文件经 ASCII 临时目录读取。测试在原中文路径下用该候选代码复跑，共 8 通过（`logs/083_proposed_exodus_tests.log`）。当前工作站的 TEMP 是 ASCII。候选代码在 TEMP 仍含非 ASCII 时明确返回错误。

## 2. D 开挖面复测

说明里的 `--set input.stages[0].file=...` 实跑退出 1，因为 CLI 点分 override 不支持数组下标。使用外部 YAML 保留示例设置并写入绝对原始 VTU 路径，构建和验证退出 0。原始模型是 332,510 个节点、548,417 个单元，识别出 5 个网格连通区，外表面 `auto → drop`。

- 开挖面 17,004 面，面积 6,418.370307 m²（构建日志数据），用发布 VTP 审核为 6,418.370277 m²。开挖候选层 `internal_faces_removed=85,215`，外表面去除 89,901 个接触面。
- 严格按面心 `z < −57.5 m` 共 489 个，全部是实际高程 −57.500301361 m 的平坦坑底，面积 384.293 m²。面心与全部顶点口径均为 489。至少有一个顶点低于该阈值的共有 625 面，另 136 面为与坑底相接的壁面。低于 −57.5013 m 的顶点和面心均为 0。
- 外表面 r3 的 110,194 面、11,270,082 B 降为 r4 的 20,293 面、2,248,198 B。r3 在坑底以下的 11,710 面环带已从发布面消失。D 的 112 个剖面通过独立验证（806 项精确数组、0 个不匹配、448 项插值数组、最大归一化 RMSE 为 3.346×10⁻⁷）。
- 证据见 `cases/D/excavation_audit.json`、`cases/D/build_report.json`、`cases/D/index.json` 与 `cases/D/validation_summary.json`。查看器全图与仰视图均为 1600×900，见 `cases/D/viewer_1600x900.png` 和 `cases/D/excavation_from_below_1600x900.png`。


### 单次构建结果

| 案例 | 主表面面数 | 主表面 B | 剖面 | 全部 VTP B | 完整站点 B | 构建 s | 验证 s | 验证失败 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 49,677 | 5,099,246 | 132 | 82,913,238 | 84,502,592 | 99.566 | 122.070 | 0 |
| B | 38,789 | 3,841,426 | 154 | 86,256,706 | 87,878,899 | 134.089 | 90.970 | 0 |
| C | 21,293 | 2,620,417 | 151 | 132,241,437 | 133,851,840 | 101.590 | 344.270 | 0 |
| D | 20,293 | 2,248,198 | 112 | 61,202,916 | 62,766,024 | 144.505 | 81.520 | 0 |
| E | 7,920 | 338,410 | 30 | 1,424,704 | 2,856,348 | 21.547 | 14.020 | 0 |
| F | 19,394 | 2,352,584 | 150 | 110,336,486 | 111,938,065 | 132.865 | 283.883 | 0 |

## 3. Abaqus

Abaqus R2020 的本地厂商例子使用 r3 已归档 ODB。曲轴导出 Step‑1 末帧，138,490 节点、88,226 个三维单元，`S` 只有节点位置，r4 实际以 PointData 写出。空尾步板例回退到 Step‑1 末帧，6,788 节点、925 个三维单元，应力位置 element-nodal average。两者 inspect、build、validate 均退出 0，关键输出见 `logs/028_...`、`logs/029_...`、`logs/048_...`–`logs/050_...`，详细 JSON/CSV 在 `cases/G/`。本次未找到可用的无三维实体 ODB，实物例子的退出码 2 未测。仓库模拟测试结果计入 §1。

## 4. MOOSE

原始 Exodus 文件与 r3 使用的原始公开样例相同。两次转换退出 0。默认最后一步 t=2，`--time first` 为 t=0。自动组合位移 `X,Y,Z`，应力 `XX,YY,ZZ,XY,YZ,ZX`，其中 ZX 与 XZ 为同一剪切分量。r4 两帧坐标最大点距为 0。r3 手工 VTU 和 r4 坐标最大差为 3.22×10⁻⁸ m，按节点坐标与单元连通性对齐后应力、位移最大绝对差均为 0。已实际构建并验证 12 个剖面，82 项精确数组、48 项插值数组，全部通过。见 `cases/H/r3_r4_difference.json`、`cases/H/validation_summary.json`、`logs/042_...`–`logs/047_...`。

## 5. Windows 工作台

D、F、OGS 已完成实际浏览器交互，检查了盘符列表、中文路径、读取、Preview、Build、Validate、Publish 与 View。D/F/E 的 ZIP 经 CRC 校验、解压到独立目录并在 Chrome 中打开。ZIP 原样包含工作台的 `index.json`。三份工作台 `case.yaml` 也都能用 CLI 构建。重建索引 SHA 与原包不一致，仅 `config_sha256` 不同，逐项对比包括产物哈希在内的其他键全部相同。原因是 GUI 构建强制设置 viewer 并哈希重新序列化的 YAML，CLI 哈希保存文件文本。所有步骤截图、盘符响应、命令、三份 SHA 和索引差异见 `workbench/{D,F,E}/`。待选分支 `codex/r4-workbench-config-hash` 让构建以持久化配置为准，已通过 6 项隔离工作台测试，拿真实 OGS 配置重建工作台和 CLI 两次后索引 SHA 相同。主 r4 三例仍报告哈希不一致。

### 5b. 大模型计时与响应

| 算例 | 读取 s | 预览 s | 构建 s | 验证 s | 最慢 API 请求 |
|---|---:|---:|---:|---:|---:|
| D | 11.0 | 31.9 | 114.5 | 26.9 | 1.119 s |
| F | 5.2 | 18.0 | 115.4 | 61.8 | 0.921 s |

本表来自仓库 `benchmark/workbench_timing.py`。验证每 5 个剖面抽 1 个。两个算例的界面最慢请求均出现在 Build，超过任务文件中的 Linux 参考。另用浏览器在实际构建期间切换 Fields、Geometry、Sections 和 Build，D/F 各 4 次均在构建尚未结束时成功，状态保持显示 build running 后转为 done，日志行数也增长（D 从 0 到 9，F 从 0 到 7）。日志响应和截图见 `workbench/D/responsiveness/`、`workbench/F/responsiveness_build/`。F 首次脚本误匹配了启动 inspect 的请求，已用 build 类型过滤复测。只采用复测结果。

## 6. ParaView / Glance 比较

执行 ParaView 5.13.3 便携版的实际 `pvpython`，所用 A/C/D VTU 暂存路径为 ASCII（两边 SHA 相等）。D 因源文件中没有空单元直接保留。A/C 用配置中的绝对应力阈值。剖面位置逐一来自本次 Sim2Web 构建的 index.json。结果、时长、表 3 填数和 M1–M11 对照见 `comparison_results.json`、`comparison_results.md` 和 `MANUSCRIPT_NUMBERS.md`。每案的 pvpython 完整 argv、版本、退出码和中间文件大小保存在 `cases/{A,C,D}/`。

原基准脚本在 5.13.3 的 `SaveData("surface.vtu")` 返回错误。下列改动收在 `codex/r4-paraview-baseline`，全部在 **ParaView 5.13.3** 上实际探测或运行。属性名以安装版代理所列为准。

| 原写法 | 现写法 | 观察 |
|---|---|---|
| `surface.vtu`、`slice_*.vtu` | `surface.vtp`、`slice_*.vtp` | `ExtractSurface` 和 `Slice` 都是 PolyData，VTP 是对应的 writer。 |
| `ExportView("scene.vtkjs")`、`ExportView("glance.html")` 分开调用 | `ExportView("scene.vtkjs", ParaViewGlanceHTML=<模板>)` | exporter 探测只有 `.vtkjs` 返回 WebExporter。属性实际名 `ParaViewGlanceHTML`。输出 `scene.vtkjs` 及 `scene.html`。 |
| 主应力数组依赖过滤器初始选择 | `retained.UpdatePipeline()` 后 `principal.CellTensors = ["Stress"]` | A 的 Threshold 输出中初始 `CellTensors=[]`，C 的首轮归档也没有三个主应力数组。探测 `CellArrays` 不存在。D 无 Threshold 的默认选择已含三个主应力，显式选取不改变定义。 |
| 无位移模长过滤、视图默认颜色 | `Calculator.AttributeType="Point Data"`、`ResultArrayName="Displacement_Magnitude"`、`Function=mag("Displacement")`、`ColorBy(...)`、`ResetCamera()` | 生成协议所需的模长字段并使输出初始着色有定义。 |
| 所有算例强制通过阈值过滤器 | D 增加 `--keep-all` | D 原模型已删除挖空的单元。A/C 的空区阈值过滤保留。 |
| 不记录面积/总时长所需明细 | JSON 增加 `surface_faces` 和 `elapsed_wall_seconds` | 不改变过滤器和主应力默认顺序。 |

ParaView 自带 Glance 模板在这台 Chrome 的试跑出现 `bindRepresentationToManipulator`，数据集列表能加载，截图中的三维场景为空。改用 Kitware 发布的 Glance 独立模板，把完全相同的 vtkjs 数据重新内嵌。单剖面 D 的替代模板实测能够画出几何。完整包补测采用 Kitware 官方支持的 `name/url` 参数，由本机回环服务器分别提供 Glance 查看器与同一完整 vtkjs 数据。这个路径避开超大内嵌 HTML 的执行阻塞。包体积同时列出 vtkjs 和内嵌 HTML，首帧采用分开加载模式。早期 probe 计到了 3,186 索引的坐标轴控件，排除这些试次。Glance 最终首帧以主画布上至少 10,000 索引的模型 WebGL triangles draw 为准，再等待两个动画帧。Sim2Web 使用其仓库 benchmark 的 firstRender。浏览器缓存关闭，运行明确区分不同模板和首轮应力未启用的 ParaView 包。[Kitware 导出说明](https://www.kitware.com/exporting-paraview-scenes-to-paraview-glance/) · [Kitware 独立模板](https://kitware.github.io/glance/app/ParaViewGlance.html) · [按 URL 加载说明](https://kitware.github.io/glance/doc/loading_files.html)

D/F 用仓库同一 VTK 过滤器实测。D 的最小、中间、最大主应力最大误差分别为 1.405813、3.152970、1.762586 MPa，占各自范围 13.7056%、75.8984%、22.1703%，仅通用结果受拉 3,808 个。F 的最小、中间、最大主应力差分别为 21.711403、53.164728、31.453324 MPa，占 4.7954%、16.5251%、16.4312%，仅通用结果受拉 15,613 个。逐项见 `MANUSCRIPT_NUMBERS.md`、`cases/F/paraview_principal.json`。计算保留 `XX,YY,ZZ,XY,YZ,XZ` 默认顺序与按文件标签 `XX,YY,ZZ,XY,XZ,YZ` 的对照。A/C 的应力对照也见比较 JSON。

### 开挖附加处理与主应力重排

A 的默认 ParaView 表面是保留岩体的外露面。额外 4 个操作隔离空区相邻的实体面，产出 49,677 面、31,376.719 m²。D 额外 3 个操作（先去六个域边界、再剔除双侧都是实体的接触面、最后单独输出）产出 17,004 面、6,418.370 m²。两例输出与 Sim2Web 的面数相同，1 mm 内面心双向无漏配，未核对面向和物理场值。C 仅要求边坡外表面，开挖层没有额外操作。COMPARISON_PROTOCOL.md 中现成的 C 外表面对照引用的是 r3 的 F 数字，本次 C 使用实际 917,062/21,293 面。见各案例 `paraview_excavation_extras.json` 和 M7/M8。

用一个额外的重排操作把文件的 XZ、YZ 分量放入 VTK 期望位置，再用同一滤镜，A/C/D 的最大误差均回落到双精度舍入量级。该修正对照与默认结果分列，见 `paraview_principal_reordered.json`。实际 Glance 归档含 A 133、C 152、D 113 个对象，每个对象都含位移模长和三项主应力。工作站上的 Sim2Web 字段切换已用额外浏览器脚本实测。Glance 个别剖面按可见性按钮切换，没有同等的连续剖面滑块。三案的 Glance 切换测试在独立 42 秒边界内没有取得可核对的切换渲染，M4 JSON 保留实际失败原因和空值。首帧三个试次均成功。

### GUI Trace 口径

首轮 A 在桌面通过 Tools → Start Trace 后加载、Apply，再通过桌面 Python 面板批量操作。保存的原生 Trace 记录了 132 个 Slice，缺少通过 Python 直接设置的部分属性和 ExportView 行。完整性复测在真实桌面 ParaView 用相同代理、过滤器和位置，启用原生属性和导出记录钩子。单独列出原生 Trace 总行数和去掉空白、注释后的行数。逐一解析原生 Trace 的剖面原点和法向并对照 index.json，检查每个剖面位置，纯手工逐项点击整套导出流程和耗时未实测。初始试验和正式计时各有记录。

### 可复核的比较摘要

| 项目 | A | C | D |
|---|---|---|---|
| M1 Trace 有效行 / Sim2Web 改行、点击 | 5411 / 36 行、14 次 | 6192 / 17 行、14 次 | 4579 / 35 行、14 次 |
| M2 pvpython / Sim2Web 构建 / 验证 (s) | 194.505 / 99.566 / 122.070 | 364.272 / 101.590 / 344.270 | 165.219 / 144.505 / 81.520 |
| M3 Glance 官方模板 HTML / Sim2Web 站点 | 256,286,362 B（256.286 MB） / 84,502,592 B（84.503 MB） | 440,648,222 B（440.648 MB） / 133,851,840 B（133.852 MB） | 200,162,242 B（200.162 MB） / 62,766,024 B（62.766 MB） |
| M4 首帧中位数 (ms) Glance / Sim2Web | 31,214.0 / 2,868.8 | 49,043.2 / 2,661.6 | 23,636.0 / 3,686.2 |
| M5 通用结果误判受拉 | 14711 | 19608 | 3808 |
| M6 Sim2Web 应力量纲 | ok | ok | ok |
| M7 增加分离开挖面的处理操作 | 4 | 0 | 3 |
| M8 ParaView / Sim2Web 外表面面数 | 51973 / 主层为开挖面 | 917062 / 21293 | 105508 / 20293 |
| M9 Sim2Web 源单元、节点 ID | 有 / 有 | 有 / 有 | 有 / 有 |
| M10 ParaView / Sim2Web 剖面数 | 132 / 132 | 151 / 151 | 112 / 112 |
| M11 Sim2Web validate 退出码 | 0 | 0 | 0 |

同机脚本打包与桌面 GUI Trace 是两份证据。Glance 首帧采用分开载入官方查看器和 vtkjs，独立 HTML 使用同一数据并单列体积。逐项目径、全部浏览器试次、验证和原始文件路径见 `comparison_results.json` 与 `MANUSCRIPT_NUMBERS.md`。

## 7. 交付与命令记录

交付目录包含 `MANUSCRIPT_NUMBERS.md`、`REFERENCES.md`、M1–M11 表、JSON/CSV、Trace、截图与独立 Git bundle。原始模型、求解器、完整站点、Glance 大文件留在本机。所有外部命令退出码和耗时可从下表定位，每条日志保留实际输出。各子步骤的精确 argv 也记录于工作台和 ParaView 的 JSON。特定截图和包的大小在文中使用十进制 MB。稿件的应用反馈、正式发布 DOI、F 数据权属仍需作者提供。

### GUI 与后台命令索引

- ParaView 桌面在 Tools → Start Trace 开始录制，A 从 File → Open 和 Apply 读取，然后通过 View → Python Shell → Run Script 运行 `repro_scripts/pv_gui_trace.py`。批量启动本身不产生 CLI 退出码，桌面脚本有逐案成功或错误状态。
- Glance 首轮、自带模板和启用主应力前的探测各自保留，退出码或停止证据见日志 072、073、081、109。
- `COMMANDS.csv` 含执行目录、起始时间、完整命令和日志路径。Windows 工作台各子命令见 `workbench/*/commands.json`。各外部 ParaView argv 见 `cases/*/paraview{_corrected/, _command.json}` 对应目录。

| 编号 | 实际命令或记录的操作 | 退出码 | wall s | 关键输出 |
|---|---|---:|---:|---|
| 001_bundle_download | `curl.exe --fail --silent --show-error --location <Drive bundle 1l9cAQhVQHLrVD9Rte28cxlUQRRNQvGXN> --output C:/swv_r4_20261121/sim2web_r4.bundle` | 0 | 0.718 | [001_bundle_download.log](logs/001_bundle_download.log) |
| 002_bundle_sha256 | `Get-FileHash -Algorithm SHA256 C:/swv_r4_20261121/sim2web_r4.bundle` | 0 | 0.075 | [002_bundle_sha256.log](logs/002_bundle_sha256.log) |
| 003_download_task | `curl.exe --fail --silent --show-error --location <Drive task 1W2Fzm-e6EEPAr60UwLrp6KWhEu8bN4Dy> --output C:/swv_r4_20261121/CODEX_TASK_r4_sim2web.md` | 0 | 0.517 | [003_download_task.log](logs/003_download_task.log) |
| 004_download_manuscript | `curl.exe --fail --silent --show-error --location <Drive manuscript 1KQXlPbcWv6d_FIwg5lCIho6QVfcgRQkK> --output C:/swv_r4_20261121/manuscript_zh.docx` | 0 | 1.015 | [004_download_manuscript.log](logs/004_download_manuscript.log) |
| 005_bundle_verify | `git bundle verify C:/swv_r4_20261121/sim2web_r4.bundle; git bundle list-heads` | 0 | 0.605 | [005_bundle_verify.log](logs/005_bundle_verify.log) |
| 006_preserve_r3_user_data | `Move prior untracked case5 and ignored case4 VTU working copies to G:/成果/papers/02/SimWebView_user_data_before_r4` | 0 | 0.127 | [006_preserve_r3_user_data.log](logs/006_preserve_r3_user_data.log) |
| 007_git_fetch | `git fetch C:/swv_r4_20261121/sim2web_r4.bundle refactor/sim2web:refactor/sim2web` | 0 | 0.265 | [007_git_fetch.log](logs/007_git_fetch.log) |
| 008_git_checkout | `git checkout refactor/sim2web` | 0 | 1.571 | [008_git_checkout.log](logs/008_git_checkout.log) |
| 009_git_verify_head | `git log --oneline -5; git rev-parse HEAD; git rev-parse codex/r3-abaqus-exporter-guards` | 0 | 0.662 | [009_git_verify_head.log](logs/009_git_verify_head.log) |
| 010_preserve_old_build_output | `Move-Item untracked src/simwebview leftovers to C:/swv_r4_20261121/previous_src_leftovers on the prior checkout` | 0 | 0.179 | [010_preserve_old_build_output.log](logs/010_preserve_old_build_output.log) |
| 011_venv | `bundled Python 3.12 -m venv C:/swv_r4_20261121/venv` | 0 | 10.498 | [011_venv.log](logs/011_venv.log) |
| 012_requirements | `python -m pip install -r requirements.txt` | 0 | 52.596 | [012_requirements.log](logs/012_requirements.log) |
| 013_editable | `python -m pip install -e ".[test,convert]"` | 0 | 20.524 | [013_editable.log](logs/013_editable.log) |
| 014_pytest | `python -m pytest -q` | 1 | 26.022 | [014_pytest.log](logs/014_pytest.log) |
| 015_versions | `python -c <read pinned dependencies and CLI versions>` | 0 | 0.757 | [015_versions.log](logs/015_versions.log) |
| 016_realdata | `$env:SIM2WEB_REALDATA=1; python -m pytest -q -m realdata -vv` | 0 | 546.763 | [016_realdata.log](logs/016_realdata.log) |
| 017_npm_ci | `npm ci` | 0 | 13.399 | [017_npm_ci.log](logs/017_npm_ci.log) |
| 018_npm_build | `npm run build` | 0 | 9.230 | [018_npm_build.log](logs/018_npm_build.log) |
| 019_viewer_tests | `npm run test:viewer` | 0 | 0.800 | [019_viewer_tests.log](logs/019_viewer_tests.log) |
| 020_workbench_tests | `npm run test:workbench` | 0 | 0.879 | [020_workbench_tests.log](logs/020_workbench_tests.log) |
| 021_paraview_download | `curl.exe --fail --location <official ParaView 5.13.3 Windows archive> --output ParaView-5.13.3-Windows-Python3.10-msvc2017-AMD64.zip` | 0 | 187.238 | [021_paraview_download.log](logs/021_paraview_download.log) |
| 022_paraview_extract | `tar.exe -xf ParaView-5.13.3-Windows-Python3.10-msvc2017-AMD64.zip -C C:/swv_r4_20261121/paraview` | 0 | 14.398 | [022_paraview_extract.log](logs/022_paraview_extract.log) |
| 023_extract_manuscript_targets | `bundled Python extract_docx_targets.py manuscript_zh.docx manuscript_highlights.json` | 0 | 0.562 | [023_extract_manuscript_targets.log](logs/023_extract_manuscript_targets.log) |
| 024_case5_extension | `Copy-Item case5/kala_final wb_case5/input/kala_final.vtu; verify both SHA-256` | 0 | 1.263 | [024_case5_extension.log](logs/024_case5_extension.log) |
| 025_prepare_configs | `python prepare_cases.py <repository> <scratch> <run>` | 0 | 0.297 | [025_prepare_configs.log](logs/025_prepare_configs.log) |
| 026_documented_index_override | `sim2web build examples/flac3d_pit_case4/sim2web.yaml --set input.stages[0].file=G:/成果/papers/02/case4/EXC12_dis.vtu` | 2 | 1.984 | [026_documented_index_override.log](logs/026_documented_index_override.log) |
| 027_principal_D | `python benchmark/paraview_principal_check.py 'G:/成果/papers/02/case4/EXC12_dis.vtu' --array Stress --out 'G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/paraview_principal.json'` | 0 | 7.149 | [027_principal_D.log](logs/027_principal_D.log) |
| 027_principal_F | `python benchmark/paraview_principal_check.py 'G:/成果/papers/02/wb_case5/input/kala_final.vtu' --array Stress --out 'G:/成果/papers/02/codex_run_2026-11-21_r4/cases/F/paraview_principal.json'` | 0 | 3.984 | [027_principal_F.log](logs/027_principal_F.log) |
| 028_abaqus_r2020_crankshaft | `ABQLauncher.exe python abaqus_odb_to_vtu.py <vendor crankshaft_TCD_nodal_averaged_R2020.odb> crankshaft.vtu` | 0 | 11.719 | [028_abaqus_r2020_crankshaft.log](logs/028_abaqus_r2020_crankshaft.log) |
| 029_abaqus_r2020_plate | `ABQLauncher.exe python abaqus_odb_to_vtu.py <vendor abaqus_plate_single_R2020.odb> plate.vtu` | 0 | 1.572 | [029_abaqus_r2020_plate.log](logs/029_abaqus_r2020_plate.log) |
| 034_build_A | `sim2web build 'C:/swv_r4_20261121/model_runs/A/case.yaml'` | 0 | 99.566 | [034_build_A.log](logs/034_build_A.log) |
| 034_build_B | `sim2web build 'C:/swv_r4_20261121/model_runs/B/case.yaml'` | 0 | 134.089 | [034_build_B.log](logs/034_build_B.log) |
| 034_build_C | `sim2web build 'C:/swv_r4_20261121/model_runs/C/case.yaml'` | 0 | 101.590 | [034_build_C.log](logs/034_build_C.log) |
| 034_build_D | `sim2web build 'C:/swv_r4_20261121/model_runs/D/case.yaml'` | 0 | 144.505 | [034_build_D.log](logs/034_build_D.log) |
| 034_build_E | `sim2web build 'C:/swv_r4_20261121/model_runs/E/case.yaml'` | 0 | 21.547 | [034_build_E.log](logs/034_build_E.log) |
| 034_build_F | `sim2web build 'C:/swv_r4_20261121/model_runs/F/case.yaml'` | 0 | 132.865 | [034_build_F.log](logs/034_build_F.log) |
| 035_validate_A | `sim2web validate 'C:/swv_r4_20261121/model_runs/A/case.yaml'` | 0 | 122.070 | [035_validate_A.log](logs/035_validate_A.log) |
| 035_validate_B | `sim2web validate 'C:/swv_r4_20261121/model_runs/B/case.yaml'` | 0 | 90.970 | [035_validate_B.log](logs/035_validate_B.log) |
| 035_validate_C | `sim2web validate 'C:/swv_r4_20261121/model_runs/C/case.yaml'` | 0 | 344.270 | [035_validate_C.log](logs/035_validate_C.log) |
| 035_validate_D | `sim2web validate 'C:/swv_r4_20261121/model_runs/D/case.yaml'` | 0 | 81.520 | [035_validate_D.log](logs/035_validate_D.log) |
| 035_validate_E | `sim2web validate 'C:/swv_r4_20261121/model_runs/E/case.yaml'` | 0 | 14.020 | [035_validate_E.log](logs/035_validate_E.log) |
| 035_validate_F | `sim2web validate 'C:/swv_r4_20261121/model_runs/F/case.yaml'` | 0 | 283.883 | [035_validate_F.log](logs/035_validate_F.log) |
| 036_collect_A | `Copy build, index, validation JSON/CSV to cases/A; measure site bytes without validation` | 0 | 0.130 | [036_collect_A.log](logs/036_collect_A.log) |
| 036_collect_B | `Copy build, index, validation JSON/CSV to cases/B; measure site bytes without validation` | 0 | 0.084 | [036_collect_B.log](logs/036_collect_B.log) |
| 036_collect_C | `Copy build, index, validation JSON/CSV to cases/C; measure site bytes without validation` | 0 | 0.079 | [036_collect_C.log](logs/036_collect_C.log) |
| 036_collect_D | `Copy build, index, validation JSON/CSV to cases/D; measure site bytes without validation` | 0 | 0.083 | [036_collect_D.log](logs/036_collect_D.log) |
| 036_collect_E | `Copy build, index, validation JSON/CSV to cases/E; measure site bytes without validation` | 0 | 0.188 | [036_collect_E.log](logs/036_collect_E.log) |
| 036_collect_F | `Copy build, index, validation JSON/CSV to cases/F; measure site bytes without validation` | 0 | 0.258 | [036_collect_F.log](logs/036_collect_F.log) |
| 037_ogs_separate | `C:/swv_r3_20261121/ogs_venv/Scripts/ogs.exe --version; Get-FileHash of the r3 OGS VTU used for the walkthrough` | 0 | 2.745 | [037_ogs_separate.log](logs/037_ogs_separate.log) |
| 038_pv_portable_download | `curl.exe --fail --location --max-time 480 'https://www.paraview.org/files/v5.13/ParaView-5.13.3-Windows-Python3.10-msvc2017-AMD64.zip' --output C:/swv_r4_20261121/pv_5_13_3_portable.zip` | 0 | 147.491 | [038_pv_portable_download.log](logs/038_pv_portable_download.log) |
| 039_pv_portable_extract | `tar.exe -xf C:/swv_r4_20261121/pv_5_13_3_portable.zip -C C:/swv_r4_20261121/pv_portable` | 0 | 19.025 | [039_pv_portable_extract.log](logs/039_pv_portable_extract.log) |
| 040_copy_tests_ascii | `Copy-Item the checked-out tests, tools and pyproject.toml to C:/swv_r4_20261121/ascii_test_root` | 0 | 0.204 | [040_copy_tests_ascii.log](logs/040_copy_tests_ascii.log) |
| 041_pytest_ascii | `C:/swv_r4_20261121/venv/Scripts/python.exe -m pytest -q (same r4 executable and ASCII fixture paths)` | 1 | 20.385 | [041_pytest_ascii.log](logs/041_pytest_ascii.log) |
| 042_moose_source | `Copy verified official elastic_patch_out.e from r3; git hash-object elastic_patch_out.e` | 0 | 0.530 | [042_moose_source.log](logs/042_moose_source.log) |
| 043_moose_last | `sim2web convert elastic_patch_out.e moose.vtu` | 0 | 1.031 | [043_moose_last.log](logs/043_moose_last.log) |
| 044_moose_first | `sim2web convert elastic_patch_out.e moose_t0.vtu --time first` | 0 | 1.046 | [044_moose_first.log](logs/044_moose_first.log) |
| 045_moose_inspect | `sim2web inspect moose.vtu --draft-config draft.yaml > cases/H/inspect.json` | 0 | 1.147 | [045_moose_inspect.log](logs/045_moose_inspect.log) |
| 046_moose_build | `sim2web build case.yaml (MOOSE)` | 0 | 2.266 | [046_moose_build.log](logs/046_moose_build.log) |
| 047_moose_validate | `sim2web validate case.yaml (MOOSE)` | 0 | 1.530 | [047_moose_validate.log](logs/047_moose_validate.log) |
| 048_inspect_crankshaft | `sim2web inspect crankshaft.vtu --draft-config crankshaft.draft.yaml` | 0 | 1.901 | [048_inspect_crankshaft.log](logs/048_inspect_crankshaft.log) |
| 048_inspect_plate | `sim2web inspect plate.vtu --draft-config plate.draft.yaml` | 0 | 0.888 | [048_inspect_plate.log](logs/048_inspect_plate.log) |
| 049_build_crankshaft | `sim2web build crankshaft.yaml` | 0 | 12.310 | [049_build_crankshaft.log](logs/049_build_crankshaft.log) |
| 049_build_plate | `sim2web build plate.yaml` | 0 | 3.335 | [049_build_plate.log](logs/049_build_plate.log) |
| 050_validate_crankshaft | `sim2web validate crankshaft.yaml` | 0 | 3.981 | [050_validate_crankshaft.log](logs/050_validate_crankshaft.log) |
| 050_validate_plate | `sim2web validate plate.yaml` | 0 | 1.982 | [050_validate_plate.log](logs/050_validate_plate.log) |
| 051_pv_version | `pvpython.exe --version` | 0 | 3.500 | [051_pv_version.log](logs/051_pv_version.log) |
| 052_pv_baseline_original | `pvpython benchmark/paraview_baseline.py <Case D VTU> --out <smoke directory> --sections x=0` | 1 | 10.747 | [052_pv_baseline_original.log](logs/052_pv_baseline_original.log) |
| 053_pv_launch_gui | `paraview.exe --disable-registry` | 0 | 0.181 | [053_pv_launch_gui.log](logs/053_pv_launch_gui.log) |
| 055_workbench_A | `python drive_workbench.py A <repository> <scratch> <run>` | 1 | 38.237 | [055_workbench_A.log](logs/055_workbench_A.log) |
| 055_workbench_C | `python drive_workbench.py C <repository> <scratch> <run>` | 0 | 489.685 | [055_workbench_C.log](logs/055_workbench_C.log) |
| 055_workbench_D | `python drive_workbench.py D <repository> <scratch> <run>` | 0 | 167.383 | [055_workbench_D.log](logs/055_workbench_D.log) |
| 055_workbench_E | `python drive_workbench.py E <repository> <scratch> <run>` | 0 | 60.234 | [055_workbench_E.log](logs/055_workbench_E.log) |
| 055_workbench_F | `python drive_workbench.py F <repository> <scratch> <run>` | 0 | 342.500 | [055_workbench_F.log](logs/055_workbench_F.log) |
| 056_pytest_ascii_complete | `python -m pytest -q from ASCII fixture root with all three checked-in case configs` | 0 | 22.828 | [056_pytest_ascii_complete.log](logs/056_pytest_ascii_complete.log) |
| 057_pv_exporter_probe | `pvpython C:/swv_r4_20261121/pv_probe.py` | 0 | 15.753 | [057_pv_exporter_probe.log](logs/057_pv_exporter_probe.log) |
| 058_workbench_timing_D | `C:/swv_r4_20261121/venv/Scripts/python.exe G:/成果/papers/02/SimWebView/benchmark/workbench_timing.py C:/swv_r4_20261121/wb_timing/D --out G:/成果/papers/02/codex_run_2026-11-21_r4/workbench/D/workbench_timing.json` | 0 | 186.795 | [058_workbench_timing_D.log](logs/058_workbench_timing_D.log) |
| 058_workbench_timing_F | `C:/swv_r4_20261121/venv/Scripts/python.exe G:/成果/papers/02/SimWebView/benchmark/workbench_timing.py C:/swv_r4_20261121/wb_timing/F --out G:/成果/papers/02/codex_run_2026-11-21_r4/workbench/F/workbench_timing.json` | 0 | 202.201 | [058_workbench_timing_F.log](logs/058_workbench_timing_F.log) |
| 059_patch_baseline | `python C:/swv_r4_20261121/patch_baseline.py benchmark/paraview_baseline.py C:/swv_r4_20261121/paraview_baseline.py` | 0 | 0.266 | [059_patch_baseline.log](logs/059_patch_baseline.log) |
| 060_pv_ascii_D | `Copy-Item case4/EXC12_dis.vtu C:/swv_r4_20261121/pv_sources/D.vtu; compare SHA-256` | 0 | 2.191 | [060_pv_ascii_D.log](logs/060_pv_ascii_D.log) |
| 061_pv_baseline_smoke | `C:\swv_r4_20261121\pv_portable\ParaView-5.13.3-Windows-Python3.10-msvc2017-AMD64\bin\pvpython.exe C:/swv_r4_20261121/paraview_baseline.py C:/swv_r4_20261121/pv_sources/D.vtu --out C:/swv_r4_20261121/pv_smoke --keep-all --sections z=-57.5003 --glance-template C:\swv_r4_20261121\paraview\ParaView-5.13.3-Windows-Python3.10-msvc2017-AMD64\share\paraview-5.13\web\glance\ParaViewGlance.html` | 0 | 22.885 | [061_pv_baseline_smoke.log](logs/061_pv_baseline_smoke.log) |
| 062_pv_ascii_A | `Copy-Item 'G:/成果/papers/02/SimWebView/examples/flac3d_cavern_iv2/input/IV-2.vtu' 'C:/swv_r4_20261121/pv_sources/A.vtu'; compare SHA-256` | 0 | 4.980 | [062_pv_ascii_A.log](logs/062_pv_ascii_A.log) |
| 062_pv_ascii_C | `Copy-Item 'G:/成果/papers/02/SimWebView/examples/3dec_slope/input/slopemodel.vtu' 'C:/swv_r4_20261121/pv_sources/C.vtu'; compare SHA-256` | 0 | 2.576 | [062_pv_ascii_C.log](logs/062_pv_ascii_C.log) |
| 063_pv_full | `python C:/swv_r4_20261121/run_paraview.py 'C:/swv_r4_20261121' 'G:/成果/papers/02/codex_run_2026-11-21_r4' 'G:/成果/papers/02/SimWebView' A C D` | 0 | 989.297 | [063_pv_full.log](logs/063_pv_full.log) |
| 064_moose_r3_comparison | `python C:/swv_r4_20261121/moose_compare.py C:/swv_r3_20261121/moose/final_bundle.vtu C:/swv_r4_20261121/moose/moose.vtu C:/swv_r4_20261121/moose/moose_t0.vtu G:/成果/papers/02/codex_run_2026-11-21_r4/cases/H/r3_r4_difference.json` | 0 | 2.316 | [064_moose_r3_comparison.log](logs/064_moose_r3_comparison.log) |
| 065_open_r3_package | `node benchmark/screenshots.mjs --site 'G:/成果/papers/02/SimWebView_user_data_before_r4/3dec_slope_case5/site' --browser 'C:/Program Files/Google/Chrome/Application/chrome.exe' --out 'G:/成果/papers/02/codex_run_2026-11-21_r4/cases/F/r3_legacy_package.png'` | 1 | 303.863 | [065_open_r3_package.log](logs/065_open_r3_package.log) |
| 066_case_D_excavation | `python C:/swv_r4_20261121/case_d_audit.py C:/swv_r4_20261121/model_runs/D/site G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/excavation_audit.json <r3 index>` | 0 | 14.008 | [066_case_D_excavation.log](logs/066_case_D_excavation.log) |
| 067_workbench_index_diff_D | `python index_diff.py <workbench ZIP> <CLI rebuild> G:/成果/papers/02/codex_run_2026-11-21_r4/workbench/D/index_diff.json` | 0 | 0.215 | [067_workbench_index_diff_D.log](logs/067_workbench_index_diff_D.log) |
| 067_workbench_index_diff_E | `python index_diff.py <workbench ZIP> <CLI rebuild> G:/成果/papers/02/codex_run_2026-11-21_r4/workbench/E/index_diff.json` | 0 | 0.176 | [067_workbench_index_diff_E.log](logs/067_workbench_index_diff_E.log) |
| 067_workbench_index_diff_F | `python index_diff.py <workbench ZIP> <CLI rebuild> G:/成果/papers/02/codex_run_2026-11-21_r4/workbench/F/index_diff.json` | 0 | 0.185 | [067_workbench_index_diff_F.log](logs/067_workbench_index_diff_F.log) |
| 068_screenshot_D | `node benchmark/screenshots.mjs --site C:/swv_r4_20261121/model_runs/D/site --browser 'C:/Program Files/Google/Chrome/Application/chrome.exe' --hash 'field=Y_Disp&section=0&layers=exterior:0:1,excavation:1:1&parallel=1&cam=-7,-25,95,-7,0,-22,0,1,0,39' --out G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/viewer_1600x900.png` | 0 | 12.113 | [068_screenshot_D.log](logs/068_screenshot_D.log) |
| 068_screenshot_F | `node benchmark/screenshots.mjs --site C:/swv_r4_20261121/model_runs/F/site --browser 'C:/Program Files/Google/Chrome/Application/chrome.exe' --hash 'field=TotalDisplacement&section=1&layers=exterior:1:0.35' --axis y --index 12 --out G:/成果/papers/02/codex_run_2026-11-21_r4/cases/F/viewer_1600x900.png` | 0 | 7.672 | [068_screenshot_F.log](logs/068_screenshot_F.log) |
| 069_screenshot_D_below | `node benchmark/screenshots.mjs --site C:/swv_r4_20261121/model_runs/D/site --browser 'C:/Program Files/Google/Chrome/Application/chrome.exe' --hash 'field=Y_Disp&section=0&layers=exterior:0:1,excavation:1:1&parallel=1&cam=-7,-30,-115,-7,0,-29,0,0,1,40' --out G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/excavation_from_below_1600x900.png` | 0 | 10.562 | [069_screenshot_D_below.log](logs/069_screenshot_D_below.log) |
| 070_browser_A | `node benchmark/browser_benchmark.mjs --site C:/swv_r4_20261121/model_runs/A/site --runs 3 --sections 10 --frames 120 --browser 'C:/Program Files/Google/Chrome/Application/chrome.exe' --headless false --out G:/成果/papers/02/codex_run_2026-11-21_r4/cases/A/sim2web_browser.json` | 0 | 33.422 | [070_browser_A.log](logs/070_browser_A.log) |
| 070_browser_C | `node benchmark/browser_benchmark.mjs --site C:/swv_r4_20261121/model_runs/C/site --runs 3 --sections 10 --frames 120 --browser 'C:/Program Files/Google/Chrome/Application/chrome.exe' --headless false --out G:/成果/papers/02/codex_run_2026-11-21_r4/cases/C/sim2web_browser.json` | 0 | 38.563 | [070_browser_C.log](logs/070_browser_C.log) |
| 070_browser_D | `node benchmark/browser_benchmark.mjs --site C:/swv_r4_20261121/model_runs/D/site --runs 3 --sections 10 --frames 120 --browser 'C:/Program Files/Google/Chrome/Application/chrome.exe' --headless false --out G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/sim2web_browser.json` | 0 | 44.159 | [070_browser_D.log](logs/070_browser_D.log) |
| 071_draft_diffs | `python C:/swv_r4_20261121/compare_drafts.py C:/swv_r4_20261121 G:/成果/papers/02/codex_run_2026-11-21_r4` | 0 | 27.127 | [071_draft_diffs.log](logs/071_draft_diffs.log) |
| 072_glance_smoke | `node C:/swv_r4_20261121/glance_browser.mjs 'G:/成果/papers/02/SimWebView' C:/swv_r4_20261121/pv_smoke/scene.html C:/swv_r4_20261121/pv_smoke/browser.json C:/swv_r4_20261121/pv_smoke/browser.png 1` | 1 | 186.963 | [072_glance_smoke.log](logs/072_glance_smoke.log) |
| 073_glance_A | `node C:/swv_r4_20261121/glance_browser.mjs 'G:/成果/papers/02/SimWebView' C:/swv_r4_20261121/pv_baselines/A/scene.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/A/glance_browser.json G:/成果/papers/02/codex_run_2026-11-21_r4/cases/A/glance_1600x900.png 3` | 1 | 744.050 | [073_glance_A.log](logs/073_glance_A.log) |
| 074_wb_ui_responsive_D | `node C:/swv_r4_20261121/workbench_responsive.mjs 'G:/成果/papers/02/SimWebView' C:/swv_r4_20261121/venv/Scripts/sim2web.exe C:/swv_r4_20261121/wb_responsiveness/D G:/成果/papers/02/codex_run_2026-11-21_r4/workbench/D/responsiveness 8780` | 0 | 153.435 | [074_wb_ui_responsive_D.log](logs/074_wb_ui_responsive_D.log) |
| 074_wb_ui_responsive_F | `node C:/swv_r4_20261121/workbench_responsive.mjs 'G:/成果/papers/02/SimWebView' C:/swv_r4_20261121/venv/Scripts/sim2web.exe C:/swv_r4_20261121/wb_responsiveness/F G:/成果/papers/02/codex_run_2026-11-21_r4/workbench/F/responsiveness 8781` | 0 | 36.108 | [074_wb_ui_responsive_F.log](logs/074_wb_ui_responsive_F.log) |
| 075_pv_fix_commit | `python commit_separate.py <repo> C:/swv_r4_20261121/paraview_baseline.py codex/r4-paraview-baseline benchmark/paraview_baseline.py` | 0 | 2.305 | [075_pv_fix_commit.log](logs/075_pv_fix_commit.log) |
| 076_reference_crossref | `Invoke-RestMethod Crossref publication records for 102630, 100430, 101690` | 0 | 2.612 | [076_reference_crossref.log](logs/076_reference_crossref.log) |
| 077_glance_official_template | `curl.exe 'https://kitware.github.io/glance/app/ParaViewGlance.html' --output C:/swv_r4_20261121/Glance_Kitware.html` | 0 | 6.321 | [077_glance_official_template.log](logs/077_glance_official_template.log) |
| 078_glance_official_smoke_embed | `C:\swv_r4_20261121\pv_portable\ParaView-5.13.3-Windows-Python3.10-msvc2017-AMD64\bin\pvpython.exe C:/swv_r4_20261121/reembed_glance.py C:/swv_r4_20261121/pv_smoke/scene.vtkjs C:/swv_r4_20261121/Glance_Kitware.html C:/swv_r4_20261121/pv_smoke/scene_kitware.html` | 0 | 1.891 | [078_glance_official_smoke_embed.log](logs/078_glance_official_smoke_embed.log) |
| 079_glance_official_smoke_browser | `node C:/swv_r4_20261121/glance_browser.mjs 'G:/成果/papers/02/SimWebView' C:/swv_r4_20261121/pv_smoke/scene_kitware.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/glance_official_smoke.json G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/glance_official_smoke.png 1` | 0 | 12.834 | [079_glance_official_smoke_browser.log](logs/079_glance_official_smoke_browser.log) |
| 080_glance_official_embed_A | `pvpython C:/swv_r4_20261121/reembed_glance.py C:/swv_r4_20261121/pv_baselines/A/scene.vtkjs C:/swv_r4_20261121/Glance_Kitware.html C:/swv_r4_20261121/pv_baselines/A/scene_kitware.html` | 0 | 2.704 | [080_glance_official_embed_A.log](logs/080_glance_official_embed_A.log) |
| 082_patch_proposals | `python C:/swv_r4_20261121/patch_proposals.py <repo> C:/swv_r4_20261121` | 1 | 0.940 | [082_patch_proposals.log](logs/082_patch_proposals.log) |
| 083_proposed_exodus_tests | `python -m pytest -q tests/test_convert.py with isolated proposed/exodus-windows code and primary Unicode repo` | 0 | 13.225 | [083_proposed_exodus_tests.log](logs/083_proposed_exodus_tests.log) |
| 084_proposed_exodus_commit | `python commit_separate.py <repo> <convert.py> codex/r4-exodus-windows src/sim2web/convert.py` | 0 | 1.957 | [084_proposed_exodus_commit.log](logs/084_proposed_exodus_commit.log) |
| 085_proposed_workbench_tests | `python -m pytest -q tests/test_workbench.py with isolated proposed/workbench-config-hash code` | 0 | 22.650 | [085_proposed_workbench_tests.log](logs/085_proposed_workbench_tests.log) |
| 086_proposed_workbench_commit | `python commit_separate.py <repo> <workbench.py> codex/r4-workbench-config-hash src/sim2web/workbench.py` | 0 | 1.979 | [086_proposed_workbench_commit.log](logs/086_proposed_workbench_commit.log) |
| 087_patch_workbench_retry | `python patch_proposals.py <repo> C:/swv_r4_20261121 with corrected import anchor` | 0 | 1.048 | [087_patch_workbench_retry.log](logs/087_patch_workbench_retry.log) |
| 088_proposed_workbench_tests | `python -m pytest -q tests/test_workbench.py with isolated proposed/workbench-config-hash source` | 0 | 21.578 | [088_proposed_workbench_tests.log](logs/088_proposed_workbench_tests.log) |
| 089_proposed_workbench_commit | `python commit_separate.py <repo> <workbench.py> codex/r4-workbench-config-hash src/sim2web/workbench.py` | 0 | 1.583 | [089_proposed_workbench_commit.log](logs/089_proposed_workbench_commit.log) |
| 090_legacy_site | `node C:/swv_r4_20261121/legacy_screenshot.mjs --site 'G:/成果/papers/02/SimWebView_user_data_before_r4/3dec_slope_case5/site' --browser 'C:/Program Files/Google/Chrome/Application/chrome.exe' --out 'G:/成果/papers/02/codex_run_2026-11-21_r4/cases/F/r3_legacy_package.png'` | 1 | 0.401 | [090_legacy_site.log](logs/090_legacy_site.log) |
| 091_legacy_cfg | `C:/swv_r4_20261121/venv/Scripts/simwebview.exe build 'G:/成果/papers/02/SimWebView_user_data_before_r4/3dec_slope_case5/simwebview.yaml' --no-viewer --set sections.enabled=false --set output.dir=C:/swv_r4_20261121/legacy_cfg_site` | 0 | 22.383 | [091_legacy_cfg.log](logs/091_legacy_cfg.log) |
| 092_wb_ui_responsive_F_build | `node C:/swv_r4_20261121/workbench_responsive.mjs 'G:/成果/papers/02/SimWebView' C:/swv_r4_20261121/venv/Scripts/sim2web.exe C:/swv_r4_20261121/wb_responsiveness/F G:/成果/papers/02/codex_run_2026-11-21_r4/workbench/F/responsiveness_build 8781 (filter POST by kind=build)` | 0 | 119.873 | [092_wb_ui_responsive_F_build.log](logs/092_wb_ui_responsive_F_build.log) |
| 093_legacy_site_hook | `node C:/swv_r4_20261121/legacy_screenshot.mjs --site 'G:/成果/papers/02/SimWebView_user_data_before_r4/3dec_slope_case5/site' --browser 'C:/Program Files/Google/Chrome/Application/chrome.exe' --out 'G:/成果/papers/02/codex_run_2026-11-21_r4/cases/F/r3_legacy_package.png'` | 0 | 13.023 | [093_legacy_site_hook.log](logs/093_legacy_site_hook.log) |
| 094_commit_exodus-windows | `python C:/swv_r4_20261121/commit_separate.py <repo> C:/swv_r4_20261121/proposed/exodus-windows/sim2web/convert.py codex/r4-exodus-windows src/sim2web/convert.py (preserve original newline convention)` | 0 | 4.395 | [094_commit_exodus-windows.log](logs/094_commit_exodus-windows.log) |
| 094_commit_paraview-baseline | `python C:/swv_r4_20261121/commit_separate.py <repo> C:/swv_r4_20261121/paraview_baseline.py codex/r4-paraview-baseline benchmark/paraview_baseline.py (preserve original newline convention)` | 0 | 2.751 | [094_commit_paraview-baseline.log](logs/094_commit_paraview-baseline.log) |
| 094_commit_workbench-config-hash | `python C:/swv_r4_20261121/commit_separate.py <repo> C:/swv_r4_20261121/proposed/workbench-config-hash/sim2web/workbench.py codex/r4-workbench-config-hash src/sim2web/workbench.py (preserve original newline convention)` | 0 | 4.016 | [094_commit_workbench-config-hash.log](logs/094_commit_workbench-config-hash.log) |
| 095_fix_bundles | `git bundle create 'G:/成果/papers/02/codex_run_2026-11-21_r4/sim2web_r4_validation_fixes.bundle' refs/heads/codex/r4-exodus-windows refs/heads/codex/r4-paraview-baseline refs/heads/codex/r4-workbench-config-hash ^722176f; git bundle verify 'G:/成果/papers/02/codex_run_2026-11-21_r4/sim2web_r4_validation_fixes.bundle'; git bundle list-heads 'G:/成果/papers/02/codex_run_2026-11-21_r4/sim2web_r4_validation_fixes.bundle'` | 0 | 2.686 | [095_fix_bundles.log](logs/095_fix_bundles.log) |
| 096_pv_stress_selection_probe | `pvpython C:/swv_r4_20261121/pv_stress_probe.py C:/swv_r4_20261121/pv_sources/A.vtu` | 1 | 17.495 | [096_pv_stress_selection_probe.log](logs/096_pv_stress_selection_probe.log) |
| 097_pv_stress_explicit_probe | `pvpython C:/swv_r4_20261121/pv_stress_probe.py C:/swv_r4_20261121/pv_sources/A.vtu; read and explicitly set CellTensors=[Stress]` | 0 | 14.753 | [097_pv_stress_explicit_probe.log](logs/097_pv_stress_explicit_probe.log) |
| 098_pv_corrected_ABC | `python C:/swv_r4_20261121/run_paraview_corrected.py 'C:/swv_r4_20261121' 'G:/成果/papers/02/codex_run_2026-11-21_r4' 'G:\成果\papers\02\SimWebView' A C (explicit CellTensors)` | 0 | 689.744 | [098_pv_corrected_ABC.log](logs/098_pv_corrected_ABC.log) |
| 099_field_switch_A | `node C:/swv_r4_20261121/sim2web_field_switch.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/model_runs/A/site G:/成果/papers/02/codex_run_2026-11-21_r4/cases/A/field_switch.json` | 1 | 5.644 | [099_field_switch_A.log](logs/099_field_switch_A.log) |
| 099_field_switch_C | `node C:/swv_r4_20261121/sim2web_field_switch.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/model_runs/C/site G:/成果/papers/02/codex_run_2026-11-21_r4/cases/C/field_switch.json` | 1 | 6.076 | [099_field_switch_C.log](logs/099_field_switch_C.log) |
| 099_field_switch_D | `node C:/swv_r4_20261121/sim2web_field_switch.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/model_runs/D/site G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/field_switch.json` | 1 | 4.414 | [099_field_switch_D.log](logs/099_field_switch_D.log) |
| 100_generic_excavation_A | `python C:/swv_r4_20261121/generic_excavation_extras.py A C:/swv_r4_20261121/pv_sources/A.vtu C:/swv_r4_20261121/pv_baselines/A/surface.vtp C:/swv_r4_20261121/model_runs/A/site G:/成果/papers/02/codex_run_2026-11-21_r4/cases/A/paraview_excavation_extras.json` | 0 | 16.036 | [100_generic_excavation_A.log](logs/100_generic_excavation_A.log) |
| 100_generic_excavation_D | `python C:/swv_r4_20261121/generic_excavation_extras.py D C:/swv_r4_20261121/pv_sources/D.vtu C:/swv_r4_20261121/pv_baselines/D/surface.vtp C:/swv_r4_20261121/model_runs/D/site G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/paraview_excavation_extras.json` | 0 | 26.448 | [100_generic_excavation_D.log](logs/100_generic_excavation_D.log) |
| 101_glance_official_embed_D | `pvpython C:/swv_r4_20261121/reembed_glance.py C:/swv_r4_20261121/pv_baselines/D/scene.vtkjs C:/swv_r4_20261121/Glance_Kitware.html C:/swv_r4_20261121/pv_baselines/D/scene_kitware_v2.html` | 0 | 4.532 | [101_glance_official_embed_D.log](logs/101_glance_official_embed_D.log) |
| 103_final_glance_embed_A | `pvpython C:/swv_r4_20261121/reembed_glance.py C:/swv_r4_20261121/pv_baselines_corrected/A/scene.vtkjs C:/swv_r4_20261121/Glance_Kitware.html C:/swv_r4_20261121/pv_baselines_corrected/A/scene_kitware_r4.html` | 0 | 12.069 | [103_final_glance_embed_A.log](logs/103_final_glance_embed_A.log) |
| 105_case_F_screenshot_range | `node benchmark/screenshots.mjs --site C:/swv_r4_20261121/model_runs/F/site --browser 'C:/Program Files/Google/Chrome/Application/chrome.exe' --hash 'field=TotalDisplacement&range=p5_p95&section=1&layers=exterior:1:0.28' --axis y --index 12 --out G:/成果/papers/02/codex_run_2026-11-21_r4/cases/F/viewer_p5_p95_1600x900.png` | 0 | 18.583 | [105_case_F_screenshot_range.log](logs/105_case_F_screenshot_range.log) |
| 106_final_baseline_commit | `python commit_separate.py <repo> C:/swv_r4_20261121/paraview_baseline.py codex/r4-paraview-baseline benchmark/paraview_baseline.py (validated explicit CellTensors)` | 0 | 6.864 | [106_final_baseline_commit.log](logs/106_final_baseline_commit.log) |
| 107_final_fix_bundle | `git bundle create 'G:/成果/papers/02/codex_run_2026-11-21_r4/sim2web_r4_validation_fixes.bundle' refs/heads/codex/r4-exodus-windows refs/heads/codex/r4-paraview-baseline refs/heads/codex/r4-workbench-config-hash ^722176f; git bundle verify 'G:/成果/papers/02/codex_run_2026-11-21_r4/sim2web_r4_validation_fixes.bundle'; git bundle list-heads 'G:/成果/papers/02/codex_run_2026-11-21_r4/sim2web_r4_validation_fixes.bundle'` | 0 | 1.385 | [107_final_fix_bundle.log](logs/107_final_fix_bundle.log) |
| 108_final_repo_state | `git status --short --branch; git rev-parse HEAD; git diff --stat HEAD -- src; git branch --list codex/r3-abaqus-exporter-guards -v` | 0 | 1.473 | [108_final_repo_state.log](logs/108_final_repo_state.log) |
| 109_retire_superseded_glance_probes | `Stop the two superseded Glance probe wrappers for first-round A/C files without explicit principal arrays; verify based on exact node executable argv` | 0 | 4.100 | [109_retire_superseded_glance_probes.log](logs/109_retire_superseded_glance_probes.log) |
| 110_field_switch_A | `node C:/swv_r4_20261121/sim2web_field_switch.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/model_runs/A/site G:/成果/papers/02/codex_run_2026-11-21_r4/cases/A/field_switch.json (normalized Windows static root)` | 0 | 6.731 | [110_field_switch_A.log](logs/110_field_switch_A.log) |
| 110_field_switch_C | `node C:/swv_r4_20261121/sim2web_field_switch.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/model_runs/C/site G:/成果/papers/02/codex_run_2026-11-21_r4/cases/C/field_switch.json (normalized Windows static root)` | 0 | 6.896 | [110_field_switch_C.log](logs/110_field_switch_C.log) |
| 110_field_switch_D | `node C:/swv_r4_20261121/sim2web_field_switch.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/model_runs/D/site G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/field_switch.json (normalized Windows static root)` | 0 | 6.550 | [110_field_switch_D.log](logs/110_field_switch_D.log) |
| 111_retire_blocked_glance | `Stop blocked Glance v2 processes after retaining measured A first frame; filter by absolute command line and own test names` | 0 | 1.968 | [111_retire_blocked_glance.log](logs/111_retire_blocked_glance.log) |
| 112_browser_final_embed_A | `pvpython C:/swv_r4_20261121/reembed_glance.py C:/swv_r4_20261121/pv_baselines_corrected/A/scene.vtkjs C:/swv_r4_20261121/Glance_Kitware.html C:/swv_r4_20261121/pv_baselines_corrected/A/scene_kitware_standalone.html` | 0 | 3.473 | [112_browser_final_embed_A.log](logs/112_browser_final_embed_A.log) |
| 112_browser_final_embed_C | `pvpython C:/swv_r4_20261121/reembed_glance.py C:/swv_r4_20261121/pv_baselines_corrected/C/scene.vtkjs C:/swv_r4_20261121/Glance_Kitware.html C:/swv_r4_20261121/pv_baselines_corrected/C/scene_kitware_standalone.html` | 0 | 5.196 | [112_browser_final_embed_C.log](logs/112_browser_final_embed_C.log) |
| 112_browser_final_embed_D | `pvpython C:/swv_r4_20261121/reembed_glance.py C:/swv_r4_20261121/pv_baselines/D/scene.vtkjs C:/swv_r4_20261121/Glance_Kitware.html C:/swv_r4_20261121/pv_baselines/D/scene_kitware_standalone.html` | 0 | 3.024 | [112_browser_final_embed_D.log](logs/112_browser_final_embed_D.log) |
| 113_glance_final_A | `node C:/swv_r4_20261121/glance_browser_final.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/pv_baselines_corrected/A/scene_kitware_standalone.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/A/paraview_corrected/glance_official_browser.json no_screenshot 3` | 0 | 142.481 | [113_glance_final_A.log](logs/113_glance_final_A.log) |
| 113_glance_final_C | `node C:/swv_r4_20261121/glance_browser_final.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/pv_baselines_corrected/C/scene_kitware_standalone.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/C/paraview_corrected/glance_official_browser.json no_screenshot 3` | 1 | 312.593 | [113_glance_final_C.log](logs/113_glance_final_C.log) |
| 113_glance_final_D | `node C:/swv_r4_20261121/glance_browser_final.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/pv_baselines/D/scene_kitware_standalone.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/glance_official_browser.json no_screenshot 3` | 0 | 69.891 | [113_glance_final_D.log](logs/113_glance_final_D.log) |
| 114_pv_native_trace_probe | `pvpython C:/swv_r4_20261121/smtrace_probe.py` | 0 | 9.730 | [114_pv_native_trace_probe.log](logs/114_pv_native_trace_probe.log) |
| 115_candidate_wb_ogs_hash | `python C:/swv_r4_20261121/workbench_hash_retest.py <E case.yaml> C:/swv_r4_20261121/wb_hash_retest G:/成果/papers/02/codex_run_2026-11-21_r4/workbench/E/candidate_retest.json` | 0 | 25.592 | [115_candidate_wb_ogs_hash.log](logs/115_candidate_wb_ogs_hash.log) |
| 116_pv_desktop_trace_export | `Stop owned first GUI macro after capturing A; Start-Process 'C:\swv_r4_20261121\paraview\ParaView-5.13.3-Windows-Python3.10-msvc2017-AMD64\bin\paraview.exe' --script=C:/swv_r4_20261121/pv_gui_optimized.py` | 0 | 2.932 | [116_pv_desktop_trace_export.log](logs/116_pv_desktop_trace_export.log) |
| 117_workbench_A_retry | `python C:/swv_r4_20261121/drive_workbench.py A 'G:\成果\papers\02\SimWebView' 'C:/swv_r4_20261121' 'G:/成果/papers/02/codex_run_2026-11-21_r4'` | 0 | 377.538 | [117_workbench_A_retry.log](logs/117_workbench_A_retry.log) |
| 118_glance_changes_A | `node C:/swv_r4_20261121/glance_workflow_switch.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/pv_baselines_corrected/A/scene_kitware_standalone.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/A/paraview_corrected/glance_interaction.json no_screenshot 1` | 0 | 39.906 | [118_glance_changes_A.log](logs/118_glance_changes_A.log) |
| 118_glance_changes_C | `node C:/swv_r4_20261121/glance_workflow_switch.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/pv_baselines_corrected/C/scene_kitware_standalone.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/C/paraview_corrected/glance_interaction.json no_screenshot 1` | 1 | 128.692 | [118_glance_changes_C.log](logs/118_glance_changes_C.log) |
| 118_glance_changes_D | `node C:/swv_r4_20261121/glance_workflow_switch.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/pv_baselines/D/scene_kitware_standalone.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/glance_interaction.json no_screenshot 1` | 0 | 49.677 | [118_glance_changes_D.log](logs/118_glance_changes_D.log) |
| 119_reordered_principal_A | `python C:/swv_r4_20261121/reorder_principal_check.py 'G:/成果/papers/02/SimWebView/examples/flac3d_cavern_iv2/input/IV-2.vtu' G:/成果/papers/02/codex_run_2026-11-21_r4/cases/A/paraview_principal_reordered.json` | 0 | 22.932 | [119_reordered_principal_A.log](logs/119_reordered_principal_A.log) |
| 119_reordered_principal_C | `python C:/swv_r4_20261121/reorder_principal_check.py 'G:/成果/papers/02/SimWebView/examples/3dec_slope/input/slopemodel.vtu' G:/成果/papers/02/codex_run_2026-11-21_r4/cases/C/paraview_principal_reordered.json` | 0 | 12.553 | [119_reordered_principal_C.log](logs/119_reordered_principal_C.log) |
| 119_reordered_principal_D | `python C:/swv_r4_20261121/reorder_principal_check.py 'G:/成果/papers/02/case4/EXC12_dis.vtu' G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/paraview_principal_reordered.json` | 0 | 20.101 | [119_reordered_principal_D.log](logs/119_reordered_principal_D.log) |
| 120_glance_archive_contents | `python C:/swv_r4_20261121/audit_glance_content.py A <corrected A scene> C <corrected C scene> D <D scene>` | 0 | 1.482 | [120_glance_archive_contents.log](logs/120_glance_archive_contents.log) |
| 121_native_trace_complete_probe | `pvpython C:/swv_r4_20261121/smtrace_complete_probe.py (probe native property and exporter trace hooks)` | 0 | 12.467 | [121_native_trace_complete_probe.log](logs/121_native_trace_complete_probe.log) |
| 122_pv_desktop_complete_traces | `Retain partial optimized traces; Stop owned previous desktop macro; Start-Process 'C:\swv_r4_20261121\paraview\ParaView-5.13.3-Windows-Python3.10-msvc2017-AMD64\bin\paraview.exe' --script=C:/swv_r4_20261121/pv_gui_complete.py` | 0 | 1.058 | [122_pv_desktop_complete_traces.log](logs/122_pv_desktop_complete_traces.log) |
| 123_glance_controls_probe | `node C:/swv_r4_20261121/glance_dom_probe.mjs 'G:\成果\papers\02\SimWebView' <small D Glance smoke> G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/glance_controls.json no_screenshot 1` | 0 | 7.671 | [123_glance_controls_probe.log](logs/123_glance_controls_probe.log) |
| 125_glance_geometry_controls_probe | `node C:/swv_r4_20261121/glance_dom_geometry_probe.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/pv_smoke/scene_kitware.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/glance_geometry_controls.json no_screenshot 1` | 0 | 10.620 | [125_glance_geometry_controls_probe.log](logs/125_glance_geometry_controls_probe.log) |
| 127_glance_model_event_A | `node C:/swv_r4_20261121/glance_geometry_events.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/pv_baselines_corrected/A/scene_kitware_standalone.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/A/paraview_corrected/glance_model_event.json no_screenshot 1` | 1 | 164.320 | [127_glance_model_event_A.log](logs/127_glance_model_event_A.log) |
| 127_glance_model_event_C | `node C:/swv_r4_20261121/glance_geometry_events.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/pv_baselines_corrected/C/scene_kitware_standalone.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/C/paraview_corrected/glance_model_event.json no_screenshot 1` | 1 | 164.474 | [127_glance_model_event_C.log](logs/127_glance_model_event_C.log) |
| 127_glance_model_event_D | `node C:/swv_r4_20261121/glance_geometry_events.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/pv_baselines/D/scene_kitware_standalone.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/glance_model_event.json no_screenshot 1` | 1 | 166.150 | [127_glance_model_event_D.log](logs/127_glance_model_event_D.log) |
| 128_retire_blocked_geometry_poll | `Stop owned Playwright waitForFunction probe for embedded D after >7 min with no response; retain event-based trials` | 0 | 1.889 | [128_retire_blocked_geometry_poll.log](logs/128_retire_blocked_geometry_poll.log) |
| 129_glance_split_physical_D | `node C:/swv_r4_20261121/glance_geometry_events.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/Glance_Kitware.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/glance_split_model_event.json no_screenshot 1 C:/swv_r4_20261121/pv_baselines/D/scene.vtkjs` | 0 | 42.795 | [129_glance_split_physical_D.log](logs/129_glance_split_physical_D.log) |
| 130_glance_split_geometry_A | `node C:/swv_r4_20261121/glance_geometry_events.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/Glance_Kitware.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/A/paraview_corrected/glance_split_geometry_browser.json no_screenshot 3 C:/swv_r4_20261121/pv_baselines_corrected/A/scene.vtkjs` | 0 | 105.391 | [130_glance_split_geometry_A.log](logs/130_glance_split_geometry_A.log) |
| 130_glance_split_geometry_C | `node C:/swv_r4_20261121/glance_geometry_events.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/Glance_Kitware.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/C/paraview_corrected/glance_split_geometry_browser.json no_screenshot 3 C:/swv_r4_20261121/pv_baselines_corrected/C/scene.vtkjs` | 0 | 149.047 | [130_glance_split_geometry_C.log](logs/130_glance_split_geometry_C.log) |
| 130_glance_split_geometry_D | `node C:/swv_r4_20261121/glance_geometry_events.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/Glance_Kitware.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/glance_split_geometry_browser.json no_screenshot 3 C:/swv_r4_20261121/pv_baselines/D/scene.vtkjs` | 0 | 78.237 | [130_glance_split_geometry_D.log](logs/130_glance_split_geometry_D.log) |
| 131_retire_desktop_cleanup | `Stop owned ParaView macro stuck deleting completed D proxies; retain complete D traces` | 0 | 0.922 | [131_retire_desktop_cleanup.log](logs/131_retire_desktop_cleanup.log) |
| 132_pv_desktop_A | `Start-Process 'C:\swv_r4_20261121\paraview\ParaView-5.13.3-Windows-Python3.10-msvc2017-AMD64\bin\paraview.exe' --script=C:/swv_r4_20261121/pv_gui_one_case.py with R4_PV_TRACE_CASE=A; wait for native Trace and export result` | 0 | 340.633 | [132_pv_desktop_A.log](logs/132_pv_desktop_A.log) |
| 132_pv_desktop_C | `Start-Process 'C:\swv_r4_20261121\paraview\ParaView-5.13.3-Windows-Python3.10-msvc2017-AMD64\bin\paraview.exe' --script=C:/swv_r4_20261121/pv_gui_one_case.py with R4_PV_TRACE_CASE=C; wait for native Trace and export result` | 0 | 766.918 | [132_pv_desktop_C.log](logs/132_pv_desktop_C.log) |
| 133_glance_control_smoke | `node C:/swv_r4_20261121/glance_split_switch.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/Glance_Kitware.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/glance_split_controls_smoke.json no_screenshot 1 C:/swv_r4_20261121/pv_smoke/scene.vtkjs` | 0 | 31.862 | [133_glance_control_smoke.log](logs/133_glance_control_smoke.log) |
| 135_trace_audit_A | `python C:/swv_r4_20261121/audit_native_trace.py G:/成果/papers/02/codex_run_2026-11-21_r4/cases/A/paraview_gui_native_trace.py G:/成果/papers/02/codex_run_2026-11-21_r4/cases/A/index.json G:/成果/papers/02/codex_run_2026-11-21_r4/cases/A/paraview_gui_trace_audit.json` | 0 | 0.327 | [135_trace_audit_A.log](logs/135_trace_audit_A.log) |
| 135_trace_audit_C | `python C:/swv_r4_20261121/audit_native_trace.py G:/成果/papers/02/codex_run_2026-11-21_r4/cases/C/paraview_gui_native_trace.py G:/成果/papers/02/codex_run_2026-11-21_r4/cases/C/index.json G:/成果/papers/02/codex_run_2026-11-21_r4/cases/C/paraview_gui_trace_audit.json` | 0 | 0.388 | [135_trace_audit_C.log](logs/135_trace_audit_C.log) |
| 135_trace_audit_D | `python C:/swv_r4_20261121/audit_native_trace.py G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/paraview_gui_native_trace.py G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/index.json G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/paraview_gui_trace_audit.json` | 0 | 0.873 | [135_trace_audit_D.log](logs/135_trace_audit_D.log) |
| 136_bound_glance_controls | `Retire own superseded direct control harness with no rendered switch response; use bounded per-phase trials` | 0 | 0.959 | [136_bound_glance_controls.log](logs/136_bound_glance_controls.log) |
| 137_glance_bounded_switch_A | `node C:/swv_r4_20261121/glance_split_switch_bounded.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/Glance_Kitware.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/A/paraview_corrected/glance_geometry_interaction.json no_screenshot 1 C:/swv_r4_20261121/pv_baselines_corrected/A/scene.vtkjs` | 0 | 69.157 | [137_glance_bounded_switch_A.log](logs/137_glance_bounded_switch_A.log) |
| 137_glance_bounded_switch_C | `node C:/swv_r4_20261121/glance_split_switch_bounded.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/Glance_Kitware.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/C/paraview_corrected/glance_geometry_interaction.json no_screenshot 1 C:/swv_r4_20261121/pv_baselines_corrected/C/scene.vtkjs` | 0 | 77.025 | [137_glance_bounded_switch_C.log](logs/137_glance_bounded_switch_C.log) |
| 137_glance_bounded_switch_D | `node C:/swv_r4_20261121/glance_split_switch_bounded.mjs 'G:\成果\papers\02\SimWebView' C:/swv_r4_20261121/Glance_Kitware.html G:/成果/papers/02/codex_run_2026-11-21_r4/cases/D/glance_geometry_interaction.json no_screenshot 1 C:/swv_r4_20261121/pv_baselines/D/scene.vtkjs` | 0 | 64.900 | [137_glance_bounded_switch_D.log](logs/137_glance_bounded_switch_D.log) |
| 138_delivery_content_check | `python C:/swv_r4_20261121/qa_r4.py G:/成果/papers/02/codex_run_2026-11-21_r4` | 0 | 0.313 | [138_delivery_content_check.log](logs/138_delivery_content_check.log) |
| 139_retire_unused_control_wait | `Stop the owned PowerShell waiter for superseded Glance control tests after bounded split tests completed` | 0 | 0.084 | [139_retire_unused_control_wait.log](logs/139_retire_unused_control_wait.log) |
