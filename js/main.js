const DEFAULT_COALS = [
    { name: "温明15灰精煤", price: 950, ash: 15.22, sulfur: 0.68, volatile: 34.14, glue: 90, ratio: 4.5 },
    { name: "四股泉", price: 1067, ash: 11.5, sulfur: 3.4, volatile: 34, glue: 90, ratio: 3 },
    { name: "混洗煤（2-1/鑫发矿1:1）", price: 690, ash: 5.62, sulfur: 0.42, volatile: 29.98, glue: 85, ratio: 2 },
    { name: "免洗煤", price: 100, ash: 5, sulfur: 0.5, volatile: 32, glue: 0, ratio: 0.5 }
];

let coals = [];

// 调料煤清单（canonical 名称 + 别名），优化器按此清单约束配比：
// 单种 ≤ 1 成、多种合计 ≤ 1.5 成。匹配方式：coal.name 精确等于清单任一项。
const SEASONING_COAL_NAMES = [
    "免洗煤", "金河煤", "金河精煤",
    "魏矿", "魏矿精煤",
    "无烟沫子", "无烟煤", "无烟沫子精煤"
];

/**
 * 判断煤种是否为调料煤（按名称精确匹配清单）
 * @param {string} name - 煤种名称
 * @returns {boolean}
 */
function isSeasoningCoal(name) {
    if (!name) return false;
    return SEASONING_COAL_NAMES.indexOf(name) >= 0;
}

let targetBounds = {
    ash: { min: 11, max: 12 },
    sulfur: { min: 1, max: 2 },
    volatile: { min: 28, max: 33 },
    glue: { min: 85, max: 100 }
};

function getDefaultCoals() {
    return DEFAULT_COALS.map(c => ({ ...c, ratio: c.ratio }));
}

function initCoals() {
    coals = getDefaultCoals();
}

function calculateHybridMetrics() {
    const coalCount = coals.length;
    if (coalCount === 0) {
        return { ash: 0, sulfur: 0, volatile: 0, glue: 0, price: 0 };
    }

    let sumAsh = 0, sumSulfur = 0, sumVolatile = 0, sumGlue = 0, sumPrice = 0;
    let totalRatio = 0;

    for (let c of coals) {
        let ratio = (c.ratio || 0);
        totalRatio += ratio;
        // 加权分子：Σ(指标 × 配比)
        sumAsh += (c.ash || 0) * ratio;
        sumSulfur += (c.sulfur || 0) * ratio;
        sumVolatile += (c.volatile || 0) * ratio;
        sumGlue += (c.glue || 0) * ratio;
        sumPrice += (c.price || 0) * ratio;
    }

    // 分母 = 实际总配比 Σr_i（标准加权平均）；总配比为 0 时结果全 0（除零保护）
    if (totalRatio === 0) {
        return { ash: 0, sulfur: 0, volatile: 0, glue: 0, price: 0 };
    }

    // 四舍五入到 2 位小数
    var round2 = function (v) { return Math.round(v * 100) / 100; };
    return {
        ash: round2(sumAsh / totalRatio),
        sulfur: round2(sumSulfur / totalRatio),
        volatile: round2(sumVolatile / totalRatio),
        glue: round2(sumGlue / totalRatio),
        price: round2(sumPrice / totalRatio)
    };
}

function checkStatus(value, type) {
    let bounds = targetBounds[type];
    if (!bounds) return false;
    return value >= bounds.min && value <= bounds.max;
}

