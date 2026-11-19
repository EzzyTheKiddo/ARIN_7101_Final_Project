# M3 研究、实现与交接记录

阶段：开发验证完成，待M4复核。开发验证使用一个abrupt对话。

## 1. Beta手算

每臂先验为 Beta(1,1)。所选臂的结果为 1、1、0 时，更新为 Beta(3,2)，均值为 0.6。选择时比较后验抽样成功率减去成本惩罚，更新时只用正确性。

## 2. MAP、梯度、Hessian与Laplace

令 X 为一臂所选问题的特征矩阵，y 为其反馈，z=Xw，p=sigmoid(z)，τ 为高斯先验精度。负对数后验为 `sum(logaddexp(0,z)) - yᵀz + τwᵀw/2`，梯度为 `Xᵀ(p-y) + τw`，Hessian 为 `Xᵀdiag(p(1-p))X + τI`。对MAP处的解析Hessian解线性方程得到近似协方差。每臂每收到5条已选反馈才重拟合，间隔内继续使用上次后验。拟合返回非有限量或梯度范数超过 0.001 时中止并报告对应臂。

## 3. 学习器与回放

保留M3展示本及[完整参考本](../reference/ARIN7101_Context_Bandit_Release_v1_Complete_Reference.ipynb)的逐臂Beta更新、logistic Laplace和规则路由思路。集成时改为显式配置、独立初始化、词边界特征、用于拟合和有限差分的共用目标函数及Hessian、单对话输入校验。CTS使用截距、显式项目ID与独立词 its。评估器保存四臂结果，选择器每轮接收问题和按ARMS排序的成本；随后收到所选臂的正确性。

## 4. 开发验证

- PR #3 的 M3 接口 smoke test 通过。
- 使用 M2 分支提交 `21ab47f77a73f6113950a7fa90a874f9c370f23c` 中的 `team_workspace/m2_handoff/m3_handoff_abrupt_130100.csv`。1,200 条四臂行产生 4,200 条回放行（300题 × 7方法 × 2算法seed）。选中行的正确性、成本、效用、coverage和outdated与M2表匹配。
- 打乱输入顺序、固定seed重新回放，以及翻转全部未选臂奖励均保持回放不变。验证了第五次反馈前后的后验、未选臂和独立初始化。
- MAP梯度范数约 7.37e-7，有限差分梯度与Hessian最大误差分别约 5.04e-11 和 1.89e-11，协方差最小特征值约 0.384。

## 5. M4接口验收与后续统计复核

M4调用 `replay_episode(arm_outcomes, method, algorithm_seed, cfg)`。运行第0节、共同协议和M3代码单元后，调用 `export_m3_development(handoff_path, run_id, PROTOCOL_DRAFT)`，在开发run内生成 `audit/method_checks.json` 和 `tables/development_replay.csv`。本次run为 `m3_abrupt_130100`。正式统计复核等待M4提供结果。

## 6. 局限与贡献记录

Laplace后验是近似，有限频率拟合有滞后。模板特征和一个开发对话的验证范围有限。代码集成、数值检查和本记录初稿有AI辅助；成员应补充本人验证、设计与贡献。
