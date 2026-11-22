# 论文图 2 · 算例 D 工作台与发布查看器

2026-11-22 JST。按 Drive 中的 fig2_layout_mock.png 拼版。算例为 FLAC3D 深基坑（examples/flac3d_pit_case4，施工步 EXC12_dis）。左栏的工作台项目和右栏发布查看器读取同一次实际构建的结果，Sim2Web 版本 0.2.0。原构建记录为 60.234 s，112 个剖面，阶段数据产品 61,202,916 字节。独立验证通过，共检查 114 个产品，精确不符 0 个。

## (a) 工作台原生截图

在 880 × 820 CSS 像素的工作台窗口分别截取左侧六步和右侧完整诊断，第 3 步为当前步。两张截图均保持原生字号和原文，等比放进浅灰外框。为保留全部诊断且控制整图高度，六步栏以较小比例缩放。

| 诊断 | 截图显示原文 |
|---|---|
| Model | 548,417 cells, 332,510 points |
| Stress component order | Read from the file: XX, YY, ZZ, XY, XZ, YZ |
| Stress unit | MPa: implied unit weight 14.6 kN/m³ |
| Excavation surface (EXC12_dis) | 17,004 faces, 6,418 m² |
| Mesh interfaces (EXC12_dis) | 85,215 faces with rock on both sides left out of the excavation surface |
| Internal faces (EXC12_dis) | 89,901 block-contact faces removed from the exterior |
| Validation | Every published value matches the source model |

## (b) 同一结果的发布查看器

- 着色量为 **位移模量 TotalDisplacement（m）**，点数据。两个可见图层为外表面（不透明度 35%）和开挖面（100%）。使用 viridis、8 档。图 3(d) 使用开挖面上的 Y 向位移。
- 使用 EXC12_dis 施工步的 P5–P95 色标。两层相同的实测色标下限为 **4.841852915e-05 m**，上限为 **0.005555023806 m**。图中端点显示为 **4.842e-5 m** 和 **0.005555 m**。
- 正交视图，从水平向下俯视 **35°**，方位角 **228°**，相机滚转 **-48°**。放大到基坑及周边外表面，剖面关闭。查看器顶部取景裁掉了方向标。

## 印刷核验

- PNG 为 3898 × 2268 像素，RGB，**16.50 × 9.60 cm**，**600 dpi**，共 **1,740,837 字节**。
- 左栏宽 **5.00 cm**，右栏宽 **11.10 cm**。两栏外左上角标签为 **9 pt 粗体**。浏览器截图以 deviceScaleFactor 4 获取，分图最低有效密度 **720.6 dpi**。
- 诊断正文印刷名义字号 **5.00 pt**，六步标签 **3.35 pt**，右栏色标标题 **6.12 pt**、刻度 **5.97 pt**。
- PNG SHA-256 为 505c3a95d5dc5f565156d07af86c28dec87aec791a1c0e372a23c568c507c266。

## 仅在 (b) 注入的 CSS

左栏没有注入样式。应用源码未修改。

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

## 截图命令

| 命令 | 退出码 | 耗时（s） |
|---|---:|---:|
| Verify the existing Case D 0.2.0 build and passing validation before taking both screenshots from it | 0 | 0.119 |
| python -m sim2web gui C:/swv_fig2_native_20261122/project --port 18813 --no-browser | 0 | 1.841 |
| node C:/swv_fig2_mock_20261122/capture_mock.mjs 'G:\成果\papers\02\SimWebView' http://127.0.0.1:18813 C:/swv_fig2_mock_20261122/captures | 0 | 16.243 |
| python -m sim2web gui C:/swv_fig2_native_20261122/project --port 18813 --no-browser | 0 | 2.143 |
| node C:/swv_fig2_mock_20261122/capture_mock.mjs 'G:\成果\papers\02\SimWebView' http://127.0.0.1:18813 C:/swv_fig2_mock_20261122/captures | 0 | 14.936 |
| python -m sim2web gui C:/swv_fig2_native_20261122/project --port 18813 --no-browser | 0 | 1.724 |
| node C:/swv_fig2_mock_20261122/capture_mock.mjs 'G:\成果\papers\02\SimWebView' http://127.0.0.1:18813 C:/swv_fig2_mock_20261122/captures | 0 | 14.246 |
| python C:/swv_fig2_mock_20261122/compose_mock.py close | 0 | 1.906 |
