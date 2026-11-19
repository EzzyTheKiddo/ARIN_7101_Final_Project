# M1–M3 接入自检（试用）

在仓库根目录、已安装 requirements.txt 的 Python 环境执行：

```powershell
python scripts/test_member_handoff.py --member m1
python scripts/test_member_handoff.py --member m2
python scripts/test_member_handoff.py --member m3
python scripts/test_member_handoff.py --member all --verbose
python scripts/test_member_handoff.py --member m3 --notebook path/to/your_notebook.ipynb
```

PASS 仅表示小型接口案例通过；NOT_READY 表示调用遇到 NotImplementedError；FAIL 表示接口、依赖、加载或断言失败。退出码：0 全部通过，1 至少一项失败，2 无失败但有未实现。all 模式会继续检查其他成员。--verbose 打印失败堆栈。

## 检查范围
- M1：8 题、stable/abrupt、小型固定 fixture seed；重复生成一致、ID 连续、切换边界、公开前缀、未来隔离、证据位置；调用 audit_truth 检查可调用性，但不把任意返回值认定为审计通过。
- M2：自建两条历史，不依赖 M1；四臂上下文预算/顺序/来源、不修改输入、规则回答、空上下文 UNKNOWN、四臂表及效用公式。
- M3：自建 12 题四臂表，不依赖 M1/M2；三维 its 特征、七种方法回放、重复运行一致、固定臂、元数据、所选结果匹配，以及翻转未选奖励不改变回放。

## 加载约定与限制
使用 shared-protocol-draft 和所选成员 m1-/m2-/m3- 代码单元。为跳过安装、展示、导出与正式执行入口，加载器仅执行顶层 import、函数/类定义和赋值，不执行顶层 if/for/表达式。函数内逻辑保持原样。常量和依赖应在这些声明中准备；依赖被跳过的条件初始化时，会报 FAIL，需要调整为可独立加载的定义区。
这不是完整 Notebook 执行，也不是安全沙箱：赋值右侧、导入、装饰器和函数本身仍可执行代码，只对可信团队 Notebook 使用。脚本本身不安装依赖、不导出文件、不创建 run、不写审查表。当前主工作本测试中未调用正式入口；若成员将文件写入放进声明或被测函数，应先检查其副作用。
独立的 M3_presentation.ipynb 尚不满足统一 cell ID 和接口约定；应接入主工作本后运行，不能用临时适配掩盖接口不一致。

## 如何处理结果
修复 FAIL 时提供命令、cell/函数、错误和最小输入。NOT_READY 可以用于开发阶段定位待补接口，不应转换成 PASS。接入后继续执行本人完整测试和真实开发数据联调。
本脚本不覆盖导出/哈希、十题人工签收、M1 真值审计返回语义、M3 梯度/Hessian/第五次重拟合数值核查、完整正式规模或研究结论；不能代替接收人验收。

2026-11-19 实测当前主工作本：M1 PASS，M2 PASS，M3 NOT_READY（question_features 未实现）。所有数据是内存 fixture，seed 910001–910003 为测试用途，应避免作为未来正式 seed 使用。
