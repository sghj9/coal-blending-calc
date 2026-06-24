function createNumberInput(initialVal, minVal, maxVal, step, onUpdate) {
    const input = document.createElement('input');
    input.type = 'number';
    input.value = initialVal;
    input.step = step;
    if (minVal !== undefined) input.min = minVal;
    if (maxVal !== undefined) input.max = maxVal;
    input.addEventListener('change', function(e) {
        let newVal = parseFloat(e.target.value);
        if (isNaN(newVal)) newVal = 0;
        if (newVal < minVal) newVal = minVal;
        if (newVal > maxVal) newVal = maxVal;
        onUpdate(newVal);
    });
    return input;
}

function renderTable() {
    const tbody = document.getElementById('tableBody');
    tbody.innerHTML = '';
    coals.forEach((coal, idx) => {
        const row = tbody.insertRow();
        const nameCell = row.insertCell(0);
        const nameInput = document.createElement('input');
        nameInput.type = 'text';
        nameInput.value = coal.name;
        nameInput.className = 'name-input';
        nameInput.addEventListener('change', (e) => { coals[idx].name = e.target.value; });
        nameCell.appendChild(nameInput);

        const priceCell = row.insertCell(1);
        const priceInput = createNumberInput(coal.price, 0, 9999, 0.1, (val) => { coals[idx].price = val; });
        priceCell.appendChild(priceInput);

        const ashCell = row.insertCell(2);
        const ashInput = createNumberInput(coal.ash, 0, 60, 0.1, (val) => { coals[idx].ash = val; });
        ashCell.appendChild(ashInput);

        const volCell = row.insertCell(3);
        const volInput = createNumberInput(coal.volatile, 0, 60, 0.1, (val) => { coals[idx].volatile = val; });
        volCell.appendChild(volInput);

        const sulfurCell = row.insertCell(4);
        const sulfurInput = createNumberInput(coal.sulfur, 0, 10, 0.01, (val) => { coals[idx].sulfur = val; });
        sulfurCell.appendChild(sulfurInput);

        const glueCell = row.insertCell(5);
        const glueInput = createNumberInput(coal.glue, 0, 120, 1, (val) => { coals[idx].glue = val; });
        glueCell.appendChild(glueInput);

        const ratioCell = row.insertCell(6);
        const ratioInput = createNumberInput(coal.ratio, 0, 999, 0.01, (val) => { coals[idx].ratio = val; });
        ratioCell.appendChild(ratioInput);

        // 是否调料煤（只读，按名称精确匹配清单派生，不参与计算输入）
        const seasoningCell = row.insertCell(7);
        seasoningCell.textContent = isSeasoningCoal(coal.name) ? '是' : '否';
        seasoningCell.className = isSeasoningCoal(coal.name) ? 'seasoning-yes' : 'seasoning-no';

        const delCell = row.insertCell(8);
        const delBtn = document.createElement('button');
        delBtn.textContent = '🗑️';
        delBtn.className = 'delete-btn';
        delBtn.addEventListener('click', () => {
            if (coals.length === 1) { alert("至少保留一个煤种"); return; }
            coals.splice(idx, 1);
            renderTable();
            updateTotalRatioDisplay();
            alert("已删除煤种，请点击【确认指标和配比】按钮更新计算结果。");
        });
        delCell.appendChild(delBtn);
    });
    updateTotalRatioDisplay();
}

function updateTotalRatioDisplay() {
    let total = coals.reduce((sum, c) => sum + (c.ratio > 0 ? c.ratio : 0), 0);
    if (total > 10.005) {
        document.getElementById('totalRatioInfo').innerHTML = `⚠️ 当前总配比为 ${total.toFixed(2)} 成（超出十成，请注意）`;
    } else {
        document.getElementById('totalRatioInfo').innerHTML = `📐 当前总配比为 ${total.toFixed(2)} 成`;
    }
}

