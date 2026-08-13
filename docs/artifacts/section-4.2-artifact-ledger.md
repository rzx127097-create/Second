# 第4.2节产物证据台账

## 1. 成熟度与结论边界

- 当前成熟度：M1（设计契约与验收标准已冻结，正文和交付产物已生成）。
- 允许表述：建立、定义、刻画、约束、用于后续实现与验证。
- 不允许表述：算法已实现、移动补给已证明有效、SR-MAPPO显著优于对照、完成真实部署验证。
- 本节产物不包含训练日志、正式实验结果或工程参数标定结论。

## 2. 源文件到产物的追溯关系

```text
docs/design/section-4.2-design-contract.md
-> docs/thesis/section-4.2.md
-> scripts/figures/generate_section_4_2_figures.py
-> artifacts/figures/chapter4/fig4-3_heterogeneous_decision_model.*
-> scripts/documents/build_section_4_2_docx.py
-> artifacts/documents/4.2空地异构协同施药决策模型.docx
-> C:/Users/RZX/Desktop/论文/小论文/第二个问题/第二问/4.2空地异构协同施药决策模型.docx
```

正文中的式（4.9）至式（4.31）以 `docs/thesis/section-4.2.md` 为唯一可编辑源。Word构建脚本通过Pandoc将行内和陈列公式转换为原生Office Math（OMML），不把公式栅格化。图4-3由Python脚本生成，Word中嵌入PNG，仓库同时保留SVG、PDF、PNG和TIFF版本。

## 3. 本次V2修订记录

- 修正农田四邻接定义：以栅格行列索引的曼哈顿距离等于1判定拓扑邻接，再以米制中心欧氏距离定义边长。
- 修正请求状态转移接口：请求记录纳入累计实际转移量、剩余需求、可服务库存和闭合原因，并分别设置取消、未满足与重新开放守卫。
- 修正Dec-POMDP符号：使用 $\mathcal{Z}$ 表示观测函数，$\Omega$ 仅表示农田区域。
- 重排图4-3(a)的资源—生态—请求—联合到达—奖励时序；环境到下一步局部观测的执行反馈改为实线，训练阶段全局状态、价值和优化连接保留虚线。
- 增加最迟出发约束下的 `fallback_hold` 回退规则，保证动作掩码至少保留一个合法动作。

## 4. 验证记录

| 检查项 | 结果 | 证据 |
|---|---|---|
| 公式编号连续性 | 通过 | 式（4.9）至式（4.31），共23个陈列公式 |
| Word可编辑公式 | 通过 | 23个 `m:oMathPara`，不少于80个OMML对象 |
| Word图像嵌入 | 通过 | 仅嵌入图4-3一张图 |
| 可见LaTeX残留 | 通过 | DOCX结构检查及PDF文字抽取均未发现 `$$`、`\tag` 或LaTeX命令 |
| 公式符号审计 | 通过 | Markdown源稿与最终DOCX均返回 `OK` |
| 科研图结构预检 | 通过 | 20项通过，0警告，0失败 |
| PDF最小字形 | 通过 | 图4-3最小字形5.18 pt，高于5 pt下限 |
| 栅格图分辨率 | 通过 | PNG与TIFF均为600 dpi，尺寸不低于4000×2000像素 |
| Word逐页渲染 | 通过 | 共10页；公式、编号、图和题注未发现裁切或越界 |
| 两份Word一致性 | 通过 | 仓库副本与用户目录副本SHA-256一致 |

自动化结构测试命令：

```powershell
python -m pytest tests\test_section_4_2_artifacts.py -q
```

验证结果：`7 passed`。

## 5. SHA-256

| 文件 | SHA-256 |
|---|---|
| `docs/design/section-4.2-design-contract.md` | `E51E738AF950690385634A56448A07ED7C5305D357D6F60725E5CD9A33208A0F` |
| `docs/thesis/section-4.2.md` | `FE3D7FF528E2F5AF9D84B8CDC2A982430BED94C152D25F69A978F18400193F8C` |
| `scripts/figures/generate_section_4_2_figures.py` | `BBD0F9C4030299E0E4ED102C9CB67EBCAC1A3B4A8465DE5D095E9638244A70E7` |
| `scripts/documents/build_section_4_2_docx.py` | `B580971D40A284CA4737DEFA84F76909C68DDF0A801B60824BC5208CCEC3F968` |
| `fig4-3_heterogeneous_decision_model.svg` | `80C88A13C80A09D96EC845A34278F629C1DD5A30D2036604E5149EF5A6B1E56F` |
| `fig4-3_heterogeneous_decision_model.pdf` | `D05FB93663DF44580F3EF14E8DF3ADFACBF7392EFA6844DD2BE2FC3AF2C57C8D` |
| `fig4-3_heterogeneous_decision_model.png` | `49B620AD2F5C607B79C8D4CCC932DA9407AB172FDA866CB04672982F5265933A` |
| `fig4-3_heterogeneous_decision_model.tiff` | `48015F4C34E9F8D12835DF821848421D93E824200D1836253AB0ADE1A6606DD5` |
| 两份 `4.2空地异构协同施药决策模型.docx` | `81E21E9A62285B205A3CB0707AFDF3D05BF146C4E72A9EF8B7337C67A94B63E9` |

## 6. 后续门禁

进入M2前仍需完成道路拓扑、跨尺度物理位移、请求与服务状态机、药液守恒、动作掩码重放、角色梯度隔离、团队GAE和归一化冻结测试。工程参数、`K_max`、观测维数及奖励权重须在相应代码接口、参数依据和实验方案冻结后再写入后续章节，不得从本节设计稿反向杜撰。
