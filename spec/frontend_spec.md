# 配煤计算器 - 项目规格文档

> 文档版本：v1.1  
> 最后更新：2026-06-09  
> 关联代码文件：`index.html`、`js/main.js`、`js/ui.js`、`js/validation.js`、`js/storage.js`、`css/style.css`、`data/defaultCoals.json`  
> 原始文件（保留）：`coal_blending_calc.html`

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
│   └── storage.js             # 未来扩展占位（localStorage / IndexedDB）
├── data/
│   └── defaultCoals.json      # 默认煤种数据（JSON 格式镜像，运行时不使用）
├── spec/
│   └── frontend_spec.md       # 本文档
├── tests/
│   ├── helpers.py             # 测试辅助模块（JS 拼接、mock 注入、Node.js 执行）
│   ├── test_core_calculation.py   # 核心计算测试（18 条）
│   ├── test_status_and_bounds.py  # 达标判定与边界测试（13 条）
│   ├── test_initial_data.py       # 初始数据测试（21 条）
│   └── test_dom_boundary.py       # DOM 边界测试（19 条）
├── assets/icons/              # 预留
├── coal_blending_calc.html    # 原始单文件（保留，未删除）
├── CLAUDE.md                  # Agent 规则
├── requirements.txt           # Python 依赖（pytest）
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
| `data/defaultCoal.json` | 8 条默认煤种数据（JSON 数组） | 数据镜像文件，供独立查看/编辑；运行时使用 `main.js` 中的 `DEFAULT_COALS` 常量 |

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

## 三、功能规格说明

### 3.1 数据模型
| 字段 | 类型 | 约束（必填？范围？默认？）|
|---|---|---|
| 煤种名称 | string | 必填，不能为空 |
| 煤价 | number | ≥0，默认0 |
| 灰分 | number | ≥0，默认0 |
| 硫分 | number | ≥0，默认0 |
| 挥发分 | number | ≥0，默认0 |
| 粘结 | number | ≥0，默认0 |
| 配比（成） | number | ≥0，默认0，1成=10% |
| 目标范围（每项 min/max） | number | 可空，空值按0处理 |

### 3.2 加权计算算法

- 单个煤种权重 = 配比（成） × 0.1
- 混合指标 = Σ( 煤种指标 × 权重 )
- 分母固定为 1.0（隐含十成满配：不足十成的剩余配比由无属性煤种填补，其所有指标为 0；超出十成按实际值计算，UI 提示警告）

> 示例：2 种煤，A 配比 2 成，灰分 10；B 配比 3 成，灰分 20。  
> 权重：A=0.2，B=0.3  
> 混合灰分 = 10×0.2 + 20×0.3 = 2 + 6 = 8.0  
> （实际总配比 5 成，剩余 5 成由无属性煤种填补，指标均为 0，不贡献分子）

### 3.3 达标判定

对于每个指标（除煤价外），若 min ≤ 实际值 ≤ max 则显示"达标"（绿色标签），否则"超标"（红色标签）。煤价仅显示数值及"成本指标"灰色标签。

### 3.4 配比优化建议

#### 3.4.1 功能概述

用户设定目标范围后，点击"🔍 优化配比建议"按钮，系统自动求解**满足全部指标约束且综合煤价最低**的配比组合。

#### 3.4.2 数学模型

将配比优化建模为**线性规划（LP）**问题：

- **决策变量**：每种煤的配比 r_i（成），共 n 个
- **目标函数**：min Z = Σ(p_i × r_i × 0.1) —— 最小化综合煤价
- **约束条件**：
  1. 灰分：A_min ≤ Σ(a_i × r_i × 0.1) ≤ A_max
  2. 硫分：S_min ≤ Σ(s_i × r_i × 0.1) ≤ S_max
  3. 挥发分：V_min ≤ Σ(v_i × r_i × 0.1) ≤ V_max
  4. 粘结：G_min ≤ Σ(g_i × r_i × 0.1) ≤ G_max
  5. 总配比：Σ r_i ≤ 10（不超过十成）
  6. 非负：r_i ≥ 0

使用**两阶段单纯形法**求解，每个 `≤` 约束引入松弛变量转换为标准型。

#### 3.4.3 算法

- 算法：两阶段单纯形法（Phase I 找初始可行基，Phase II 求最优解）
- 防退化：Bland's rule 选择出入基变量
- 实现文件：`js/optimizer.js`

#### 3.4.4 输入

| 输入 | 来源 | 说明 |
|------|------|------|
| 煤种列表 | 当前表格中的煤种（不含配比列） | 取 name / price / ash / sulfur / volatile / glue |
| 目标范围 | 当前"钢厂目标范围"输入框的值 | 四个指标的 min / max |

#### 3.4.5 输出

点击按钮后，在"钢厂目标范围"卡片下方展示优化结果卡片：

| 字段 | 说明 |
|------|------|
| 建议配比列表 | 每种煤的建议配比（成），保留 1 位小数 |
| 总配比 | Σ 建议配比（成） |
| 综合煤价 | 最优目标函数值（¥/t） |
| 预期混合指标 | 灰分/硫分/挥发分/粘结的计算值及达标状态 |
| 状态提示 | 成功（绿色）或失败原因（红色） |