function updateResultUI(avg) {
    const container = document.getElementById('metricsList');
    if (!container) return;
    const items = [
        { label: '灰分 A%', key: 'ash', unit: '%', precision: 2, type: 'ash' },
        { label: '挥发分 V%', key: 'volatile', unit: '%', precision: 2, type: 'volatile' },
        { label: '硫分 S%', key: 'sulfur', unit: '%', precision: 2, type: 'sulfur' },
        { label: '粘结 G', key: 'glue', unit: '', precision: 2, type: 'glue' },
        { label: '综合煤价', key: 'price', unit: '¥/t', precision: 2, type: null }
    ];
    container.innerHTML = '';
    items.forEach(item => {
        let rawVal = avg[item.key];
        let displayVal = rawVal.toFixed(item.precision);
        let valueHtml = `${displayVal}<span class="metric-unit"> ${item.unit}</span>`;
        let statusHtml = '';
        if (item.type) {
            const isPass = checkStatus(rawVal, item.type);
            const statusText = isPass ? '达标' : '超标';
            const statusClass = isPass ? 'status-pass' : 'status-fail';
            statusHtml = `<div class="status-badge ${statusClass}">${statusText}</div>`;
        } else {
            statusHtml = `<div class="status-badge status-neutral">成本指标</div>`;
        }
        const rowDiv = document.createElement('div');
        rowDiv.className = 'metric-row';
        rowDiv.innerHTML = `
            <div class="metric-name">${item.label}</div>
            <div class="metric-value">${valueHtml}</div>
            ${statusHtml}
        `;
        container.appendChild(rowDiv);
    });
}

function fetchTargetBoundsFromInputs(silent = true) {
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

    if (ashMin > ashMax) { let t = ashMin; ashMin = ashMax; ashMax = t; if (!silent) alert("灰分下限大于上限，已自动交换为 " + ashMin.toFixed(2) + " ~ " + ashMax.toFixed(2)); }
    if (sulfurMin > sulfurMax) { let t = sulfurMin; sulfurMin = sulfurMax; sulfurMax = t; if (!silent) alert("硫分下限大于上限，已自动交换为 " + sulfurMin.toFixed(2) + " ~ " + sulfurMax.toFixed(2)); }
    if (volMin > volMax) { let t = volMin; volMin = volMax; volMax = t; if (!silent) alert("挥发分下限大于上限，已自动交换为 " + volMin.toFixed(2) + " ~ " + volMax.toFixed(2)); }
    if (glueMin > glueMax) { let t = glueMin; glueMin = glueMax; glueMax = t; if (!silent) alert("粘结下限大于上限，已自动交换为 " + glueMin.toFixed(2) + " ~ " + glueMax.toFixed(2)); }

    targetBounds.ash = { min: ashMin, max: ashMax };
    targetBounds.sulfur = { min: sulfurMin, max: sulfurMax };
    targetBounds.volatile = { min: volMin, max: volMax };
    targetBounds.glue = { min: glueMin, max: glueMax };

    if (ashMinInput) { ashMinInput.value = ashMin; ashMaxInput.value = ashMax; }
    if (sulfurMinInput) { sulfurMinInput.value = sulfurMin; sulfurMaxInput.value = sulfurMax; }
    if (volMinInput) { volMinInput.value = volMin; volMaxInput.value = volMax; }
    if (glueMinInput) { glueMinInput.value = glueMin; glueMaxInput.value = glueMax; }
}

function refreshAndNotify(message, skipConfirm = false) {
    fetchTargetBoundsFromInputs(true);

    // 检查总配比是否超过十成
    const totalRatio = coals.reduce((sum, c) => sum + (c.ratio > 0 ? c.ratio : 0), 0);
    if (totalRatio > 10.005) {
        updateTotalRatioDisplay();
        alert(`警告！当前总配比${totalRatio.toFixed(2)}成，超过十成，请重新配比`);
        return false;
    }

    const avg = calculateHybridMetrics();
    updateResultUI(avg);
    updateTotalRatioDisplay();
    if (!skipConfirm) alert(message);
    return true;
}

function renderTargetInputs() {
    const container = document.getElementById('targetRangeContainer');
    if (!container) return;
    const configs = [
        { id: 'ash', label: '灰分 A%', minVal: targetBounds.ash.min, maxVal: targetBounds.ash.max },
        { id: 'volatile', label: '挥发分 V%', minVal: targetBounds.volatile.min, maxVal: targetBounds.volatile.max },
        { id: 'sulfur', label: '硫分 S%', minVal: targetBounds.sulfur.min, maxVal: targetBounds.sulfur.max },
        { id: 'glue', label: '粘结 G', minVal: targetBounds.glue.min, maxVal: targetBounds.glue.max }
    ];
    container.innerHTML = '';
    configs.forEach(cfg => {
        const div = document.createElement('div');
        div.className = 'target-item';
        div.innerHTML = `
            <label>${cfg.label}</label>
            <div class="range-input">
                <input type="number" id="target_${cfg.id}_min" value="${cfg.minVal}" step="0.1" placeholder="下限">
                <span>~</span>
                <input type="number" id="target_${cfg.id}_max" value="${cfg.maxVal}" step="0.1" placeholder="上限">
            </div>
        `;
        container.appendChild(div);
    });
}

