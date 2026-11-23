# M4 正式运行管理（待团队验收）

## 分工与参数候选
M2/M3 的模块正确性测试由本人负责。M4 负责同输入、同种子、同评价口径的实验编排与对话级比较，不代写算法、不代签审查。

| 模块 | 已有候选/默认 | 责任与状态 |
|---|---|---|
| M1 | 近期题概率、更新/初始冲突比例等默认配置 | M1解释机制；当前无确认的候选网格 |
| M2 | 检索候选数8/9/12 | M2提出；需由M2使策略参数可配置并验证，再交M4统一比较 |
| M3 | prior_precision=1、refit_every=5，算法seed 17/37 | 默认，不代表已选定多个实验组合；候选由M3提出并解释 |
| M4 | λ=0.25/0.5/1.0；bootstrap 2000/10000 | 探索建议未执行未冻结。λ改变行为需重放；bootstrap只改变统计计算精度 |

不必穷举参数笛卡尔积。优先验证具体问题，例如M2的候选截断；固定其他条件比较8/9/12，报告每条对话及各场景的效用、准确率、成本、旧值率。若发现参数间交互再做小规模联合比较。全部选择使用开发数据；正式结果只评价冻结方案。M5可先用demo做排版，不必等待所有参数探索结束。

## 输入准备
scripts/run_m4_formal.py 提供 freeze/run 两个命令，当前只支持每场景30条、每条300题设计。

plan.json 是完整计划对象，字段包括：
- config：完整 PROTOCOL_DRAFT 配置（lambda、cost_reference、algorithm_seeds、bootstrap等）。
- baselines：stable/abrupt各自开发固定臂。
- evaluation_seeds：stable/abrupt各30个不重复整数。
- used_seeds：全组披露的所有已用对话seed，除代码内已知禁用范围外也要登记。

evidence.json 是证据名到路径的映射，路径相对此文件：audit_review、truth_checks、strategy_checks、method_checks、development_outcomes、approvals。需提供真实产物，不用占位空对象。

approvals 文件需包含：plan_sha256（m4_protocol.canonical_hash(plan)）、code_sha256（notebook/runner/protocol/loader实际文件SHA256）、evidence_sha256（除approvals自身外所有证据SHA256）；members对象的M1–M5各有name/date/approved；另有m3_statistics_reviewed和all_used_seeds_disclosed两个真实确认值。程序不会生成签名。批准记录是人工声明，不是数字签名系统，仍需团队审查真实性。

代码绑定文件：根工作本、scripts/run_m4_formal.py、scripts/m4_protocol.py、scripts/test_member_handoff.py。配置、代码或审计证据变化后旧批准失效。

```powershell
python scripts/run_m4_formal.py freeze --plan plan.json --evidence evidence.json --destination outputs/frozen/approved_v1
python scripts/run_m4_formal.py run --frozen outputs/frozen/approved_v1 --run-id formal_unique_id
```

freeze复制证据和源码并拒绝覆盖。run再次核对批准、快照与当前代码；从批准的开发全臂表复算基线；检查开发/正式seed分离。在生成任何正式对话前向team_workspace/formal_runs.json追加started事件，然后运行60条对话。完成状态为computed_pending_review，仍待M3/M5验收，不自动标complete。

失败追加failed事件，保留已使用seed和目录；重复run ID或已尝试seed会被拒绝。注册采用锁文件和原子替换，异常进程退出留下的锁/.new文件须人工调查，不自动删除或覆盖。不得并行启动共享同一登记文件的正式任务。冻结后不能依据已看结果调参并伪称原主检验。

## 验证与限制
python scripts/test_m4_protocol.py 在临时目录使用明确的SYNTHETIC签名测试，绝不写实际审查表；覆盖绑定、篡改、重用seed、重复run、未签审查和失败历史保留。当前仅有生命周期组件测试和先前demo计算链验证，尚未执行真人批准的完整正式运行。上游证据由批准者确认含义，不能只靠文件哈希推断研究通过。

当前没有真实审批文件，formal_runs.json保持原状态。正式数据不可在团队确认前生成。

## 追加：候选数开发探索入口

```powershell
python scripts/explore_m4_candidates.py --run-id your_unique_candidate_run
```

该脚本在内存中对M2的select_context只替换head(8)为head(k)，不修改M2工作本；若源代码不再精确匹配，则停止要求重新审核。比较同时应用于两个检索臂，k=8/9/12，预算保持256，focus锚点和打包规则不变。方法回放使用相同算法seed，但行为分叉后的随机过程不保证逐次抽样完全对齐。
先验证k=8与默认基准一致，且固定短/长窗不受变体影响，再比较同一方法相对k=8的对话级效用、正确率、成本与旧值变化。保存三个变体的全部四臂与回放结果，不只保留最佳者。不把适配器变成正式协议；若选定新候选数，应请M2正式参数化并独立测试，再冻结。