#### 3.4.6 交互

- "🔍 优化配比建议"按钮位于"钢厂目标范围"卡片内
- 点击后触发计算，结果展示在下方的动态卡片中
- "应用建议"按钮：将建议配比填入煤种表格的各行配比输入框
- 应用后不自动计算，用户仍需点击"确认指标和配比"

#### 3.4.7 边界与错误处理

| 情况 | 行为 |
|------|------|
| 煤种数量 = 0 | 提示"请先添加煤种" |
| 目标范围未填写 | 使用默认值（同 fetchTargetBoundsFromInputs 逻辑） |
| 无可行解 | 显示"当前煤种无法在目标范围内配出合格混合煤，请放宽目标范围或调整煤种" |
| 优化后总配比 < 10 成 | 正常（剩余配比由无属性煤填补） |
| 所有煤价相同 | 找任意可行解（成本等价） |
| 目标下限 = 上限 | 作为等式约束处理（算法中为两个 ≤ 约束夹逼） |

## 四、端点 / 接口
（无后端，纯前端交互）

| 动作 | 输入 | 成功返回 | 失败情况 |
|---|---|---|---|
| 添加煤种 | 弹窗依次输入7个字段 | 表格新增一行，提示"请点击确认按钮更新" | 输入无效（非数字/取消）→ 不添加 |
| 删除煤种 | 点击某行🗑️ | 删除该行，提示"请点击确认按钮更新" | 只剩一行时禁止删除并提示 |
| 确认指标和配比 | 读取当前表格所有行 | 计算混合指标、更新达标状态、提示成功 | 存在空值时弹窗询问是否继续（空值→0） |
| 确认目标范围 | 读取四个指标的上下限 | 更新达标状态、提示成功 | 上下限颠倒时弹窗交换并确认；空值弹窗询问（空值→0） |

## 五、边界（每条之后会变成一条测试）
- 煤种数量：1种 ~ 不限（删除时至少保留1种）
- 配比总和：可全0 → 混合指标全0；> 10成时弹窗警告"当前总配比X成，超过十成，请重新配比"，不计算混合指标不更新结果
- 目标范围：下限 > 上限 → 弹窗交换，用户确认后才应用
- 空值处理：用户确认继续后，缺失数值自动当作0
- 确认计算：用户修改任意表格数值或目标范围输入框、添加新煤种、删除煤种后，不自动计算，用户点击确认按钮才会进行计算

## 六、测试

### 6.1 测试框架

`tests/helpers.py` 提供特征测试基础设施：

1. **JS 拼接**：按依赖顺序读取 `main.js` → `ui.js` → `validation.js` → `storage.js`，拼接为单一脚本
2. **浏览器 Mock**：注入最小化的 `document`、`alert`、`confirm`、`prompt`、`window` 全局对象
3. **Node.js 执行**：将拼接脚本与测试代码写入临时文件，通过 Node.js（`D:\SLDownload\Nodejs\node.exe`）子进程执行
4. **结果收集**：测试代码调用 `report(value)` 上报结果，Python 端通过 stdout JSON 解析获取

### 6.2 测试文件

| 文件 | 用例数 | 覆盖范围 |
|------|--------|---------|
| `tests/test_core_calculation.py` | 18 | `calculateHybridMetrics()` 在各种配比和煤种组合下的计算结果 |
| `tests/test_status_and_bounds.py` | 13 | `checkStatus()` 达标判定、`fetchTargetBoundsFromInputs()` 边界处理 |
| `tests/test_initial_data.py` | 21 | `DEFAULT_COALS` 数据完整性、`initCoals()`、`getDefaultCoals()` |
| `tests/test_dom_boundary.py` | 19 | 空值、缺失元素、NaN 等 DOM 边界情况 |
| `tests/test_optimizer.py` | 12 | 单纯形法求解、配比优化正确性与边界（pytest） |

**总计：83 条特征测试**

### 6.3 运行测试

```bash
# 安装依赖（优先使用清华镜像源）
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# unittest 测试（原有）
cd tests
python -m unittest discover -v

# pytest 测试（新增优化模块）
cd tests
pytest test_optimizer.py -v
```

## 七、明确不做
- 界面及弹窗中不出现英文说明，都用中文

## 八、待办与未来扩展方向（记录）

- [ ] **数据持久化**：使用 `localStorage` 保存当前煤种列表和目标范围，避免刷新丢失。（`js/storage.js` 已预留扩展点）
- [ ] **导出功能**：导出配比方案为 CSV 或截图。
- [ ] **加载预设配方**：保存/加载多个常用配方。
- [x] **配比优化建议**：给定目标范围，反向求解最经济的配比组合（线性规划）。（← 已实现，`js/optimizer.js`）
- [ ] **多方案对比**：最低成本 vs 最均衡方案，两者均达标但配比分布不同，适用不同供应链场景。
- [ ] **多煤种候选池优化**：从几十种候选煤中自动选取最优子集 + 配比，需后端服务支持。
- [ ] **图表可视化**：指标达标雷达图、配比饼图。
- [ ] **批量导入**：支持 Excel/JSON 导入煤种数据。
- [ ] **触摸滑块**：更友好的配比微调方式。
- [ ] **成本分析**：煤价与指标的综合效益提示。
