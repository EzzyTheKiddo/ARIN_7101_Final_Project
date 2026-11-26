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

evidence.json 是证据名到路径的映射，路径相对此文件：audit_review、truth_checks、strategy_checks、method_checks、development_outcomes、development_provenance、approvals。需提供这七项真实产物，不用占位空对象。

development_provenance 是 JSON 对象，包含 config_sha256（canonical_hash(plan['config'])）、notebook_sha256（实际运行工作本的文件 SHA256）和 development_sha256（开发全臂 CSV 的文件 SHA256）。必须由生成该开发结果的配置和源码填写，不能给旧结果重新贴上当前哈希。

truth_checks、strategy_checks、method_checks 使用同一信封格式：包含上述三个哈希、status="passed" 和 payload（原始检查结果）。程序检查 payload 内部结果，外层 passed 不足以通过。truth_checks 必须覆盖全部开发对话且每条300题、无错误；strategy_checks 必须包含通过的 fixture_checks、四项 development_checks 和匹配的 outcomes 行数；method_checks 必须包含 Beta 后验 [3,2]、反馈隔离检查、七种方法、匹配的算法种子/refit、开发对话来源及回放行数，且梯度范数≤1e-3、梯度/Hessian 有限差分误差≤1e-5、协方差最小特征值>0。字段名见 scripts/m4_protocol.py 的 validate_evidence。

开发 CSV 必须覆盖每场景配置数量的对话、每条完整300题×4臂；程序复算 utility = y - lambda * cost / cost_reference 和固定基线，检查缺失值、重复记录及开发/正式种子分离。人工抽查的十题必须属于该开发表。

旧版裸检查文件不能直接用于新版 freeze。应以最终配置和工作本重新生成或核验开发产物，保留原始来源后整理为上述格式，再取得团队批准；不得把失败或未运行检查包装为 passed。整个工作本哈希参与绑定，因此工作本变更后也需要重新核验。哈希绑定和内容检查不能证明文件声明真实，仍需人工审查来源。

配置在冻结前检查完整字段、类型、有限值与取值范围。批准者 name/date 必须为非空字符串，date 必须能解析为 ISO 日期或日期时间，null 不再视作有效签署。

计算失败时，failure.json 和失败登记独立尝试写入；任一写入失败会作为附注保留在原始异常上，两者都失败也不会替换计算异常。磁盘故障仍可能使持久化失败，需要人工调查 started 状态，已登记的种子继续禁止重用。

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
