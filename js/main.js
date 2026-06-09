const DEFAULT_COALS = [
    { name: "神华9层", price: 650, ash: 6.5, sulfur: 3.0, volatile: 31, glue: 90, ratio: 1.0 },
    { name: "11#主焦混洗", price: 900, ash: 9.0, sulfur: 0.8, volatile: 29, glue: 90, ratio: 2.0 },
    { name: "四股权", price: 1150, ash: 11.5, sulfur: 3.4, volatile: 34, glue: 90, ratio: 1.5 },
    { name: "金河煤", price: 600, ash: 6.0, sulfur: 0.2, volatile: 30, glue: 20, ratio: 0.6 },
    { name: "免洗煤", price: 500, ash: 5.0, sulfur: 0.5, volatile: 32, glue: 0, ratio: 0.5 },
    { name: "圆通2硫", price: 1000, ash: 15.0, sulfur: 2.0, volatile: 31, glue: 88, ratio: 0.5 },
    { name: "圆通1.5硫", price: 700, ash: 15.0, sulfur: 1.5, volatile: 32, glue: 86, ratio: 1.0 },
    { name: "温明煤", price: 1020, ash: 15.0, sulfur: 1.0, volatile: 33, glue: 90, ratio: 0.9 }
];

let coals = [];

let targetBounds = {
    ash: { min: 0, max: 11.0 },
    sulfur: { min: 0, max: 1.0 },
    volatile: { min: 28, max: 34 },
    glue: { min: 75, max: 100 }
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

    for (let c of coals) {
        let weight = (c.ratio || 0) * 0.1;
        sumAsh += (c.ash || 0) * weight;
        sumSulfur += (c.sulfur || 0) * weight;
        sumVolatile += (c.volatile || 0) * weight;
        sumGlue += (c.glue || 0) * weight;
        sumPrice += (c.price || 0) * weight;
    }

    // 分母固定为 1.0（隐含十成满配，不足十成的剩余配比由无属性煤种填补）
    return {
        ash: sumAsh,
        sulfur: sumSulfur,
        volatile: sumVolatile,
        glue: sumGlue,
        price: sumPrice
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
