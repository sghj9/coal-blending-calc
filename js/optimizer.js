/**
 * 配比优化求解器 — 两阶段单纯形法 + Branch-and-Bound MILP + 配比优化接口
 *
 * 将配比优化建模为混合整数线性规划（MILP）：
 *   min Σ(p_i × 0.001 × y_i)    (最小化综合煤价, y_i = 100 × r_i)
 *   s.t. 指标下限 ≤ Σ(指标_i × 0.001 × y_i) ≤ 指标上限   (灰分/挥发分/硫分)
 *        Σ y_i = 1000            (总配比等于十成，等式约束)
 *        y_i ∈ Z⁺ (0~1000 整数, 每 1 单位 = 0.01 成配比)
 *
 * 混合指标采用标准加权平均 Σ(指标×r)/Σr；因 Σr=10（等式）为常数，
 * 加权平均 = Σ(指标×y×0.001)，约束保持线性。粘结不作为约束，仅参考。
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
// 混合整数线性规划（MILP）— Branch-and-Bound 框架
// ═══════════════════════════════════════════════════════════

/**
 * 分支定界法求解 MILP：前 nVars 个变量为整数约束
 *
 * 每个节点重新构建 A、b 后调用 simplex() 求解 LP 松弛。
 * 小规模问题（n ≤ 20）下，simplex 单次求解 < 1ms，B&B 总开销 < 50ms。
 *
 * @param {number[]} c - 目标函数系数
 * @param {number[][]} A - 约束矩阵（每行 ≤ 约束）
 * @param {number[]} b - 约束右端常数
 * @param {number} nVars - 需要整数约束的变量数（对应 y_0..y_{nVars-1}）
 * @returns {{success: boolean, x: number[]|null, obj: number|null, message: string}}
 */