function syncCoalsFromTable() {
    const rows = document.querySelectorAll('#tableBody tr');
    for (let i = 0; i < rows.length && i < coals.length; i++) {
        const row = rows[i];
        const nameInput = row.cells[0].querySelector('input');
        coals[i].name = nameInput ? nameInput.value.trim() : "未命名";

        const priceVal = row.cells[1].querySelector('input')?.value;
        coals[i].price = parseFloat(priceVal);
        if (isNaN(coals[i].price)) coals[i].price = 0;

        const ashVal = row.cells[2].querySelector('input')?.value;
        coals[i].ash = parseFloat(ashVal);
        if (isNaN(coals[i].ash)) coals[i].ash = 0;

        const volatileVal = row.cells[3].querySelector('input')?.value;
        coals[i].volatile = parseFloat(volatileVal);
        if (isNaN(coals[i].volatile)) coals[i].volatile = 0;

        const sulfurVal = row.cells[4].querySelector('input')?.value;
        coals[i].sulfur = parseFloat(sulfurVal);
        if (isNaN(coals[i].sulfur)) coals[i].sulfur = 0;

        const glueVal = row.cells[5].querySelector('input')?.value;
        coals[i].glue = parseFloat(glueVal);
        if (isNaN(coals[i].glue)) coals[i].glue = 0;

        const ratioVal = row.cells[6].querySelector('input')?.value;
        coals[i].ratio = parseFloat(ratioVal);
        if (isNaN(coals[i].ratio)) coals[i].ratio = 0;
    }
}

function addCoalManually() {
    const name = prompt("请输入煤种名称：", "新煤种");
    if (name === null) return;
    const priceInput = prompt("请输入煤价 (¥/t)：", "800");
    if (priceInput === null) return;
    const ashInput = prompt("请输入灰分 A%：", "10");
    if (ashInput === null) return;
    const volatileInput = prompt("请输入挥发分 V%：", "30");
    if (volatileInput === null) return;
    const sulfurInput = prompt("请输入硫分 S%：", "0.8");
    if (sulfurInput === null) return;
    const glueInput = prompt("请输入粘结 G：", "70");
    if (glueInput === null) return;
    const ratioInput = prompt("请输入配比（成）：", "0.5");
    if (ratioInput === null) return;

    const price = parseFloat(priceInput);
    const ash = parseFloat(ashInput);
    const sulfur = parseFloat(sulfurInput);
    const volatileVal = parseFloat(volatileInput);
    const glue = parseFloat(glueInput);
    const ratio = parseFloat(ratioInput);

    if (isNaN(price) || isNaN(ash) || isNaN(sulfur) || isNaN(volatileVal) || isNaN(glue) || isNaN(ratio)) {
        alert("输入无效，请确保所有数值正确填写。");
        return;
    }

    coals.push({
        name: name.trim(),
        price: price,
        ash: ash,
        sulfur: sulfur,
        volatile: volatileVal,
        glue: glue,
        ratio: ratio
    });
    renderTable();
    updateTotalRatioDisplay();
    alert("已添加新煤种，请点击【确认指标和配比】按钮更新计算结果。");
}

/**
 * 渲染配比优化建议结果
 * @param {Object} result - optimizeBlending() 的返回值
 */
