function checkCoalTableCompleteness() {
    const missing = [];
    const rows = document.querySelectorAll('#tableBody tr');
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const nameInput = row.cells[0]?.querySelector('input');
        const coalName = nameInput ? nameInput.value.trim() : `第${i+1}行`;
        if (!nameInput || nameInput.value.trim() === "") {
            missing.push(`${coalName}的煤种名称`);
        }
        const priceInput = row.cells[1]?.querySelector('input');
        const ashInput = row.cells[2]?.querySelector('input');
        const sulfurInput = row.cells[3]?.querySelector('input');
        const volatileInput = row.cells[4]?.querySelector('input');
        const glueInput = row.cells[5]?.querySelector('input');
        const ratioInput = row.cells[6]?.querySelector('input');

        const priceVal = priceInput ? priceInput.value : "";
        const ashVal = ashInput ? ashInput.value : "";
        const sulfurVal = sulfurInput ? sulfurInput.value : "";
        const volatileVal = volatileInput ? volatileInput.value : "";
        const glueVal = glueInput ? glueInput.value : "";
        const ratioVal = ratioInput ? ratioInput.value : "";

        if (priceVal === "" || isNaN(parseFloat(priceVal))) missing.push(`${coalName}的煤价`);
        if (ashVal === "" || isNaN(parseFloat(ashVal))) missing.push(`${coalName}的灰分`);
        if (sulfurVal === "" || isNaN(parseFloat(sulfurVal))) missing.push(`${coalName}的硫分`);
        if (volatileVal === "" || isNaN(parseFloat(volatileVal))) missing.push(`${coalName}的挥发分`);
        if (glueVal === "" || isNaN(parseFloat(glueVal))) missing.push(`${coalName}的粘结`);
        if (ratioVal === "" || isNaN(parseFloat(ratioVal))) missing.push(`${coalName}的配比`);
    }
    return missing;
}

function confirmAndRefresh(checkFunc, successMsg, refreshAction) {
    const missing = checkFunc();
    if (missing.length > 0) {
        const msg = "以下数值未填写：\n" + missing.join("\n") + "\n\n是否仍继续计算？(未填数值将自动视为0)";
        if (confirm(msg)) {
            refreshAction();
            alert(successMsg);
        }
    } else {
        refreshAction();
        alert(successMsg);
    }
}

function checkTargetCompleteness() {
    const missing = [];
    const mapping = [
        { id: 'target_ash_min', name: '灰分的下限' },
        { id: 'target_ash_max', name: '灰分的上限' },
        { id: 'target_sulfur_min', name: '硫分的下限' },
        { id: 'target_sulfur_max', name: '硫分的上限' },
        { id: 'target_volatile_min', name: '挥发分的下限' },
        { id: 'target_volatile_max', name: '挥发分的上限' },
        { id: 'target_glue_min', name: '粘结的下限' },
        { id: 'target_glue_max', name: '粘结的上限' }
    ];
    for (let item of mapping) {
        const input = document.getElementById(item.id);
        if (!input) continue;
        const val = input.value;
        if (val === "" || isNaN(parseFloat(val))) {
            missing.push(item.name);
        }
    }
    return missing;
}
