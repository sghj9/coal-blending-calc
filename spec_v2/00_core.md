# 00 — 产品核心行为（唯一真相）

> 文档版本：v2.0
> 最后更新：2026-06-16
> 关联代码文件：`index.html`、`js/main.js`、`js/ui.js`、`js/validation.js`、`js/optimizer.js`、`js/storage.js`、`css/style.css`、`data/defaultCoals.json`
> 原始文件（保留）：`coal_blending_calc.html`、`spec/frontend_spec.md`

## 一、项目结构

```
coal_blending_calc/
├── index.html                 # 主页面（结构骨架 + 外部引用）
├── css/
│   └── style.css              # 所有样式（从原 HTML <style> 块提取）
├── js/
│   ├── main.js                # 全局状态、核心计算、初始化入口
│   ├── ui.js                  # DOM 渲染与交互（表格、结果卡片、目标输入框）
│   ├── validation.js          # 完整性校验与确认对话框
│   ├── optimizer.js           # 配比优化求解器（单纯形法 + 分支定界）
│   └── storage.js             # 未来扩展占位（localStorage / IndexedDB）
├── data/
│   └── defaultCoals.json      # 默认煤种数据（JSON 格式镜像，运行时不使用）
├── spec/
│   └── frontend_spec.md       # 原始规格文档（保留，不修改）
├── spec_v2/
│   ├── 00_core.md             # 本文档 — 产品核心行为（唯一真相）
│   ├── 01_ui_behavior.md      # UI 交互规则
│   ├── 02_calculation.md      # 计算逻辑（公式级）
│   ├── 03_optimizer.md        # 优化算法（独立）
│   ├── 90_experiments.md      # 实验性设计
│   ├── 99_archived.md         # 废弃内容
│   └── README.md              # 目录索引
├── tests/
│   ├── helpers.py                     # 测试辅助模块（JS 拼接、mock 注入、Node.js 执行）
│   ├── unit/                          # 单元测试（纯逻辑，单函数）
│   │   ├── test_calculation.py        # 核心计算测试
│   │   ├── test_data.py               # 初始数据测试
│   │   ├── test_status.py             # 达标判定与目标范围测试
│   │   └── test_optimizer.py          # 单纯形法求解器测试
│   ├── integration/                   # 集成测试（需 DOM mock，多模块协作）
│   │   ├── test_ui_flow.py            # UI 交互流程测试
│   │   └── test_optimizer_e2e.py      # 优化器端到端测试
│   └── regression/                    # 回归测试（关键现状行为锁）
│       └── test_current_behavior.py   # 受控的现状行为测试
├── assets/icons/              # 预留
├── coal_blending_calc.html    # 原始单文件（保留，未删除）
├── CLAUDE.md                  # Agent 规则
├── pyproject.toml              # 项目元数据与 Python 依赖（pytest）
├── .gitignore
└── README.md
```

### 1.1 模块职责

| 文件 | 包含函数 / 内容 | 职责 |
|------|----------------|------|
| `js/main.js` | `DEFAULT_COALS`、`coals`、`targetBounds`、`getDefaultCoals()`、`initCoals()`、`calculateHybridMetrics()`、`checkStatus()`、`bindEvents()`、`init()` | 全局状态定义、核心计算逻辑、事件绑定、初始化入口 |
| `js/ui.js` | `createNumberInput()`、`renderTable()`、`updateTotalRatioDisplay()`、`updateResultUI()`、`fetchTargetBoundsFromInputs()`、`refreshAndNotify()`、`renderTargetInputs()`、`syncCoalsFromTable()`、`addCoalManually()`、`renderOptimizeResult()`、`applyOptimizeRatios()` | DOM 创建与渲染、用户交互流程（表格、结果卡片、目标输入框、添加煤种弹窗、优化结果展示） |
| `js/validation.js` | `checkCoalTableCompleteness()`、`confirmAndRefresh()`、`checkTargetCompleteness()` | 表单完整性校验、确认对话框逻辑 |
| `js/optimizer.js` | `simplex()`、`_runSimplexPhase()`、`_pivot()`、`optimizeBlending()` | 两阶段单纯形法求解器、配比优化接口 |
| `js/storage.js` | （空，仅注释） | 预留 localStorage / IndexedDB 扩展点 |
| `css/style.css` | 全部 CSS 规则（从原 HTML `<style>` 块提取，原样保留） | 页面样式、响应式布局 |
| `data/defaultCoal.json` | 4 条默认煤种数据（JSON 数组） | 数据镜像文件，供独立查看/编辑；运行时使用 `main.js` 中的 `DEFAULT_COALS` 常量 |