function _milpSolve(c, A, b, nVars) {
    var EPS = 1e-10;
    var maxNodes = 2000;
    var nodeCount = 0;

    var bestObj = Infinity;
    var bestX = null;

    // 将初始 A、b 被复用前的引用无关紧要（每个节点 clone 自己的约束集）
    // DFS 栈：{A, b}
    var stack = [{ A: A, b: b }];

    while (stack.length > 0 && nodeCount < maxNodes) {
        var node = stack.pop();
        nodeCount++;

        // 1. 求解 LP 松弛
        var sol = simplex(c, node.A, node.b);
        if (!sol.success) continue;              // 剪枝：不可行

        if (sol.obj >= bestObj - EPS) continue;   // 剪枝：下界 ≥ 已找到的最优

        // 2. 检查整数性（前 nVars 个变量）
        var fracIdx = -1;
        for (var i = 0; i < nVars; i++) {
            var xi = sol.x[i] || 0;
            var nearestInt = Math.round(xi);
            if (Math.abs(xi - nearestInt) > 1e-6) {
                fracIdx = i;
                break;
            }
        }

        if (fracIdx === -1) {
            // 全部整数 → 记录为当前最优
            for (var i = 0; i < nVars; i++) {
                sol.x[i] = Math.round(sol.x[i] || 0);
            }
            bestObj = sol.obj;
            bestX = sol.x;
            continue;
        }

        // 3. 分支
        var val = sol.x[fracIdx];
        var floorVal = Math.floor(val);
        var ceilVal = Math.ceil(val);

        // 分支 A: y_k ≥ ceil → -y_k ≤ -ceil（先入栈，后处理）
        var rowA = [];
        for (var j = 0; j < nVars; j++) rowA.push(0);
        rowA[fracIdx] = -1;
        stack.push({
            A: node.A.concat([rowA]),
            b: node.b.concat([-ceilVal])
        });

        // 分支 B: y_k ≤ floor（后入栈，先处理 → floor 优先搜索）
        var rowB = [];
        for (var j = 0; j < nVars; j++) rowB.push(0);
        rowB[fracIdx] = 1;
        stack.push({
            A: node.A.concat([rowB]),
            b: node.b.concat([floorVal])
        });
    }

    if (bestX !== null) {
        return { success: true, x: bestX, obj: bestObj, message: "MILP优化成功" };
    }
    if (nodeCount >= maxNodes) {
        return { success: false, x: null, obj: null,
            message: "优化超时：分支节点数超过上限，请减少煤种数量或放宽约束" };
    }
    return { success: false, x: null, obj: null, message: "无可行整数解" };
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

    // ── 构建 MILP（y_i = 100 × r_i，y_i 为整数，步长 0.01 成）──
    // 所有系数 × 0.001（因为 r_i = y_i/100，权重 = y_i × 0.001，分母固定为 10 成）

    var c = [];        // 目标函数系数
    var A = [];        // 约束矩阵
    var bVec = [];     // 约束右端常数
    var EPS = 1e-12;

    for (var i = 0; i < n; i++) {
        c.push((coals[i].price || 0) * 0.001);
    }

    // 灰分、挥发分、硫分参与优化约束（粘结洗煤后不可预判，仅参考）
    var metricDefs = [
        { key: "ash", min: bAsh.min, max: bAsh.max },
        { key: "volatile", min: bVolatile.min, max: bVolatile.max },
        { key: "sulfur", min: bSulfur.min, max: bSulfur.max }
    ];

    for (var k = 0; k < metricDefs.length; k++) {
        var mk = metricDefs[k];

        // 上界约束：Σ(val_i × 0.001 × y_i) ≤ max
        if (mk.max < Infinity) {
            var rowUpper = [];
            for (var i = 0; i < n; i++) {
                rowUpper.push((coals[i][mk.key] || 0) * 0.001);
            }
            A.push(rowUpper);
            bVec.push(mk.max);
        }

        // 下界约束：Σ(val_i × 0.001 × y_i) ≥ min
        // → -Σ(val_i × 0.001 × y_i) ≤ -min
        if (mk.min > EPS) {
            var rowLower = [];
            for (var i = 0; i < n; i++) {
                rowLower.push(-(coals[i][mk.key] || 0) * 0.001);
            }
            A.push(rowLower);
            bVec.push(-mk.min);
        }
    }

    // 总配比约束：Σ y_i = 1000（即 Σ r_i = 10，等式约束）
    // 拆为 ≤ 1000 与 ≥ 1000（即 -Σ y_i ≤ -1000）两行
    var rowTotalLE = [];
    var rowTotalGE = [];
    for (var i = 0; i < n; i++) {
        rowTotalLE.push(1);
        rowTotalGE.push(-1);
    }
    A.push(rowTotalLE);
    bVec.push(1000);
    A.push(rowTotalGE);
    bVec.push(-1000);

    // 调料煤约束：单种 ≤ 1 成（y_i ≤ 100），多种合计 ≤ 1.5 成（Σy_i ≤ 150）
    // 仅对名称命中调料煤清单的煤种生效（见 main.js isSeasoningCoal）
    var seasoningIdx = [];
    for (var i = 0; i < n; i++) {
        if (isSeasoningCoal(coals[i].name)) seasoningIdx.push(i);
    }
    // 单种上限：每个调料煤 y_i ≤ 100
    for (var s = 0; s < seasoningIdx.length; s++) {
        var rowSingle = [];
        for (var i = 0; i < n; i++) rowSingle.push(0);
        rowSingle[seasoningIdx[s]] = 1;
        A.push(rowSingle);
        bVec.push(100);
    }
    // 合计上限：Σ 调料煤 y_i ≤ 150（仅当存在 ≥2 种调料煤时才追加）
    if (seasoningIdx.length > 1) {
        var rowSum = [];
        for (var i = 0; i < n; i++) {
            rowSum.push(seasoningIdx.indexOf(i) >= 0 ? 1 : 0);
        }
        A.push(rowSum);
        bVec.push(150);
    }

    // ── 调用 MILP 求解（前 n 个变量为整数）──
    var result = _milpSolve(c, A, bVec, n);

    if (!result.success) {
        return {
            success: false, ratios: null, totalRatio: 0, cost: 0,
            metrics: null, status: null,
            message: result.message || "无法找到满足所有目标范围的配比方案，请放宽目标范围或调整煤种"
        };
    }

    // ── y_i → r_i（/100，天然 2 位小数，无需舍入）──
    var ratios = [];
    var totalRatio = 0;
    for (var i = 0; i < n; i++) {
        var yi = result.x[i] || 0;
        var ri = yi / 100;
        ratios.push(ri);
        totalRatio += ri;
    }
    totalRatio = Math.round(totalRatio * 100) / 100;

    // ── 计算混合指标（标准加权平均 Σ(指标×r)/Σr，2 位舍入）──
    // totalRatio 由等式约束保证为 10；为前向兼容（未来总配比=8 等场景），
    // 这里按实际 totalRatio 做分母，并做除零保护。
    var sumAsh = 0, sumSulfur = 0, sumVolatile = 0, sumGlue = 0, sumPrice = 0;
    for (var i = 0; i < n; i++) {
        var r = ratios[i];
        sumAsh += (coals[i].ash || 0) * r;
        sumSulfur += (coals[i].sulfur || 0) * r;
        sumVolatile += (coals[i].volatile || 0) * r;
        sumGlue += (coals[i].glue || 0) * r;
        sumPrice += (coals[i].price || 0) * r;
    }

    var denom = (totalRatio === 0) ? 1 : totalRatio;  // 除零保护
    var round2 = function (v) { return Math.round(v * 100) / 100; };
    var metrics = {
        ash: round2(sumAsh / denom),
        sulfur: round2(sumSulfur / denom),
        volatile: round2(sumVolatile / denom),
        glue: round2(sumGlue / denom),
        price: round2(sumPrice / denom)
    };

    // ── 达标判定（基于 2 位舍入后的指标值）──
    var status = {
        ash: metrics.ash >= bAsh.min - EPS && metrics.ash <= bAsh.max + EPS,
        sulfur: metrics.sulfur >= bSulfur.min - EPS && metrics.sulfur <= bSulfur.max + EPS,
        volatile: metrics.volatile >= bVolatile.min - EPS && metrics.volatile <= bVolatile.max + EPS,
        glue: null      // 洗煤后粘结不可预判，仅作参考值
    };

    return {
        success: true,
        ratios: ratios,
        totalRatio: totalRatio,
        cost: metrics.price,
        metrics: metrics,
        status: status,
        message: "优化成功，综合煤价 " + metrics.price.toFixed(2) + " ¥/t"
    };
}