function bindEvents() {
    document.getElementById('addCoalBtn').addEventListener('click', addCoalManually);

    document.getElementById('confirmCoalBtn').addEventListener('click', () => {
        confirmAndRefresh(
            checkCoalTableCompleteness,
            '✅ 指标和配比已确认，计算结果已更新',
            () => {
                syncCoalsFromTable();
                return refreshAndNotify('', true);
            }
        );
    });

    document.getElementById('applyTargetBtn').addEventListener('click', () => {
        const missingTarget = checkTargetCompleteness();
        if (missingTarget.length > 0) {
            const msg = "以下目标范围未填写：\n" + missingTarget.join("\n") + "\n\n是否仍继续计算？(未填数值将自动视为0)";
            if (!confirm(msg)) return;
        }
        // 获取当前输入框的值，处理颠倒并提示确认
        const ashMinInput = document.getElementById('target_ash_min');
        const ashMaxInput = document.getElementById('target_ash_max');
        const sulfurMinInput = document.getElementById('target_sulfur_min');
        const sulfurMaxInput = document.getElementById('target_sulfur_max');
        const volMinInput = document.getElementById('target_volatile_min');
        const volMaxInput = document.getElementById('target_volatile_max');
        const glueMinInput = document.getElementById('target_glue_min');
        const glueMaxInput = document.getElementById('target_glue_max');

        let ashMin = ashMinInput ? parseFloat(ashMinInput.value) : 0;
        let ashMax = ashMaxInput ? parseFloat(ashMaxInput.value) : 20;
        let sulfurMin = sulfurMinInput ? parseFloat(sulfurMinInput.value) : 0;
        let sulfurMax = sulfurMaxInput ? parseFloat(sulfurMaxInput.value) : 5;
        let volMin = volMinInput ? parseFloat(volMinInput.value) : 0;
        let volMax = volMaxInput ? parseFloat(volMaxInput.value) : 50;
        let glueMin = glueMinInput ? parseFloat(glueMinInput.value) : 0;
        let glueMax = glueMaxInput ? parseFloat(glueMaxInput.value) : 120;

        if (isNaN(ashMin)) ashMin = 0;
        if (isNaN(ashMax)) ashMax = 20;
        if (isNaN(sulfurMin)) sulfurMin = 0;
        if (isNaN(sulfurMax)) sulfurMax = 5;
        if (isNaN(volMin)) volMin = 0;
        if (isNaN(volMax)) volMax = 50;
        if (isNaN(glueMin)) glueMin = 0;
        if (isNaN(glueMax)) glueMax = 120;

        let swapped = false;
        let swapMessages = [];
        if (ashMin > ashMax) { let t=ashMin; ashMin=ashMax; ashMax=t; swapMessages.push(`灰分: ${ashMin.toFixed(2)} ~ ${ashMax.toFixed(2)}`); swapped=true; }
        if (sulfurMin > sulfurMax) { let t=sulfurMin; sulfurMin=sulfurMax; sulfurMax=t; swapMessages.push(`硫分: ${sulfurMin.toFixed(2)} ~ ${sulfurMax.toFixed(2)}`); swapped=true; }
        if (volMin > volMax) { let t=volMin; volMin=volMax; volMax=t; swapMessages.push(`挥发分: ${volMin.toFixed(2)} ~ ${volMax.toFixed(2)}`); swapped=true; }
        if (glueMin > glueMax) { let t=glueMin; glueMin=glueMax; glueMax=t; swapMessages.push(`粘结: ${glueMin.toFixed(2)} ~ ${glueMax.toFixed(2)}`); swapped=true; }

        if (swapped) {
            const msg = "以下目标范围下限大于上限，已自动交换为：\n" + swapMessages.join("\n") + "\n\n是否确认应用此范围？";
            if (!confirm(msg)) return;
            // 更新输入框显示交换后的值
            if (ashMinInput) { ashMinInput.value = ashMin; ashMaxInput.value = ashMax; }
            if (sulfurMinInput) { sulfurMinInput.value = sulfurMin; sulfurMaxInput.value = sulfurMax; }
            if (volMinInput) { volMinInput.value = volMin; volMaxInput.value = volMax; }
            if (glueMinInput) { glueMinInput.value = glueMin; glueMaxInput.value = glueMax; }
        }

        // 应用目标范围并弹出成功提示
        fetchTargetBoundsFromInputs(false);
        refreshAndNotify('✅ 目标范围已应用，计算结果已更新', false);
    });

    document.getElementById('optimizeBtn').addEventListener('click', handleOptimize);
}

function init() {
    initCoals();
    renderTargetInputs();
    renderTable();
    bindEvents();
    fetchTargetBoundsFromInputs(true);
    const avg = calculateHybridMetrics();
    updateResultUI(avg);
    updateTotalRatioDisplay();
}

function handleOptimize() {
    // 同步表格数据到 coals 数组
    syncCoalsFromTable();
    // 同步目标范围到 targetBounds
    fetchTargetBoundsFromInputs(true);

    if (coals.length === 0) {
        alert("请先添加煤种，至少需要1种煤才能进行优化");
        return;
    }

    // 调用优化算法
    var result = optimizeBlending(coals, targetBounds);

    // 渲染优化结果
    renderOptimizeResult(result);
}

// init() 由 index.html 在所有脚本加载完成后调用
