/**
 * 配比优化求解器 — 两阶段单纯形法 + 配比优化接口
 *
 * 将配比优化建模为线性规划（LP）：
 *   min Σ(p_i × 0.1 × r_i)      (最小化综合煤价)
 *   s.t. 指标下限 ≤ Σ(指标_i × 0.1 × r_i) ≤ 指标上限
 *        Σ r_i ≤ 10              (总配比不超过十成)
 *        r_i ≥ 0
 */

// ═══════════════════════════════════════════════════════════
// 辅助函数
// ═══════════════════════════════════════════════════════════

/**
 * 枢轴操作：将 enteringCol 作为新基变量替换 leavingRow 行的旧基变量
 */
function _pivot(tableau, m, totalVars, basicVar, row, col, EPS) {
    var tableauCols = totalVars + 1;
    var pivotVal = tableau[row][col];

    // 归一化枢轴行
    for (var j = 0; j < tableauCols; j++) {
        tableau[row][j] /= pivotVal;
    }

    // 消元其他行（包括目标行）
    for (var i = 0; i <= m; i++) {
        if (i === row) continue;
        var factor = tableau[i][col];
        if (Math.abs(factor) > EPS) {
            for (var j = 0; j < tableauCols; j++) {
                tableau[i][j] -= factor * tableau[row][j];
            }
        }
    }

    // 更新基变量记录
    basicVar[row] = col;
}

/**
 * 运行单纯形迭代（Bland's rule 防循环）
 *
 * @param {number} maxCol - 只考虑列 0..maxCol-1 作为候选入基变量（Phase II 用此排除人工变量）
 * @returns {{success: boolean}} 是否成功找到最优解
 */
function _runSimplexPhase(tableau, m, totalVars, basicVar, EPS, maxCol) {
    var maxIter = 2000;
    var iter = 0;
    var tableauCols = totalVars + 1;

    // 如果未指定 maxCol，默认考虑所有变量
    if (maxCol === undefined) maxCol = totalVars;

    while (iter < maxIter) {
        iter++;

        // Bland's rule step 1: 选最小索引的负检验数作为入基变量（仅限 maxCol 范围内）
        var enteringCol = -1;
        for (var j = 0; j < maxCol; j++) {
            if (tableau[m][j] < -EPS) {
                enteringCol = j;
                break;  // 最小索引
            }
        }

        if (enteringCol === -1) {
            // 所有检验数 ≥ 0 → 已达最优
            return { success: true };
        }

        // Bland's rule step 2: 最小比值测试，平局时选最小基变量索引
        var leavingRow = -1;
        var minRatio = Infinity;
        for (var i = 0; i < m; i++) {
            var aij = tableau[i][enteringCol];
            if (aij > EPS) {
                var ratio = tableau[i][tableauCols - 1] / aij;
                if (ratio < minRatio - EPS) {
                    minRatio = ratio;
                    leavingRow = i;
                } else if (Math.abs(ratio - minRatio) <= EPS) {
                    // 比值相等 → Bland's rule: 选基变量索引更小的行
                    if (leavingRow === -1 || basicVar[i] < basicVar[leavingRow]) {
                        leavingRow = i;
                    }
                }
            }
        }

        if (leavingRow === -1) {
            // 入基变量在所有行中系数 ≤ 0 → 解无界
            return { success: false };
        }

        // 执行枢轴操作
        _pivot(tableau, m, totalVars, basicVar, leavingRow, enteringCol, EPS);
    }

    // 超过最大迭代次数
    return { success: false };
}


// ═══════════════════════════════════════════════════════════
// 单纯形法主函数
// ═══════════════════════════════════════════════════════════

/**
 * 两阶段单纯形法求解线性规划
 *
 * 标准型：min c^T x  s.t. Ax ≤ b, x ≥ 0
 *
 * @param {number[]} c - 目标函数系数（长度 n）
 * @param {number[][]} A - 约束矩阵（m × n），每行为一个 ≤ 约束
 * @param {number[]} b - 约束右端常数（长度 m）
 * @returns {{success: boolean, x: number[]|null, obj: number|null, message: string}}
 */
