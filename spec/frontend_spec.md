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
├── .gitignore
└── README.md
```

### 1.1 模块职责

| 文件 | 包含函数 / 内容 | 职责 |
|------|----------------|------|
| `js/main.js` | `DEFAULT_COALS`、`coals`、`targetBounds`、`getDefaultCoals()`、`initCoals()`、`calculateHybridMetrics()`、`checkStatus()`、`bindEvents()`、`init()` | 全局状态定义、核心计算逻辑、事件绑定、初始化入口 |
| `js/ui.js` | `createNumberInput()`、`renderTable()`、`updateTotalRatioDisplay()`、`updateResultUI()`、`fetchTargetBoundsFromInputs()`、`refreshAndNotify()`、`renderTargetInputs()`、`syncCoalsFromTable()`、`addCoalManually()` | DOM 创建与渲染、用户交互流程（表格、结果卡片、目标输入框、添加煤种弹窗） |
| `js/validation.js` | `checkCoalTableCompleteness()`、`confirmAndRefresh()`、`checkTargetCompleteness()` | 表单完整性校验、确认对话框逻辑 |
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
- 配比总和：任意值，可全0 → 混合指标全0
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

**总计：71 条特征测试**

### 6.3 运行测试

```bash
cd tests
python -m unittest discover -v
```

## 七、明确不做
- 界面及弹窗中不出现英文说明，都用中文

## 八、待办与未来扩展方向（记录）

- [ ] **数据持久化**：使用 `localStorage` 保存当前煤种列表和目标范围，避免刷新丢失。（`js/storage.js` 已预留扩展点）
- [ ] **导出功能**：导出配比方案为 CSV 或截图。
- [ ] **加载预设配方**：保存/加载多个常用配方。
- [ ] **配比优化建议**：给定目标范围，反向求解最经济的配比组合（线性规划）。
- [ ] **图表可视化**：指标达标雷达图、配比饼图。
- [ ] **批量导入**：支持 Excel/JSON 导入煤种数据。
- [ ] **触摸滑块**：更友好的配比微调方式。
- [ ] **成本分析**：煤价与指标的综合效益提示。
