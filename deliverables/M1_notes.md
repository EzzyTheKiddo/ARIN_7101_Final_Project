# M1 研究、实现与交接记录

姓名：刘卓扬

阶段：待复核（实现、development 数据及十题证据复核已完成；本人确认、M1/M2 联合判定和 M2/M4 接收未完成）

说明：本轮代码、测试和记录由 Codex 按项目负责人的授权协助完成。成员本人仍需阅读实现、复跑检查、确认研究选择，并如实说明 AI 辅助范围后再署名。

## 1. 数据机制选择与理由

- 沿用共同设计：每条 episode 有 6 个项目、4 种属性、300 道题；`stable` 的近期题概率为 0.9；`abrupt` 在 `t=150` 从 0.9 切换到 0.1；每轮事实更新概率为 0.25；初始项目-属性组合以 0.25 概率包含两个不同版本。
- 每轮按 focus、事实、短干扰的顺序追加消息，再生成问题。近期题用 `its` 指向 focus；历史题明确写出非 focus 项目名。事实中使用 `dataset/data source`、`language/coding language`、`metric/evaluation measure`、`deadline/due date` 表达。
- 使用 episode 局部 NumPy RNG；事实值由 seed 和 episode 内序号构造。更新产生新值，复述保持值不变。`evidence` 始终指向截至当前题最后一次陈述，因此复述也会改变 evidence ID；`old_values` 保存此前不同的值。
- 参数是生成概率，不强制有限样本比例等于设定概率。这个选择保留了抽样波动，也避免通过配额让每段对话看起来过于整齐。

## 2. 生成/公开视图/独立核查的实现

- 在 notebook `m1-generation-skeleton` 实现 `generate_episode`、`public_view`、`audit_truth` 和 `export_development_data`。`public_view` 仅返回 `question/history`，历史严格截断为 `history[:end]`。
- `audit_truth` 逐题重新解析公开文本中的 focus、事实、属性同义表达和显式项目名，再重建当前值、证据 ID 和旧值。审计不以 episode 内保存的 `gold` 作为推导来源；保存值只用于最后比对。
- 输出字段说明、可见性、生成机制和统计单位写入 `audit/data_dictionary.json`；逐题核查记录写入 `audit/truth_checks.json`；按场景和状态汇总问题、旧值、历史长度、证据距离、更新和 alias 使用情况写入 `tables/development_data_profile.csv`。
- M1 测试区提供临时 fixture 导出检查。独立运行开发导出时，在共享路径单元设置新的 development `RUN_ID`，然后将 `M1_EXPORT_DEVELOPMENT` 改为 `True`；默认 `local_setup` 不会导出研究数据。

## 3. 自己设计的测试与失败案例

在 Python 3.12 环境执行 M1 单元后，以下检查通过：

- 相同 seed/配置完全复现；不同 seed 得到不同 episode；message ID 与 `t` 从 0 连续。
- `abrupt` 在小型 `T=8` fixture 的 `t=4` 切换；正式 `T=300` 的边界为 `t=150`。`stable` 始终为 A。
- 变更当前题之后的未来消息不改变 `public_view`；返回对象不含评估器字段。
- fixture 覆盖 `its`、显式项目名、属性别名、版本更新，以及同值复述后 evidence 前移。
- 故意篡改 fixture 的 `gold`、旧 `evidence`、未来 `evidence` 和 `old_values` 后，审计器能报告不一致或时间越界。
- fixture JSONL gzip 导出后可读回；重复导出被拒绝；fixture 使用临时目录，不混入 development 数据。

这些是围绕接口性质编写的自动检查，不替代 M1 成员本人解释代码，也不证明上下文策略或研究假设正确。测试来源为 notebook `m1-checks-workspace`。

## 4. 开发诊断与10题审查

运行 `outputs/development/m1_development_20261109`，共 6 条 episode、1,800 道题；独立真值审计覆盖全部 1,800 题并通过。观测比例是本次抽样结果，不是硬编码目标：

| scenario/state | questions | recent fraction | historical fraction | has-old-value fraction | mean evidence lag (messages) |
|---|---:|---:|---:|---:|---:|
| stable/A | 900 | 0.890 | 0.110 | 0.771 | 7.197 |
| abrupt/A | 450 | 0.893 | 0.107 | 0.649 | 8.691 |
| abrupt/B | 450 | 0.102 | 0.898 | 0.898 | 72.362 |

所有汇总组覆盖 6 个目标项目和 4 种属性。abrupt 后半段历史题比例及其旧值暴露较高，且平均 evidence 距离增加；这些是数据机制诊断，不能据此推断哪种策略会胜出。

2026-11-23 已取得 `team_workspace/m2_handoff/audit_examples.json` 的十题材料，并从每题公开前缀逐条追踪目标、当前值、最新证据与旧值，十题真值字段均一致。四十条策略的上下文、回答、正文预算、完整成本、评分与归档行也核对一致；已知旧值回答和缺 focus 的失败案例得到复现，未发现本轮需要修改生成器或评分代码的问题。

逐题证据和评分摘要见 [M1 十题复核记录](M1_review_20261123.md)。协作表 `team_workspace/m2_handoff/audit_review.csv` 的十条 `m1_notes` 已补充，`m1_reviewer` 已填写为 `Liu Zhuoyang`，联合 `verdict` 仍为 `pending`。与 M2 逐题核对后再填写最终判定；技术检查不替代人工签收。

## 5. 证据 run 与 M2/M4 接收

- Development run：`outputs/development/m1_development_20261109/`。
- 已导出：`data/development_dialogues.jsonl.gz`、`audit/data_dictionary.json`、`audit/truth_checks.json`、`tables/development_data_profile.csv`。
- Seeds：stable `130000-130002`；abrupt `130100-130102`。开发和审计均使用 Python 3.12.0，虚拟环境解释器为 `C:\Users\86158\Desktop\project\.venv\Scripts\python.exe`。
- JSONL gzip 逐条读回后与生成的 episode 完全一致；独立审计状态为 `passed`。数据和审计文件在本地 `outputs`，该目录由 Git 忽略，团队共享时需提供完整 run。
- M1 代码已合入当前主工作本，M2 已使用同一生成器重生成开发数据。原 M1 run 在旧工作区仍可找到，当前 v2 仓库不含该 Git 忽略目录；M2/M4 对原始归档或明确标记的重生成 run 的接收仍待记录。后续应完成十题联合判定，再由 M4 确认冻结前接口和证据来源。

## 6. 局限、引用与本人贡献

- 数据是程序生成的英文模板，答案可由规则从历史恢复；不代表真实长对话、真实语言理解、LLM 行为或实际 API 成本。
- 每题即时反馈、干扰文本、版本更新和同义词覆盖均由模拟机制规定；实际分布依 seed 波动。当前 development 仅用于发现接口和数据问题，不是正式评估结果。
- 旧 reference notebook 仅作为历史背景检查接口语义；当前实现未导入或执行其完整实现。正式引用和课程材料页码需成员本人核实。
- 本轮自动化协助包括 M1 代码草拟、fixture 测试、development 导出、十题公开前缀与策略记录复核，以及本记录撰写。成员本人需阅读并确认逐题意见、复跑相关检查、理解实现并如实说明贡献；M1/M2 联合判定和 M2/M4 接收仍待完成。
