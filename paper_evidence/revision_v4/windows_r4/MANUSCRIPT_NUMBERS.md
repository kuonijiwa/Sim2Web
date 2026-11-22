# Sim2Web r4 稿件填数表

Windows 11 中文版，同一工作站。MB = 1,000,000 B。路径相对本次交付目录。

| 位置 | 数值 | 来源文件 | 备注 |
|---|---|---|---|
| 表 3 / M1 / 算例 A | ParaView 8,443 行（有效 5,411）；Sim2Web 改 36 行，14 次点击 | cases/A/paraview_gui_native_trace.py、cases/A/paraview_gui_trace_audit.json、cases/A/draft_delta.json、workbench/A/click_count.json | 桌面宏生成的行数与纯手工流程分列。Sim2Web 有序归一化 YAML 差异；点击从已载入配置开始。GUI Trace 包含读入、剖切与导出调用。 |
| 表 3 / M2 / 算例 A | ParaView pvpython 194.505 s，桌面宏 326.168 s；Sim2Web 构建 99.566 s，验证 122.070 s | cases/A/paraview_corrected/paraview_baseline_report.json；logs/034_build_A.json；logs/035_validate_A.json | 同机；桌面宏直接导出，pvpython 另含逐个写出 VTP。纯手工操作时间未测；替代模板重封装时间单列于对比 JSON。 |
| 表 3 / M3 / 算例 A | Glance HTML 256,286,362 B（256.286 MB）；vtkjs 180,133,823 B（180.134 MB）；ParaView 表面 11,918,924 B（11.919 MB）；Sim2Web 主表面 5,099,246 B（5.099 MB）、完整站点 84,502,592 B（84.503 MB） | cases/A/paraview_corrected/paraview_baseline_report.json；cases/A/paraview_corrected/scene_kitware_size.json；cases/A/build_report.json；cases/A/site_size.json | Glance HTML 使用 Kitware 官方可绘制模板。站点排除验证输出；十进制 MB。 |
| 表 3 / M4 / 算例 A | Glance 31,214.0 ms（3/3），Sim2Web 2,868.8 ms，首帧传输 6,071,587 B（6.072 MB），剖面切换 89.9 ms | cases/A/paraview_corrected/glance_split_geometry_browser.json；cases/A/sim2web_browser.json | Chrome 冷缓存回环测试。使用 Kitware 查看器与同一 vtkjs 文件分开加载的流程。模型几何提交（至少 10,000 个索引）和两次动画帧计时，坐标轴控件已排除。Sim2Web 使用查看器 firstRender。 |
| 表 3 / 开挖面手工步骤 / 算例 A | 新增 4 个处理操作 | comparison_results.json / M7 | 对同一 absmax 再取互补空区分支；提取空区面；按接触容差筛出实体一侧的相邻面；将筛选结果单独着色并导出。 算例 A/D 的追加处理见 cases/A/paraview_excavation_extras.json。 |
| 表 3 / M1 / 算例 C | ParaView 9,642 行（有效 6,192）；Sim2Web 改 17 行，14 次点击 | cases/C/paraview_gui_native_trace.py、cases/C/paraview_gui_trace_audit.json、cases/C/draft_delta.json、workbench/C/click_count.json | 桌面宏生成的行数与纯手工流程分列。Sim2Web 有序归一化 YAML 差异；点击从已载入配置开始。GUI Trace 包含读入、剖切与导出调用。 |
| 表 3 / M2 / 算例 C | ParaView pvpython 364.272 s，桌面宏 747.236 s；Sim2Web 构建 101.590 s，验证 344.270 s | cases/C/paraview_corrected/paraview_baseline_report.json；logs/034_build_C.json；logs/035_validate_C.json | 同机；桌面宏直接导出，pvpython 另含逐个写出 VTP。纯手工操作时间未测；替代模板重封装时间单列于对比 JSON。 |
| 表 3 / M3 / 算例 C | Glance HTML 440,648,222 B（440.648 MB）；vtkjs 318,405,218 B（318.405 MB）；ParaView 表面 187,591,097 B（187.591 MB）；Sim2Web 主表面 2,620,417 B（2.620 MB）、完整站点 133,851,840 B（133.852 MB） | cases/C/paraview_corrected/paraview_baseline_report.json；cases/C/paraview_corrected/scene_kitware_size.json；cases/C/build_report.json；cases/C/site_size.json | Glance HTML 使用 Kitware 官方可绘制模板。站点排除验证输出；十进制 MB。 |
| 表 3 / M4 / 算例 C | Glance 49,043.2 ms（3/3），Sim2Web 2,661.6 ms，首帧传输 3,619,133 B（3.619 MB），剖面切换 132.6 ms | cases/C/paraview_corrected/glance_split_geometry_browser.json；cases/C/sim2web_browser.json | Chrome 冷缓存回环测试。使用 Kitware 查看器与同一 vtkjs 文件分开加载的流程。模型几何提交（至少 10,000 个索引）和两次动画帧计时，坐标轴控件已排除。Sim2Web 使用查看器 firstRender。 |
| 表 3 / 开挖面手工步骤 / 算例 C | 新增 0 个处理操作 | comparison_results.json / M7 | 本协议仅要求边坡外表面，不设坑腔层。若需要与 Sim2Web 外表面等效，还要单独去除块体间内部面。 算例 A/D 的追加处理见 cases/C/paraview_excavation_extras.json。 |
| 表 3 / M1 / 算例 D | ParaView 7,149 行（有效 4,579）；Sim2Web 改 35 行，14 次点击 | cases/D/paraview_gui_native_trace.py、cases/D/paraview_gui_trace_audit.json、cases/D/draft_delta.json、workbench/D/click_count.json | 桌面宏生成的行数与纯手工流程分列。Sim2Web 有序归一化 YAML 差异；点击从已载入配置开始。GUI Trace 包含读入、剖切与导出调用。 |
| 表 3 / M2 / 算例 D | ParaView pvpython 165.219 s，桌面宏 514.661 s；Sim2Web 构建 144.505 s，验证 81.520 s | cases/D/paraview_baseline_report.json；logs/034_build_D.json；logs/035_validate_D.json | 同机；桌面宏直接导出，pvpython 另含逐个写出 VTP。纯手工操作时间未测；替代模板重封装时间单列于对比 JSON。 |
| 表 3 / M3 / 算例 D | Glance HTML 200,162,242 B（200.162 MB）；vtkjs 138,040,732 B（138.041 MB）；ParaView 表面 24,222,498 B（24.222 MB）；Sim2Web 主表面 2,248,198 B（2.248 MB）、完整站点 62,766,024 B（62.766 MB） | cases/D/paraview_baseline_report.json；cases/D/scene_kitware_size.json；cases/D/build_report.json；cases/D/site_size.json | Glance HTML 使用 Kitware 官方可绘制模板。站点排除验证输出；十进制 MB。 |
| 表 3 / M4 / 算例 D | Glance 23,636.0 ms（3/3），Sim2Web 3,686.2 ms，首帧传输 5,338,425 B（5.338 MB），剖面切换 82.3 ms | cases/D/glance_split_geometry_browser.json；cases/D/sim2web_browser.json | Chrome 冷缓存回环测试。使用 Kitware 查看器与同一 vtkjs 文件分开加载的流程。模型几何提交（至少 10,000 个索引）和两次动画帧计时，坐标轴控件已排除。Sim2Web 使用查看器 firstRender。 |
| 表 3 / 开挖面手工步骤 / 算例 D | 新增 3 个处理操作 | comparison_results.json / M7 | 剔除模型六个盒面；对剩余候选面两侧采样并排除实体–实体界面；将剩余坑面单独着色并导出。 算例 A/D 的追加处理见 cases/D/paraview_excavation_extras.json。 |
| 结果 §4 / 主应力 / D / 最小 | 1.405813 MPa（13.7056%） | cases/D/paraview_principal.json | 百分比分母为正确主应力全色标跨度。 |
| 结果 §4 / 主应力 / D / 中间 | 3.152970 MPa（75.8984%） | cases/D/paraview_principal.json | 百分比分母为正确主应力全色标跨度。 |
| 结果 §4 / 主应力 / D / 最大 | 1.762586 MPa（22.1703%） | cases/D/paraview_principal.json | 百分比分母为正确主应力全色标跨度。 |
| 结果 §4 / 算例 D / 仅通用结果受拉 | 3808 个 / 548417 个保留单元 | cases/D/paraview_principal.json | 最大主应力仅在通用结果中大于 0。 |
| 结果 §4 / 主应力 / F / 最小 | 21.711403 MPa（4.7954%） | cases/F/paraview_principal.json | 百分比分母为正确主应力全色标跨度。 |
| 结果 §4 / 主应力 / F / 中间 | 53.164728 MPa（16.5251%） | cases/F/paraview_principal.json | 百分比分母为正确主应力全色标跨度。 |
| 结果 §4 / 主应力 / F / 最大 | 31.453324 MPa（16.4312%） | cases/F/paraview_principal.json | 百分比分母为正确主应力全色标跨度。 |
| 结果 §4 / 算例 F / 仅通用结果受拉 | 15613 个 / 393227 个保留单元 | cases/F/paraview_principal.json | 最大主应力仅在通用结果中大于 0。 |
| 结果 §4 / 算例 D / 开挖面 | 17004 面；6,418.370 m²；移除 85215 面 | cases/D/excavation_audit.json；cases/D/build_report.json | 面积在发布的 PolyData 上逐面求和。 |
| 结果 §4 / 算例 D / 坑底以下 | 面心 z < −57.5 m 为 489；名义坑底 489；其余 0；面心 z < −57.5013 m 为 0 | cases/D/excavation_audit.json | 同时提供任一、全部顶点低于平面的口径。名义坑底实际坐标约 −57.5003 m。 |
| 结果 §4 / 算例 D / 外表面 | 20293 面；2,248,198 B（2.248 MB） | cases/D/index.json；cases/D/excavation_audit.json | 记录 r3–r4 前后版本。 |
| 表 4 / 算例 A / Windows 构建 | 99.566 s | logs/034_build_A.json | 单次构建命令 wall clock；验证单独执行。测量期间机器还有并行任务。 |
| 表 4 / 算例 B / Windows 构建 | 134.089 s | logs/034_build_B.json | 单次构建命令 wall clock；验证单独执行。测量期间机器还有并行任务。 |
| 表 4 / 算例 C / Windows 构建 | 101.590 s | logs/034_build_C.json | 单次构建命令 wall clock；验证单独执行。测量期间机器还有并行任务。 |
| 表 4 / 算例 D / Windows 构建 | 144.505 s | logs/034_build_D.json | 单次构建命令 wall clock；验证单独执行。测量期间机器还有并行任务。 |
| 表 4 / 算例 D / 表面、剖面、完整包 | 主表面 20293 面，2,248,198 B（2.248 MB）；剖面 112；VTP 合计 61,202,916 B（61.203 MB）；完整站点 62,766,024 B（62.766 MB） | cases/D/index.json；cases/D/build_report.json；cases/D/site_size.json | 表 4 原有包大小的 VTP 口径与完整静态站点分别列出。 |
| 表 4 / 算例 F / Windows 构建 | 132.865 s | logs/034_build_F.json | 单次构建命令 wall clock；验证单独执行。测量期间机器还有并行任务。 |
| 表 4 / 算例 F / 表面、剖面、完整包 | 主表面 19394 面，2,352,584 B（2.353 MB）；剖面 150；VTP 合计 110,336,486 B（110.336 MB）；完整站点 111,938,065 B（111.938 MB） | cases/F/index.json；cases/F/build_report.json；cases/F/site_size.json | 表 4 原有包大小的 VTP 口径与完整静态站点分别列出。 |
| 结果 §4 / 工作台耗时 / 算例 D | 读取 10.979 s；预览 31.852 s；构建 114.489 s；验证 26.861 s；最慢请求 1.119 s | workbench/D/workbench_timing.json | 验证每 5 个剖面抽 1 个。 |
| 结果 §4 / 工作台耗时 / 算例 F | 读取 5.169 s；预览 17.980 s；构建 115.441 s；验证 61.798 s；最慢请求 0.921 s | workbench/F/workbench_timing.json | 验证每 5 个剖面抽 1 个。 |
| 例 H / MOOSE 自动转换 | 默认 t=2；--time first 得 t=0；应力最大绝对差 0.000000；位移最大绝对差 0.000000 | cases/H/r3_r4_difference.json；logs/043_moose_last.log；logs/044_moose_first.log | 按坐标和单元连通性对齐；将 ZX 与 XZ 视为同一分量。 |
| 算例 D / 查看器图 | 1600×900 | cases/D/viewer_1600x900.png | 使用仓库 benchmark/screenshots.mjs。 |
| 算例 F / 查看器图 | 1600×900 | cases/F/viewer_p5_p95_1600x900.png | 使用仓库 benchmark/screenshots.mjs。 |
| 参考文献 [15] | 作者、年份、刊物、DOI/网页及访问日期见核对表 | REFERENCES.md；references_crossref.json | [17] 包含官方源码分量顺序原文。[22] 区分原论文和 3.0 更新。 |
| 参考文献 [16] | 作者、年份、刊物、DOI/网页及访问日期见核对表 | REFERENCES.md；references_crossref.json | [17] 包含官方源码分量顺序原文。[22] 区分原论文和 3.0 更新。 |
| 参考文献 [17] | 作者、年份、刊物、DOI/网页及访问日期见核对表 | REFERENCES.md；references_crossref.json | [17] 包含官方源码分量顺序原文。[22] 区分原论文和 3.0 更新。 |
| 参考文献 [20] | 作者、年份、刊物、DOI/网页及访问日期见核对表 | REFERENCES.md；references_crossref.json | [17] 包含官方源码分量顺序原文。[22] 区分原论文和 3.0 更新。 |
| 参考文献 [22] | 作者、年份、刊物、DOI/网页及访问日期见核对表 | REFERENCES.md；references_crossref.json | [17] 包含官方源码分量顺序原文。[22] 区分原论文和 3.0 更新。 |
| 应用与反馈 | 待补 | manuscript_highlights.json | 稿件未附实际项目清单、人数、反馈原文或可核验出处。 |
| 代码发布 / C2、C4 / Zenodo DOI | 待补 | manuscript_highlights.json | 本次核验开发提交 722176f。正式发布、托管名称、正式引用提交及 DOI 待稿件作者提供。 |
| 数据可用性 / 算例 F 数据权属 | 待补 | manuscript_highlights.json | 本地数据用于授权验证，权属和可公开许可待作者确认。 |
| 声明格式 / SoftwareX | 待补 | manuscript_highlights.json | Elsevier 通用作者政策要求如使用生成式 AI 准备稿件，在参考文献前设独立声明。SoftwareX 本刊指南页面返回 403，投稿端具体字段及事实仍待作者确认。见 REFERENCES.md。 |
