# 稿件参考文献核对

访问日期均为 2026-11-21（日本时间）。期刊、卷期、页码和 DOI 缺失的博客、技术文档按网页文献著录。SoftwareX 两条原始期刊记录均有文章号，Crossref 无期号。

| 稿件位置 | 作者、年份、刊物和定位 | 原始出处 |
|---|---|---|
| [15] trame | Sebastien Jourdain、Patrick O’Leary、Will Schroeder，2022-09-23，*Trame: Visual Analytics Everywhere*，Kitware 技术博客。卷、期、页码和 DOI 不适用。 | [Kitware 原文](https://www.kitware.com/trame-visual-analytics-everywhere/) |
| [16] ParaView Glance | Sebastien Jourdain、Cory Quammen，2019-09-25，*Exporting ParaView scenes to ParaView Glance*，Kitware 技术博客。卷、期、页码和 DOI 不适用。 | [Kitware 原文](https://www.kitware.com/exporting-paraview-scenes-to-paraview-glance/) |
| [17] VTK | VTK Project，VTK 9.5 官方开发者文档（类页面未列个人作者或网页出版年份，9.5.0 版本发布于 2025-06-24），*vtkTensorPrincipalInvariants Class Reference*。卷、期、页码和 DOI 不适用。按版本 9.5.0 源码确认张量分量顺序。 | [类文档](https://vtk.org/doc/nightly/release/9.5/html/classvtkTensorPrincipalInvariants.html) · [9.5.0 发布说明](https://www.kitware.com/vtk-9-5-0/) · [过滤器源码](https://github.com/Kitware/VTK/blob/v9.5.0/Filters/Tensor/vtkTensorPrincipalInvariants.cxx#L236-L256) |
| [20] GEOMODELATOR-GUI | Thomas Kempka、Benjamin Nakaten、Elena Chabab，2026，*GEOMODELATOR-GUI: A web-based graphical user interface for 3D geological modelling*，*SoftwareX*，34，102630，DOI 10.1016/j.softx.2026.102630。 | [期刊 DOI](https://doi.org/10.1016/j.softx.2026.102630) · [Crossref 出版商存档](https://api.crossref.org/works/10.1016/j.softx.2026.102630) |
| [22] MOOSE | Cody J. Permann、Derek R. Gaston、David Andrš、Robert W. Carlsen、Fande Kong、Alexander D. Lindsay、Jason M. Miller、John W. Peterson、Andrew E. Slaughter、Roy H. Stogner、Richard C. Martineau，2020，*MOOSE: Enabling massively parallel multiphysics simulation*，*SoftwareX*，11，100430，DOI 10.1016/j.softx.2020.100430。 | [期刊 DOI](https://doi.org/10.1016/j.softx.2020.100430) · [Crossref 出版商存档](https://api.crossref.org/works/10.1016/j.softx.2020.100430) |

[17] 类参考页说明 `Sigma1` 至 `Sigma3` 的次序。过滤器源码对三维数组直接使用六个索引，源码注释写明 “6 components (3D) -> XX, YY, ZZ, XY, YZ, XZ”。VTK 9.5 的 `vtkMath::TensorFromSymmetricTensor` 官方参考页也明写 “Symmetric tensor is expected to have the following order : XX, YY, ZZ, XY, YZ, XZ”。[过滤器源码](https://github.com/Kitware/VTK/blob/v9.5.0/Filters/Tensor/vtkTensorPrincipalInvariants.cxx#L236-L256) · [vtkMath 参考页](https://vtk.org/doc/nightly/release/9.5/html/classvtkMath.html)

[22] 稿件若沿用题名末尾复数 `simulations`，对应的是 Giudicelli 等 36 位作者的 2024 更新论文，题名带 `3.0 - MOOSE`，*SoftwareX* 26，101690，DOI 10.1016/j.softx.2024.101690。表中著录的是 2020 原论文。 [2024 期刊 DOI](https://doi.org/10.1016/j.softx.2024.101690) · [完整作者](https://api.crossref.org/works/10.1016/j.softx.2024.101690)

SoftwareX 声明格式待核对项。Elsevier 通用作者政策要求，如在稿件准备中使用生成式 AI，在参考文献前加入独立声明章节。SoftwareX 单刊指南网页本次返回 HTTP 403，未核实其投稿系统额外字段。稿件的使用情况及责任说明需由作者确认。访问日期 2026-11-21。[Elsevier 作者政策](https://www.elsevier.com/en-gb/about/policies-and-standards/generative-ai-policies-for-journals) · [SoftwareX 投稿指南](https://www.sciencedirect.com/journal/softwarex/publish/guide-for-authors)