function simplex(c, A, b) {
    var EPS = 1e-10;

    var m = A.length;  // 约束数量
    var n = c.length;  // 原始变量数量

    if (m === 0 || n === 0) {
        return { success: false, x: null, obj: null, message: "约束或变量数量为0" };
    }

    // ── 第零步：分类约束，处理负RHS ──
    // isLEQ[i]=true  → 原约束 ≤ 型（b[i]>=0），加松弛变量
    // isLEQ[i]=false → 原RHS<0 已乘-1 翻转为≥型，需减剩余变量+加人工变量
    var isLEQ = [];
    var bWork = [];
    var AWork = [];

    for (var i = 0; i < m; i++) {
        if (b[i] >= -EPS) {
            isLEQ.push(true);
            bWork.push(b[i]);
            var rowA = [];
            for (var j = 0; j < n; j++) rowA.push(A[i][j]);
            AWork.push(rowA);
        } else {
            isLEQ.push(false);
            bWork.push(-b[i]);
            var rowA2 = [];
            for (var j = 0; j < n; j++) rowA2.push(-A[i][j]);
            AWork.push(rowA2);
        }
    }

    // 统计人工变量数量
    var numArtificial = 0;
    for (var i = 0; i < m; i++) {
        if (!isLEQ[i]) numArtificial++;
    }

    // 变量排列：[原始 x(0..n-1) | 松弛 s(0..m-1) | 人工 a(0..numArtificial-1)]
    var totalVars = n + m + numArtificial;
    var tableauCols = totalVars + 1;  // 最后一列为 RHS
    var tableauRows = m + 1;          // 最后一行为目标函數

    // 创建并初始化 tableau 为全零
    var tableau = [];
    for (var i = 0; i < tableauRows; i++) {
        tableau[i] = [];
        for (var j = 0; j < tableauCols; j++) {
            tableau[i][j] = 0;
        }
    }

    // ── 填充约束行 ──
    var artIdx = 0;
    for (var i = 0; i < m; i++) {
        // 原始变量系数
        for (var j = 0; j < n; j++) {
            tableau[i][j] = AWork[i][j];
        }
        // 松弛/剩余变量：≤→+1，≥→-1
        tableau[i][n + i] = isLEQ[i] ? 1 : -1;
        // 人工变量（仅 ≥ 约束）
        if (!isLEQ[i]) {
            tableau[i][n + m + artIdx] = 1;
            artIdx++;
        }
        // RHS
        tableau[i][tableauCols - 1] = bWork[i];
    }

    // ── 初始化基变量列表 ──
    var basicVar = [];
    artIdx = 0;
    for (var i = 0; i < m; i++) {
        if (isLEQ[i]) {
            basicVar.push(n + i);       // 松弛变量入基
        } else {
            basicVar.push(n + m + artIdx);  // 人工变量入基
            artIdx++;
        }
    }

    // ═══════════════════════════════════════════════
    // 第一阶段：最小化人工变量之和（找可行基）
    // ═══════════════════════════════════════════════
    if (numArtificial > 0) {
        // 设置第一阶段目标行：min Σ(人工变量)
        for (var j = 0; j < totalVars; j++) {
            tableau[m][j] = 0;
        }
        for (var k = 0; k < numArtificial; k++) {
            tableau[m][n + m + k] = 1;
        }
        tableau[m][tableauCols - 1] = 0;

        // 将基变量列在目标行中的系数消为 0
        for (var i = 0; i < m; i++) {
            var bv = basicVar[i];
            if (bv >= n + m) {  // 人工变量
                var coeff = tableau[m][bv];
                if (Math.abs(coeff) > EPS) {
                    for (var j = 0; j < tableauCols; j++) {
                        tableau[m][j] -= coeff * tableau[i][j];
                    }
                }
            }
        }

        // 执行单纯形迭代
        var ph1 = _runSimplexPhase(tableau, m, totalVars, basicVar, EPS);
        if (!ph1.success) {
            return { success: false, x: null, obj: null, message: "优化失败：第一阶段无法找到可行基" };
        }

        // 第一阶段最优值必须为 0（人工变量全部出基）
        var phase1Opt = tableau[m][tableauCols - 1];
        if (phase1Opt > 1e-8) {
            return { success: false, x: null, obj: null, message: "无可行解：无法同时满足所有约束条件" };
        }

        // 处理退化情况：人工变量仍在基中但值为 0
        for (var i = 0; i < m; i++) {
            var bv = basicVar[i];
            if (bv >= n + m) {
                // 人工变量在基中 → 尝试用非人工变量替换
                if (tableau[i][tableauCols - 1] > 1e-8) {
                    return { success: false, x: null, obj: null, message: "无可行解：人工变量无法出基" };
                }
                // 找任何非人工、非零系数的列做枢轴
                var found = false;
                for (var j = 0; j < n + m; j++) {
                    if (Math.abs(tableau[i][j]) > EPS) {
                        _pivot(tableau, m, totalVars, basicVar, i, j, EPS);
                        found = true;
                        break;
                    }
                }
                // 如果找不到就忽略（整行为零，冗余约束）
            }
        }
    }

    // ═══════════════════════════════════════════════
    // 第二阶段：优化原始目标函数
    // ═══════════════════════════════════════════════
    // 清空目标行，设置原始系数
    for (var j = 0; j < totalVars; j++) {
        tableau[m][j] = 0;
    }
    for (var j = 0; j < n; j++) {
        tableau[m][j] = c[j];
    }
    tableau[m][tableauCols - 1] = 0;

    // 将基变量在目标行中的系数消为 0
    for (var i = 0; i < m; i++) {
        var bv = basicVar[i];
        if (bv < n + m) {  // 原始变量或松弛变量
            var coeff = tableau[m][bv];
            if (Math.abs(coeff) > EPS) {
                for (var j = 0; j < tableauCols; j++) {
                    tableau[m][j] -= coeff * tableau[i][j];
                }
            }
        } else {
            // 人工变量仍在基中（退化）→ 其系数在目标中本来就是 0
        }
    }

    // 执行单纯形迭代（仅考虑原始变量 + 松弛变量，排除人工变量）
    var ph2 = _runSimplexPhase(tableau, m, totalVars, basicVar, EPS, n + m);
    if (!ph2.success) {
        return { success: false, x: null, obj: null, message: "优化失败：解无界" };
    }

    // ── 提取结果 ──
    var x = [];
    for (var j = 0; j < n; j++) x.push(0);

    for (var i = 0; i < m; i++) {
        var bv = basicVar[i];
        if (bv < n) {
            x[bv] = tableau[i][tableauCols - 1];
        }
    }

    // 注意：单纯形表中目标行 RHS 存的是 -目标值，需取反
    var obj = -tableau[m][tableauCols - 1];

    return { success: true, x: x, obj: obj, message: "优化成功" };
}