function renderOptimizeResult(result) {
    var container = document.getElementById('optimizeResultContainer');
    if (!container) return;

    container.style.display = 'block';

    if (!result.success) {
        container.innerHTML = '<div class="card" style="border-left: 4px solid #e74c3c;">' +
            '<div class="card-header"><div class="title-main">' +
            '<span class="title-icon">⚠️</span> 优化失败</div></div>' +
            '<div class="metric-row"><div class="metric-name" style="color:#e74c3c;">' +
            result.message + '</div></div></div>';
        return;
    }

    // ── 构建结果 HTML ──
    var coals = window.coals || [];
    var html = '<div class="card" style="border-left: 4px solid #27ae60;">' +
        '<div class="card-header"><div class="title-main">' +
        '<span class="title-icon">✅</span> 优化建议 · 综合煤价 ' +
        '<strong>' + result.cost.toFixed(2) + ' ¥/t</strong></div>' +
        '<div class="title-sub">总配比 ' + result.totalRatio.toFixed(2) + ' 成</div></div>';

    // 建议配比列表
    html += '<div style="padding: 8px 16px; font-size: 13px;">';
    html += '<table style="width:100%; border-collapse:collapse;">';
    html += '<tr style="border-bottom:1px solid #ddd; color:#666;">' +
        '<th style="text-align:left; padding:4px;">煤种</th>' +
        '<th style="text-align:right; padding:4px;">建议配比（成）</th></tr>';

    for (var i = 0; i < coals.length; i++) {
        var r = result.ratios[i];
        var highlight = r > 0 ? 'color:#27ae60; font-weight:bold;' : 'color:#999;';
        html += '<tr style="border-bottom:1px solid #f0f0f0;">' +
            '<td style="padding:4px;">' + (coals[i].name || '煤种' + (i+1)) + '</td>' +
            '<td style="text-align:right; padding:4px; ' + highlight + '">' +
            r.toFixed(2) + '</td></tr>';
    }
    html += '</table></div>';

    // 预期混合指标
    if (result.metrics) {
        html += '<div style="padding: 8px 16px; border-top: 1px solid #eee;">';
        html += '<div style="font-weight:bold; margin-bottom:4px;">📊 预期混合指标</div>';
        var metricItems = [
            { label: '灰分 A%', key: 'ash', unit: '%', precision: 2, constrained: true },
            { label: '挥发分 V%', key: 'volatile', unit: '%', precision: 2, constrained: true },
            { label: '硫分 S%', key: 'sulfur', unit: '%', precision: 2, constrained: true },
            { label: '粘结 G', key: 'glue', unit: '', precision: 2, constrained: false }
        ];
        for (var j = 0; j < metricItems.length; j++) {
            var item = metricItems[j];
            var val = result.metrics[item.key];
            var statusText, statusColor;
            if (item.constrained) {
                var isPass = result.status ? result.status[item.key] : false;
                statusText = isPass ? '✅ 达标' : '⚠️ 超标';
                statusColor = isPass ? '#27ae60' : '#e74c3c';
            } else {
                statusText = '📋 参考值';
                statusColor = '#888';
            }
            html += '<div style="display:flex; justify-content:space-between; padding:2px 0;">' +
                '<span>' + item.label + '</span>' +
                '<span>' + val.toFixed(item.precision) + ' ' + item.unit + '</span>' +
                '<span style="color:' + statusColor + '; font-size:12px;">' + statusText + '</span>' +
                '</div>';
        }
        html += '</div>';
    }

    // 操作按钮
    html += '<div class="btn-center" style="padding: 12px 0;">' +
        '<button class="btn-unified btn-green" id="applyOptimizeBtn">' +
        '📋 应用建议配比</button></div>';

    html += '</div>';  // end card

    container.innerHTML = html;

    // 绑定"应用建议"按钮事件
    var applyBtn = document.getElementById('applyOptimizeBtn');
    if (applyBtn) {
        applyBtn.addEventListener('click', function() {
            applyOptimizeRatios(result.ratios);
        });
    }
}

/**
 * 将优化建议的配比填入表格
 * @param {number[]} ratios - 建议配比数组
 */
function applyOptimizeRatios(ratios) {
    var rows = document.querySelectorAll('#tableBody tr');
    for (var i = 0; i < rows.length && i < ratios.length; i++) {
        var ratioInput = rows[i].cells[6].querySelector('input');
        if (ratioInput) {
            ratioInput.value = ratios[i].toFixed(2);
            // 同步到 coals 数组
            if (i < coals.length) {
                coals[i].ratio = ratios[i];
            }
        }
    }
    // 同步目标范围并自动计算更新达标情况
    fetchTargetBoundsFromInputs(true);
    var avg = calculateHybridMetrics();
    updateResultUI(avg);
    updateTotalRatioDisplay();
    alert('已应用优化建议配比，计算结果已更新。');
}