### 1.2 脚本加载顺序

`index.html` 中 `<script>` 标签按以下顺序加载：

```html
<script src="js/main.js"></script>       <!-- ① 全局变量 + 核心函数先定义 -->
<script src="js/ui.js"></script>          <!-- ② UI 函数引用 main.js 中的全局，运行时调用 -->
<script src="js/validation.js"></script>  <!-- ③ 校验函数独立 -->
<script src="js/storage.js"></script>     <!-- ④ 空占位 -->
<script>init();</script>                  <!-- ⑤ 所有脚本加载完成后触发初始化 -->
```

此顺序保证：
- `coals`、`targetBounds`、`calculateHybridMetrics()`、`checkStatus()` 等全局状态/函数在 ui.js 执行前已定义
- 跨文件函数调用（如 `bindEvents()` 调用 `addCoalManually()`、`confirmAndRefresh()`）仅在事件触发时发生，此时所有脚本已加载完毕

## 二、一句话目标

配煤人员手动输入多种煤的指标（灰分、硫分、挥发分、粘结）和配比（成），自动计算混合煤指标并与钢厂目标范围比对，判断达标情况。所有计算需用户点击确认按钮触发，不自动计算。

## 三、数据模型

| 字段 | 类型 | 约束（必填？范围？默认？）|
|---|---|---|
| 煤种名称 | string | 必填，不能为空 |
| 煤价 | number | ≥0，默认0 |
| 灰分 | number | ≥0，默认0 |
| 硫分 | number | ≥0，默认0 |
| 挥发分 | number | ≥0，默认0 |
| 粘结 | number | ≥0，默认0 |
| 配比（成） | number | ≥0，默认0，1成=10% |
| 是否调料煤 | boolean（派生） | 只读，不持久化；由煤种名称精确匹配调料煤清单得出，仅用于优化器约束与表格显示 |
| 目标范围（每项 min/max） | number | 可空，空值按0处理 |

## 四、端点 / 接口

（无后端，纯前端交互）

| 动作 | 输入 | 成功返回 | 失败情况 |
|---|---|---|---|
| 添加煤种 | 弹窗依次输入7个字段 | 表格新增一行，提示"请点击确认按钮更新" | 输入无效（非数字/取消）→ 不添加 |
| 删除煤种 | 点击某行🗑️ | 删除该行，提示"请点击确认按钮更新" | 只剩一行时禁止删除并提示 |
| 确认指标和配比 | 读取当前表格所有行 | 计算混合指标、更新达标状态、提示成功 | 存在空值时弹窗询问是否继续（空值→0） |
| 确认目标范围 | 读取四个指标的上下限 | 更新达标状态、提示成功 | 上下限颠倒时弹窗交换并确认；空值弹窗询问（空值→0） |

## 五、边界

- 煤种数量：1种 ~ 不限（删除时至少保留1种）
- 配比总和：可全0 → 混合指标全0；> 10成时弹窗警告"当前总配比X成，超过十成，请重新配比"，不计算混合指标不更新结果
- 目标范围：下限 > 上限 → 弹窗交换，用户确认后才应用
- 空值处理：用户确认继续后，缺失数值自动当作0
- 确认计算：用户修改任意表格数值或目标范围输入框、添加新煤种、删除煤种后，不自动计算，用户点击确认按钮才会进行计算

## 六、明确不做

- 界面及弹窗中不出现英文说明，都用中文