// ═══════════════════════════════════════════════════════════
// 配比优化接口
// ═══════════════════════════════════════════════════════════

/**
 * 给定煤种列表和目标范围，求成本最低的配比组合
 *
 * @param {Array} coals - 煤种数组 [{name, price, ash, sulfur, volatile, glue}, ...]
 * @param {Object} bounds - 目标范围 {ash:{min,max}, sulfur:{min,max}, volatile:{min,max}, glue:{min,max}}
 * @returns {{
 *   success: boolean,
 *   ratios: number[]|null,
 *   totalRatio: number,
 *   cost: number,
 *   metrics: {ash:number, sulfur:number, volatile:number, glue:number, price:number}|null,
 *   status: {ash:boolean, sulfur:boolean, volatile:boolean, glue:boolean}|null,
 *   message: string
 * }}
 */
function optimizeBlending(coals, bounds) {
    // ── 输入校验 ──
    if (!coals || coals.length === 0) {
        return {
            success: false, ratios: null, totalRatio: 0, cost: 0,
            metrics: null, status: null,
            message: "请先添加煤种，至少需要1种煤才能进行优化"
        };
    }

    var n = coals.length;

    // 确保 bounds 有默认值
    bounds = bounds || {};
    var bAsh = bounds.ash || { min: 0, max: 20 };
    var bSulfur = bounds.sulfur || { min: 0, max: 5 };
    var bVolatile = bounds.volatile || { min: 0, max: 50 };
    var bGlue = bounds.glue || { min: 0, max: 120 };

    // ── 构建线性规划 ──
    // 决策变量：r_i（每种煤的配比，单位：成）
    // 目标函数系数 = price_i × 0.1（因为权重 = 配比 × 0.1）

    var c = [];        // 目标函数系数
    var A = [];        // 约束矩阵
    var bVec = [];     // 约束右端常数
    var EPS = 1e-12;

    for (var i = 0; i < n; i++) {
        c.push((coals[i].price || 0) * 0.1);
    }

    // 辅助：为指标构建约束行（上界 ≤ max，下界 ≥ min → -Σ ≤ -min）
    var metrics = [
        { key: "ash", label: "灰分", min: bAsh.min, max: bAsh.max },
        { key: "sulfur", label: "硫分", min: bSulfur.min, max: bSulfur.max },
        { key: "volatile", label: "挥发分", min: bVolatile.min, max: bVolatile.max },
        { key: "glue", label: "粘结", min: bGlue.min, max: bGlue.max }
    ];

    for (var k = 0; k < metrics.length; k++) {
        var mk = metrics[k];

        // 上界约束：Σ(val_i × 0.1 × r_i) ≤ max
        if (mk.max < Infinity) {
            var rowUpper = [];
            for (var i = 0; i < n; i++) {
                rowUpper.push((coals[i][mk.key] || 0) * 0.1);
            }
            A.push(rowUpper);
            bVec.push(mk.max);
        }

        // 下界约束：Σ(val_i × 0.1 × r_i) ≥ min
        // → -Σ(val_i × 0.1 × r_i) ≤ -min
        if (mk.min > EPS) {
            var rowLower = [];
            for (var i = 0; i < n; i++) {
                rowLower.push(-(coals[i][mk.key] || 0) * 0.1);
            }
            A.push(rowLower);
            bVec.push(-mk.min);
        }
    }

    // 总配比约束：Σ r_i ≤ 10
    var rowTotal = [];
    for (var i = 0; i < n; i++) {
        rowTotal.push(1);
    }
    A.push(rowTotal);
    bVec.push(10);

    // ── 调用单纯形法求解 ──
    var result = simplex(c, A, bVec);

    if (!result.success) {
        return {
            success: false, ratios: null, totalRatio: 0, cost: 0,
            metrics: null, status: null,
            message: result.message || "无法找到满足所有目标范围的配比方案，请放宽目标范围或调整煤种"
        };
    }

    // ── 后处理：整理配比（保留全精度用于计算，另存显示用配比） ──
    var fullX = result.x;
    var ratios = [];
    var totalRatio = 0;
    for (var i = 0; i < n; i++) {
        var r = fullX[i];
        // 将极小值（浮点噪声）截断为 0
        if (r < 1e-8) r = 0;
        // 保留一位小数用于展示
        var displayR = Math.round(r * 10) / 10;
        ratios.push(displayR);
        totalRatio += displayR;
    }
    totalRatio = Math.round(totalRatio * 10) / 10;

    // ── 计算混合指标（使用全精度配比，确保约束满足） ──
    var sumAsh = 0, sumSulfur = 0, sumVolatile = 0, sumGlue = 0, sumPrice = 0;

    for (var i = 0; i < n; i++) {
        // 使用全精度配比（fullX），而非四舍五入后的 ratios
        var rawR = fullX[i] < 1e-8 ? 0 : fullX[i];
        var weight = rawR * 0.1;
        sumAsh += (coals[i].ash || 0) * weight;
        sumSulfur += (coals[i].sulfur || 0) * weight;
        sumVolatile += (coals[i].volatile || 0) * weight;
        sumGlue += (coals[i].glue || 0) * weight;
        sumPrice += (coals[i].price || 0) * weight;
    }

    // 分母固定为 1.0（隐含十成满配）
    var metrics = {
        ash: sumAsh,
        sulfur: sumSulfur,
        volatile: sumVolatile,
        glue: sumGlue,
        price: sumPrice
    };

    // ── 达标判定 ──
    var status = {
        ash: sumAsh >= bAsh.min - EPS && sumAsh <= bAsh.max + EPS,
        sulfur: sumSulfur >= bSulfur.min - EPS && sumSulfur <= bSulfur.max + EPS,
        volatile: sumVolatile >= bVolatile.min - EPS && sumVolatile <= bVolatile.max + EPS,
        glue: sumGlue >= bGlue.min - EPS && sumGlue <= bGlue.max + EPS
    };

    return {
        success: true,
        ratios: ratios,
        totalRatio: totalRatio,
        cost: Math.round(sumPrice * 100) / 100,
        metrics: {
            ash: Math.round(metrics.ash * 10000) / 10000,
            sulfur: Math.round(metrics.sulfur * 10000) / 10000,
            volatile: Math.round(metrics.volatile * 10000) / 10000,
            glue: Math.round(metrics.glue * 10000) / 10000,
            price: Math.round(metrics.price * 100) / 100
        },
        status: status,
        message: "优化成功，综合煤价 " + (Math.round(sumPrice * 100) / 100).toFixed(2) + " ¥/t"
    };
}
