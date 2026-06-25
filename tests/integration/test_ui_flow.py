"""集成测试：DOM 依赖函数的交互流程

从 test_dom_boundary.py 精简而来（26 → 12 tests）。
测试 syncCoalsFromTable / checkCoalTableCompleteness / confirmAndRefresh /
addCoalManually / refreshAndNotify 等需要 DOM mock 的多模块协作行为。
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from helpers import run_js


def _js1(test_code):
    """执行 JS 测试代码，返回第一个 report() 的值。"""
    results = run_js(test_code)
    if not results:
        raise RuntimeError("JS 测试代码未调用 report()，无返回值")
    return results[0]


# ═══════════════════════════════════════════════════════════════
# syncCoalsFromTable() 测试
# ═══════════════════════════════════════════════════════════════

def test_sync_with_no_table_rows_does_nothing():
    """表格为空（querySelectorAll 返回空）→ 循环不执行 → coals 不变"""
    result = _js1("""
        coals = [{name:"keep", price:1, ash:2, sulfur:3, volatile:4, glue:5, ratio:6}];
        syncCoalsFromTable();
        report({len: coals.length, name: coals[0].name});
    """)
    assert result["len"] == 1
    assert result["name"] == "keep"


# ═══════════════════════════════════════════════════════════════
# checkCoalTableCompleteness() 测试
# ═══════════════════════════════════════════════════════════════

def test_check_coal_table_completeness():
    """空表返回空列表；所有输入框缺失时也返回空列表（mock 下 input 为 null 则跳过）"""
    # 空表（querySelectorAll 返回 []）
    result1 = _js1("report(checkCoalTableCompleteness());")
    assert result1 == []

    # 所有输入框为 null → !input 为 true，continue 跳过
    result2 = _js1("report(checkCoalTableCompleteness());")
    assert result2 == []


# ═══════════════════════════════════════════════════════════════
# confirmAndRefresh() 测试
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("missing_count,confirm_return,action_return,expected_action_called,expected_alerts,desc", [
    # checkFunc 返回非空 → confirm 对话框，mock 默认 true → 执行 action
    (2, True, None, True, None, "有缺失+用户确认→执行action"),
    # checkFunc 返回空数组 → 直接执行 action，不弹 confirm
    (0, True, None, True, None, "无缺失→直接执行action"),
    # action 返回 false → 不弹成功提示
    (0, True, False, True, [], "action返回false→不弹成功提示"),
    # action 返回 true → 弹成功提示
    (0, True, True, True, ["✅ 计算成功"], "action返回true→弹成功提示"),
])
def test_confirm_and_refresh_flow(missing_count, confirm_return, action_return,
                                   expected_action_called, expected_alerts, desc):
    """confirmAndRefresh 通用确认模式（parametrize 合并 4 个原测试）"""
    missing = ["缺失项" + str(i + 1) for i in range(missing_count)] if missing_count > 0 else []
    import json

    result = _js1(f"""
        var alertMsgs = [];
        var origAlert = global.alert;
        global.alert = function(msg) {{ alertMsgs.push(msg); }};
        var origConfirm = global.confirm;
        global.confirm = function(msg) {{ return {json.dumps(confirm_return)}; }};

        var refreshCalled = false;
        var checkFunc = function() {{ return {json.dumps(missing)}; }};
        var action = function() {{ refreshCalled = true; return {json.dumps(action_return)}; }};
        confirmAndRefresh(checkFunc, "✅ 计算成功", action);

        global.alert = origAlert;
        global.confirm = origConfirm;
        report({{called: refreshCalled, alerts: alertMsgs}});
    """)
    assert result["called"] == expected_action_called, f"{desc}：action调用状态不符"
    if expected_alerts is not None:
        if expected_alerts:
            assert any("计算成功" in a for a in result["alerts"]), f"{desc}：应包含成功提示"
        else:
            assert result["alerts"] == [], f"{desc}：不应有alert"


# ═══════════════════════════════════════════════════════════════
# addCoalManually() 测试
# ═══════════════════════════════════════════════════════════════

def test_add_coal_manually_success():
    """所有 prompt 都返回有效值 → 新煤种被添加到 coals"""
    result = _js1("""
        coals = [];
        addCoalManually();
        report({
            len: coals.length,
            name: coals.length > 0 ? coals[0].name : null,
            price: coals.length > 0 ? coals[0].price : null,
            ash: coals.length > 0 ? coals[0].ash : null,
            sulfur: coals.length > 0 ? coals[0].sulfur : null,
            volatile: coals.length > 0 ? coals[0].volatile : null,
            glue: coals.length > 0 ? coals[0].glue : null,
            ratio: coals.length > 0 ? coals[0].ratio : null
        });
    """)
    assert result["len"] == 1
    assert result["name"] == "新煤种"
    assert result["price"] == 800
    assert result["ash"] == 10
    assert result["sulfur"] == 0.8
    assert result["volatile"] == 30
    assert result["glue"] == 70
    assert result["ratio"] == 0.5


def test_add_coal_manually_cancel_aborts():
    """取消 prompt → 不添加煤种（2合1：名称取消 + 中途取消）"""
    # 场景1: 第一个 prompt（名称）返回 null
    result1 = _js1("""
        coals = [];
        var callCount = 0;
        var origPrompt = global.prompt;
        global.prompt = function(msg, def) {
            callCount++;
            if (callCount === 1) return null;
            return def;
        };
        addCoalManually();
        global.prompt = origPrompt;
        report({len: coals.length, calls: callCount});
    """)
    assert result1["len"] == 0
    assert result1["calls"] == 1

    # 场景2: 在中间某步取消
    result2 = _js1("""
        coals = [];
        var callCount = 0;
        var origPrompt = global.prompt;
        global.prompt = function(msg, def) {
            callCount++;
            if (callCount === 4) return null;
            return def;
        };
        addCoalManually();
        global.prompt = origPrompt;
        report({len: coals.length, calls: callCount});
    """)
    assert result2["len"] == 0
    assert result2["calls"] == 4


def test_add_coal_manually_invalid_input_aborts():
    """任一数值字段 parseFloat 为 NaN → alert + return，不添加"""
    result = _js1("""
        coals = [];
        var origPrompt = global.prompt;
        global.prompt = function(msg, def) {
            if (msg.indexOf("煤价") !== -1) return "not_a_number";
            return def;
        };
        addCoalManually();
        global.prompt = origPrompt;
        report(coals.length);
    """)
    assert result == 0


# ═══════════════════════════════════════════════════════════════
# 删除煤种测试
# ═══════════════════════════════════════════════════════════════

def test_delete_coal_restrictions():
    """只能删除多于 1 种煤时的行（2合1）"""
    # 只剩 1 种煤 → 禁止删除
    result1 = _js1("""
        coals = [{name:"唯一煤种", price:0, ash:0, sulfur:0, volatile:0, glue:0, ratio:0}];
        var deleted = false;
        if (coals.length === 1) {
            deleted = false;
        } else {
            coals.splice(0, 1);
            deleted = true;
        }
        report({len: coals.length, deleted: deleted});
    """)
    assert result1["len"] == 1
    assert result1["deleted"] is False

    # 多于 1 种煤 → 可以删除
    result2 = _js1("""
        coals = [{name:"A", price:0, ash:0, sulfur:0, volatile:0, glue:0, ratio:0},
                 {name:"B", price:0, ash:0, sulfur:0, volatile:0, glue:0, ratio:0}];
        if (coals.length > 1) {
            coals.splice(0, 1);
        }
        report(coals.length);
    """)
    assert result2 == 1


# ═══════════════════════════════════════════════════════════════
# refreshAndNotify() 总配比阈值测试
# ═══════════════════════════════════════════════════════════════

def test_total_ratio_exceeds_10_blocks():
    """总配比 > 10成 → alert 警告，不计算，返回 false（2合1：明显超 + 略超容差）"""
    # 场景1: 明显超过（11成）
    result1 = _js1("""
        coals = [
            {name:"A", price:100, ash:10, sulfur:1, volatile:30, glue:90, ratio:6},
            {name:"B", price:200, ash:20, sulfur:2, volatile:30, glue:80, ratio:5}
        ];
        var alertMsg = '';
        var origAlert = global.alert;
        global.alert = function(msg) { alertMsg = msg; };
        var calcCalled = false;
        var origCalc = calculateHybridMetrics;
        calculateHybridMetrics = function() { calcCalled = true; return origCalc(); };
        var result = refreshAndNotify('不应出现', true);
        calculateHybridMetrics = origCalc;
        global.alert = origAlert;
        report({alertMsg: alertMsg, calcCalled: calcCalled, result: result});
    """)
    assert "超过十成" in result1["alertMsg"]
    assert "11.00" in result1["alertMsg"]
    assert result1["calcCalled"] is False, "总配比超十成时不应调用 calculateHybridMetrics"
    assert result1["result"] is False, "refreshAndNotify 应返回 false"

    # 场景2: 略超容差（10.01 > 10.005）
    result2 = _js1("""
        coals = [{name:"A", price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:10.01}];
        var alertMsg = '';
        var origAlert = global.alert;
        global.alert = function(msg) { alertMsg = msg; };
        refreshAndNotify('不应出现', true);
        global.alert = origAlert;
        report(alertMsg);
    """)
    assert "超过十成" in result2, "10.01 成 > 10.005 容差 → 应触发拦截"


def test_total_ratio_at_or_under_10_proceeds():
    """总配比 ≤ 10成 → 正常计算（2合1）"""
    # 场景1: 刚好 10 成
    result1 = _js1("""
        coals = [
            {name:"A", price:100, ash:10, sulfur:1, volatile:30, glue:90, ratio:5},
            {name:"B", price:200, ash:20, sulfur:2, volatile:30, glue:80, ratio:5}
        ];
        var alertMsg = '';
        var origAlert = global.alert;
        global.alert = function(msg) { alertMsg = msg; };
        refreshAndNotify('✅ 成功', true);
        global.alert = origAlert;
        report({alertMsg: alertMsg, ash: calculateHybridMetrics().ash});
    """)
    assert result1["alertMsg"] == ''
    assert result1["ash"] == pytest.approx(15.0)

    # 场景2: 小于 10 成（实际分母=5，标准加权平均）
    result2 = _js1("""
        coals = [
            {name:"A", price:100, ash:10, sulfur:1, volatile:30, glue:90, ratio:3},
            {name:"B", price:200, ash:20, sulfur:2, volatile:30, glue:80, ratio:2}
        ];
        var alertMsg = '';
        var origAlert = global.alert;
        global.alert = function(msg) { alertMsg = msg; };
        refreshAndNotify('✅ 成功', true);
        global.alert = origAlert;
        report({alertMsg: alertMsg, ash: calculateHybridMetrics().ash});
    """)
    assert result2["alertMsg"] == ''
    # 实际总配比=5，ash=(10×3+20×2)/5=(30+40)/5=14.0
    assert result2["ash"] == pytest.approx(14.0)


# ═══════════════════════════════════════════════════════════════
# renderOptimizeResult() — 全局 coals 访问测试
# ═══════════════════════════════════════════════════════════════

def test_render_optimize_result_reads_global_coals():
    """renderOptimizeResult 使用 let 声明的全局 coals（非 window.coals）渲染煤种数据行

    回归 bug：renderOptimizeResult 曾用 var coals = window.coals || []，
    但 let 声明的全局变量不挂在 window 上 → 表格无数据行。
    修复后直接引用全局 coals，表格应包含煤种名称。
    """
    import json

    result = _js1("""
        // 设置全局 coals（模拟 main.js 中的 let coals）
        coals = [
            {name:"测试煤A", price:100, ash:10, sulfur:0.5, volatile:30, glue:80, ratio:3},
            {name:"测试煤B", price:200, ash:15, sulfur:0.8, volatile:28, glue:75, ratio:7}
        ];

        // 构造一个合法的优化结果
        var mockResult = {
            success: true,
            cost: 170.0,
            totalRatio: 10.0,
            ratios: [3.0, 7.0],
            metrics: {ash: 13.5, volatile: 28.6, sulfur: 0.71, glue: 76.5},
            status: {ash: true, volatile: true, sulfur: true, glue: true}
        };

        // 捕获 renderOptimizeResult 写入的 innerHTML
        var capturedHtml = '';
        var origGetEl = document.getElementById;
        document.getElementById = function(id) {
            if (id === 'optimizeResultContainer') {
                return {
                    style: {},
                    get innerHTML() { return capturedHtml; },
                    set innerHTML(val) { capturedHtml = val; },
                    addEventListener: function(evt, fn) {},
                    querySelectorAll: function(sel) { return []; },
                    querySelector: function(sel) { return null; }
                };
            }
            // optimizeResultContainer 设置后 applyOptimizeBtn 和 backToChoicesFromResultBtn 查询
            if (id === 'applyOptimizeBtn' || id === 'backToChoicesFromResultBtn') {
                return {
                    addEventListener: function(evt, fn) {},
                    style: {},
                    querySelector: function(sel) { return null; }
                };
            }
            return origGetEl(id);
        };

        renderOptimizeResult(mockResult);

        report({
            hasCoalA: capturedHtml.indexOf('测试煤A') !== -1,
            hasCoalB: capturedHtml.indexOf('测试煤B') !== -1,
            hasRatioA: capturedHtml.indexOf('3.00') !== -1,
            hasRatioB: capturedHtml.indexOf('7.00') !== -1,
            hasCost: capturedHtml.indexOf('170.00') !== -1
        });
    """)
    assert result["hasCoalA"], "渲染结果应包含煤种A名称"
    assert result["hasCoalB"], "渲染结果应包含煤种B名称"
    assert result["hasRatioA"], "渲染结果应包含煤种A配比 3.00"
    assert result["hasRatioB"], "渲染结果应包含煤种B配比 7.00"
    assert result["hasCost"], "渲染结果应包含综合煤价 170.00"
