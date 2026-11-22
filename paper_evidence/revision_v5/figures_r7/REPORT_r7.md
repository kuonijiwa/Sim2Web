# Sim2Web r7 印刷截图

在 Windows Chrome 中重截图 2 和图 4。图 2 上下排两张，图 4 按 A–F 两列三行。
原尺寸校样在 `contact_sheets_100pct.pdf`，按 100% 打印。两张主图以 16.5 cm 宽交付。

## 印刷核验

| 图 | 高度（cm） | 分图 | 截图倍数 | 分图有效 dpi | 最小有效字高（pt） |
|---|---:|---|---:|---:|---:|
| 2 | 16.765 | (a) | 4 | 689.6 | 7.10 |
| 2 | 16.765 | (b) | 4 | 689.6 | 6.26 |
| 4 | 16.879 | (a) | 3 | 903.1 | 6.22 |
| 4 | 16.879 | (b) | 3 | 903.1 | 6.22 |
| 4 | 16.879 | (c) | 3 | 903.1 | 6.22 |
| 4 | 16.879 | (d) | 3 | 903.1 | 6.22 |
| 4 | 16.879 | (e) | 3 | 903.1 | 6.22 |
| 4 | 16.879 | (f) | 3 | 903.1 | 6.22 |

图 4 的模型覆盖分图宽度 73.2%–73.5%。字高按浏览器文字墨迹边界测量，并按分图实际印刷宽度折算。标签统一 9 pt 粗体，位于白色标签区，分图间距为 2 mm。

## 画面状态

图 2 从独立工作台工程实际读取算例 E，截图 (a) 显示构建阻塞、应力顺序选择和 16.5 kN/m³ 单位诊断。
截图 (b) 在真实构建和独立验证全部通过后截取，保留构建表、验证摘要与发布查看器。为了让诊断区易读，隔离工程把同一 VTU 的副本命名为 `ogs_slope.vtu`。

图 4 的字段、剖面位置、色图、色阶和范围模式按现有稿件复现。六幅色标端点逐幅与原图核对。C 保留 X = 830 m 剖面，E 保留 Y = 30 m 剖面，F 使用 P5–P95。
六幅都收起侧栏并用正交相机重新取景。C 的附加点选卡为排版移除。
(a) 通过查看器实际点选回原来的 `Source_Cell_ID 1160199`，读数为 **-6.857 MPa**。
D、F 的公开拼版与单张图来自本地既有发布包。结果提交包含最终图片和印刷核验所需的版面参数。

首次拉取遇到旧图 3 的 Git LFS 对象返回 404，跳过历史图片下载后检出 `92f40f5`。状态核对所用的旧图从 v6 稿件中提取。
命令、退出码和耗时见 `COMMANDS.csv`。构图计算的中间记录留在本机临时目录。

## Playwright 注入 CSS

### 图 2(a) 字段与单位

```css
.top, .steps, .log, .nav-buttons { display: none !important; }
.app { grid-template-rows: auto; height: auto; background: #fff; }
.form, .diagnostics { overflow: visible; }
.form { padding: 16px 20px 14px; }
.form h2, .diagnostics h2 { font-size: 26px; line-height: 1.15; }
.form h3 { font-size: 22px; margin: 7px 0 5px; }
.form .notice, .diagnostics .title, .diagnostics .detail { font-size: 21px; line-height: 1.23; }
.form .notice { margin: 5px 0 0; }
.app { grid-template-columns: minmax(0, 2.14fr) minmax(0, 1fr); grid-template-areas: 'centre diag'; }
.centre { display: block; }
.viewer { display: none; }
.form .row { grid-template-columns: 155px minmax(0, 1fr); gap: 10px; padding: 4px 0; }
.form .row > label, .form .row select { font-size: 21px; }
.form .row select { max-width: 100%; font: 400 23px/1.2 'Arial Narrow', Arial, sans-serif; }
.form .row:nth-of-type(1), .form .row:nth-of-type(2), .form .row:nth-of-type(3), .form .row:nth-of-type(6),
.form h3:first-of-type, .form h3:last-of-type, .form > div > .hint, .form table.data, .form > div > p.muted,
.diagnostics li:not(.error):not(.ok) { display: none; }
.diagnostics { padding: 16px 14px; }
.diagnostics li { padding: 9px 10px; }
```

### 图 2(b) 构建与验证

```css
.top, .steps, .log, .nav-buttons { display: none !important; }
.app { grid-template-rows: auto; height: auto; background: #fff; }
.form, .diagnostics { overflow: visible; }
.form { padding: 16px 20px 14px; }
.form h2, .diagnostics h2 { font-size: 26px; line-height: 1.15; }
.form h3 { font-size: 22px; margin: 7px 0 5px; }
.form .notice, .diagnostics .title, .diagnostics .detail { font-size: 21px; line-height: 1.23; }
.form .notice { margin: 5px 0 0; }
.app { grid-template-columns: minmax(0, 1fr); grid-template-areas: 'centre'; }
.centre { grid-template-rows: auto 268px; }
.diagnostics, .form > div > p.muted, .form > div > .inline { display: none; }
.form .hint, .form table.data { font-size: 20px; line-height: 1.12; }
.form table.data td, .form table.data th { padding: 3px 8px; }
.form table.data:nth-of-type(2) tbody tr:nth-child(n+4) { display: none; }
.viewer-label { font-size: 21px; }
```

### 图 4(a–f) 共用查看器样式

```css
.panel.collapsed { display: none !important; }
.right { top: 8px !important; right: 8px !important; bottom: auto !important; gap: 0 !important; }
.legend { width: 232px; min-width: 0 !important; padding: 10px; box-shadow: none !important; background: #fff !important; }
.legend-title { font: 700 38px/1.06 'Arial Narrow', Arial, sans-serif !important; color: #1f2d3d; margin-bottom: 14px !important; }
.legend-sub { display: none !important; }
.bands { font: 400 36px/1 Arial, sans-serif !important; font-variant-numeric: tabular-nums; }
.band-row { height: 39px !important; gap: 7px !important; }
.band-row .tick { transform: translateY(-5px) !important; white-space: nowrap; }
.band-row .swatch { flex: 0 0 16px; }
.band-row .swatch.tall { height: 39px !important; }
.band-row.last { height: 30px !important; }
```

### 图 2(b) 内嵌查看器

```css
.panel.collapsed { display: none !important; }
.right { display: none !important; }
```

### 图 4(a) 点选读数卡

```css
.probe { position: fixed; left: 8px; top: 8px; width: 706px !important; max-height: none !important;
  padding: 7px 11px; box-shadow: none !important; background: #fff !important; }
.probe-head { font-size: 27px !important; }
.probe-head .link { display: none; }
.probe .kv { font-size: 26px !important; margin-top: 2px !important; }
.probe .kv td { padding: 2px 4px !important; }
.probe .kv tr:not(:nth-child(2)):not(.active) { display: none; }
```
