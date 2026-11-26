# 项目进度报告｜2026 年 11 月 26 日

**项目已跑通小规模端到端 demo，正式实验尚未启动。** 当前阻塞集中在三件事上：M1/M2 完成十题联合判定，M3/M4 核验开发证据和对话级统计，全组批准待冻结的配置与种子。M5 现在就可以用 demo 开发读档和制图功能。[团队进度板](./team_workspace/team_progress.csv) · [正式运行登记](./team_workspace/formal_runs.json)

本报告以主线 `b96cdf3` 为准。11 月 23 日后，M4 的调度、冻结、正式尝试登记及归档代码已合入，M1 的逐题追踪记录也已交付。导出器增加了对四臂评价、回放和对话指标完整性的检查。[M4 合并记录](https://github.com/Space-ash/ARIN_7101_Final_Project/pull/5) · [M1 合并记录](https://github.com/Space-ash/ARIN_7101_Final_Project/pull/6) · [导出校验修订](https://github.com/Space-ash/ARIN_7101_Final_Project/commit/e995a30)

## M1–M5 进度与下一步

| 成员与状态 | 已完成及验证依据 | 下一步与交付对象 |
|---|---|---|
| **M1 · 待复核** | 两个场景的生成器和独立真值核查已接入主本。十题均已从公开对话前缀追踪目标、答案、最新证据和旧值，逐题意见已填入协作表。[逐题记录](./deliverables/M1_review_20261123.md) | 本人确认十条意见，与 M2 逐题给出联合判定。向 M2/M4 提供原始开发包，或标明重新生成的版本、种子与真值核查结果，记录接收情况。 |
| **M2 · 待复核** | 六条开发对话共 1,800 题、7,200 行四臂评价可回读，40 条抽查策略记录可重建。已比较 8、9、12 个检索候选；增加候选可找回部分证据，也会增加输入成本，开发默认值保留 8。[开发与交接记录](./deliverables/M2_notes.md) | 与 M1 在同一份协作表关闭十题；有分歧的题保留原因和复核结果。与 M3 确认回放输入，与 M4 确认全表来源、候选数决定及对应版本。[协作审查表](./team_workspace/m2_handoff/audit_review.csv) · [接口决策](./team_workspace/interface_decisions.md) |
| **M3 · 待复核** | 四个固定臂、TS、LaplaceCTS 和 RuleRouter 已接入回放。开发对话 `abrupt/130100` 用两个算法种子生成 4,200 行回放，已核对选中臂反馈、重置和后验数值；M4 的 demo 已能调用七种方法。[方法与验证记录](./deliverables/M3_notes.md) | 向 M4 交付与最终开发表、配置和工作本对应的 `method_checks`。冻结前复算对话级聚合与配对区间，确认独立样本数按对话计；正式运行后复核同一归档中的主、次效应表。 |
| **M4 · 进行中** | 开发基准已产出。小规模 demo 已从生成、四臂评价、七方法回放跑到统计归档。冻结、登记及失败留档已有实现，10 项协议测试通过。[开发证据](./deliverables/M4_development_evidence.json) · [运行记录](./deliverables/M4_notes.md) | 先把完整 demo 交 M3/M5 独立回读。收齐审查表和上游证据，核对哈希、开发基线及已用种子，取得全组批准后冻结。按冻结计划登记正式尝试，保留失败记录，向 M3/M5 交付同一份 manifest 和结果表。[正式流程](./docs/M4_FORMAL_WORKFLOW.md) |
| **M5 · 待实现** | 主本已定义读取、制图和导出接口，三个函数仍为占位。提交清单中的 slides、视频链接及全组签收仍待填写。[主工作本](./ARIN7101_Context_Bandit_Release_Notebook.ipynb) · [提交清单](./deliverables/SUBMISSION_CHECKLIST.md) | 先用 demo 实现独立读取，校验文件哈希、表键和样本数，并用缺文件或改表验证能发现错误。为每张图导出对应数据表；取得 formal 归档后完成逐图解释、slides 和视频，交全组核对。 |

## 已验证的范围

| 范围 | 截至 11 月 26 日的证据 |
|---|---|
| 十题审查 | 本次回读协作表，十题均有双方复核人字段和书面意见；十个联合判定仍为 `pending`。 |
| 小规模 demo | 本次回读本地 `outputs/demo/review_20261126_verified`，manifest 中 15 个文件的 SHA-256 全部匹配。两个场景各 2 条对话，每条 20 题；实有 320 行四臂评价、1,120 行回放、28 行对话指标，主、次效应表各 2 行。归档状态为 `demo_complete_pending_review`。 |
| 完整 demo | M4 记录为两个场景各 6 条对话、每条 300 题，共 14,400 行四臂评价和 50,400 行回放。当前工作区只有小规模 demo，完整包仍待接收并逐文件核验。 |
| 正式实验 | 正式登记为 `[]`。当前开发数据选出的固定基线是 stable 场景的 `recent_short` 和 abrupt 场景的 `resolved_tfidf`；正式比较须以全组冻结的版本和独立对话为准。 |

## 后续交付顺序

1. **冻结前并行。** M1/M2 完成十题判定和数据交接；M3/M4 用完整 demo 对账并整理冻结证据；M5 用现有小规模归档验证读取器，准备图表。
2. **批准后正式运行。** M4 按当前协议为每个场景安排 30 条独立对话、每条 300 题，共 18,000 题、72,000 行四臂评价。实际规模、基线和种子以冻结配置为准；每次尝试均登记。[正式流程](./docs/M4_FORMAL_WORKFLOW.md)
3. **归档后提交。** M3 复核对话级效应与区间，M5 从同一归档生成图表并核对图表数据。全组复核讲稿、slides、视频访问权限、引用和个人贡献后填写提交清单。[输出契约](./docs/OUTPUT_CONTRACT.md) · [提交清单](./deliverables/SUBMISSION_CHECKLIST.md)

11 月 23 日审查时的详细记录可从 Git 历史查阅。[原报告及历史快照](https://github.com/Space-ash/ARIN_7101_Final_Project/blob/b96cdf3/project_progress_11.23.md)
