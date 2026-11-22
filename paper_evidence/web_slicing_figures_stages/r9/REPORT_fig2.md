# 论文图 2 · 算例 D 的真实工作台

2026-11-22 JST。Sim2Web 0.2.0，FLAC3D 深基坑，输入 EXC12_dis.vtu。在独立项目中按算例 D 配置构建并验证，再回到第 3 步生成表面预览。整页采用原版布局和字号，左侧六步、几何设置、中央预览、右侧诊断和折叠后的日志条均在截图中。嵌入查看器的控制栏保持展开。

## 画面里的全部诊断

以下为实际界面原文。

| 诊断 | 显示值 |
|---|---|
| Model | 548,417 cells, 332,510 points |
| Stress component order | Read from the file: XX, YY, ZZ, XY, XZ, YZ |
| Stress unit | MPa: implied unit weight 14.6 kN/m³ |
| Excavation surface (EXC12_dis) | 17,004 faces, 6,418 m² |
| Mesh interfaces (EXC12_dis) | 85,215 faces with rock on both sides left out of the excavation surface |
| Internal faces (EXC12_dis) | 89,901 block-contact faces removed from the exterior |
| Validation | Every published value matches the source model |

单位 MPa 的等效重度在界面为 14.6 kN/m³，未舍入值为 14.619231 kN/m³。开挖面面积为 6,418.370 m²。两类排除面分别来自开挖面候选和外表面候选。

## 本次构建及验证

| 项目 | 实测值 |
|---|---:|
| 外表面 | 20,293 面，2,248,198 字节 |
| 开挖面 | 17,004 面，1,785,830 字节 |
| 从开挖面候选排除的内部界面 | 85,215 面 |
| 从外表面去除的块体接触面 | 89,901 面 |
| 剖面 | 112 个 |
| 阶段数据产品 | 61,202,916 字节（61.20 MB） |
| 完整静态目录，含查看器及验证文件 | 62,992,593 字节（62.99 MB） |
| 构建总时长 | 60.234 s |
| 工作台构建任务 | 61.428 s |
| 工作台完整验证任务 | 20.052 s |
| 工作台用于截图的预览任务 | 15.785 s |

验证通过。检查 114 个产品、806 个精确数组和 4,638,297 个精确元组，精确不符 0 个。插值数组 448 个，最大插值 nRMSE 为 3.346e-07，失败 0 项。面数和字节数来自两份 model_cache/index.json，耗时来自 build_report.json 与工作台任务响应，验证结果来自 validation_summary.json。

## 取景与印刷

- 原生 Chrome 160.0.8157.0，视口 1280 × 800 CSS px，deviceScaleFactor 4。
- 外表面不透明度 35%，开挖面 100%，着色字段为 TotalDisplacement，色标 viridis、P5–P95。正交相机仰角 75°，即从水平向下俯视 75°，方位角 183°。对 489 个坑底面中心做正交射线核对。35° 时，测试的 8 个方位均受坑壁遮挡。为保留清楚可见的坑底，最终取 75°，所选方位有 198 个坑底面中心可直接看到。
- 未注入 CSS。PNG 保留整窗的 5120 × 3200 像素，宽 16.50 cm，实际 788.16 dpi，共 1,143,129 字节。
- 主要原生控件的字号按印刷宽度折算为 4.57–5.48 pt。实际墨迹高度因字形而异，最小采样值为 3.65 pt。
- PNG SHA-256 为 a8ffd3430bcbba8712eb38786a406694b9ec4ae02f37e52ab6296b58b78afaa8。

## 命令记录

| 命令 | 退出码 | 耗时（s） |
|---|---:|---:|
| Copy Case D configuration and VTU into a clean project; check Sim2Web version | 0 | 3.088 |
| npm run build | 0 | 9.337 |
| python -m sim2web gui C:/swv_fig2_native_20261122/project --port 18811 --no-browser | 0 | 1.820 |
| node C:/swv_fig2_native_20261122/capture_native.mjs 'G:\成果\papers\02\SimWebView' http://127.0.0.1:18811/workbench/ C:/swv_fig2_native_20261122/captures | 0 | 109.724 |
| python -m sim2web gui C:/swv_fig2_native_20261122/project --port 18811 --no-browser | 0 | 1.600 |
| node C:/swv_fig2_native_20261122/capture_native.mjs 'G:\成果\papers\02\SimWebView' http://127.0.0.1:18811/workbench/ C:/swv_fig2_native_20261122/captures --floor-views | 0 | 29.571 |
