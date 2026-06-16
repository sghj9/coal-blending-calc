# coal_blending_calc · Agent Rules

## 命名
- 函数动词开头；布尔量用 is_/has_ 前缀

## 目录
- 规格文档放 `spec_v2/`；测试放 `tests/`，文件名 `test_*.py`
- 不在 spec 目录放测试
- **Agent 必须只遵循 `spec_v2/00_core.md`（唯一真相）+ 对应模块 spec（`01_ui_behavior.md`、`02_calculation.md`、`03_optimizer.md`）**，不得依据其他来源自行发挥行为定义

## 写代码的口味
- 先 spec、再测试、再实现；一个改动一个小提交
- 公共函数要有类型签名
- 错误要抛明确异常，不静默吞掉
- 生成的注释用中文，并使用UTF-8编码
- 你操作的环境是windows系统
- 安装Python库时，优先使用清华镜像源（`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple 包名`），并同步更新 pyproject.toml
- 如果修改某个函数的实现，先理解之前函数实现的逻辑，然后在原来的基础上，再进行修改（保留之前的函数逻辑，不要移除）
- 之前完成正确的功能，尽量不要修改。比如当前的instruction是完善功能A的，那么只需要专注功能A，不需要修改其他功能（比如功能B）

## 开发流程（必须遵循）

每一次开发必须按以下循环进行：

```
STEP 1: Update Spec   — 仅当以下情况才更新 spec：新增功能语义、修改行为定义、增加关键约束或边界条件。禁止为了代码细节频繁更新 spec。
STEP 2: Write failing unit test
STEP 3: Implement minimal code
STEP 4: Run test until pass
STEP 5: Refactor if needed
STEP 6: Commit atomic change
REPEAT
```

## Git 与变更管理
- **禁止直接 push 到 main/master**，所有修改必须在分支上进行（`feature/xxx`、`fix/xxx`、`refactor/xxx`、`update/xxx` 等）
- **禁止未说明影响范围就批量修改并提交**，每次 git 操作前必须先说明影响范围和涉及文件清单
- **一个任务 ≠ 一个 commit**（可能多个），一个 commit = 一个最小可理解变化单元，每个 commit 单一意图，message 必须表达「原因 + 改动」
- **变更必须局部化**，禁止"顺手优化"：改逻辑时不顺手重构整个文件，修 bug 时不顺手改无关代码，加功能时不顺手清理代码风格（除非用户明确要求）
- **规则优先级**（冲突时）：安全性 > 可追溯性 > 最小变更 > 性能 > 便利性
- **分支禁止直接 commit 到 main**，仅在用户明确说可以提交合并时才执行合并

## 禁止
- 不要引入未在 pyproject.toml 里的新依赖（先问）
- 不要为通过类型检查加无意义的抽象
- 不可逆操作（删数据/动钱/对外发布）必须留给人确认

## 测试

### 测试分层
| 层级 | 触发时机 | 范围 |
|------|---------|------|
| **Unit test** | 开发中每一步（STEP 2–4 循环内） | 单个函数/模块正确性 |
| **Integration test** | 功能完成后（STEP 5 重构完 → STEP 6 提交前） | 多模块协作行为 |
| **Regression test** | 上线/merge 前 | 全量已有功能不被破坏 |

- 开发中只跑相关 unit test，禁止每次跑全量
- 功能完成后补 integration test，验证端到端行为
- merge 前跑 regression test 确保无回归

### 测试纪律
- 改了行为就更新/补测试；不许把失败测试注释掉
