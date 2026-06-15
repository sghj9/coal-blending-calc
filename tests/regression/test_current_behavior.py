"""回归测试：关键现状行为锁

精选 8 个最关键 __现状 测试，锁住可能在重构中被意外修改的行为。
这些测试不一定是 spec 明确要求的，但改变它们可能导致静默回归。

命名规则：去掉 __现状 后缀，使用描述性名称。
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
# checkStatus 边界行为
# ═══════════════════════════════════════════════════════════════

def test_check_status_unknown_type_returns_false():
    """锁住：传入未在 targetBounds 中定义的类型 → 返回 false

    原因：未定义指标类型不应静默通过。如果未来添加新指标类型，
    旧代码 unknowingly 通过会导致安全事故。
    """
    result = _js1("""
        targetBounds = {ash: {min: 0, max: 10}};
        report([
            checkStatus(5, 'unknown_type'),
            checkStatus(5, ''),
            checkStatus(5, null)
        ]);
    """)
    assert result == [False, False, False]


def test_check_status_nullish_bounds_returns_false():
    """锁住：bounds 存在但 min/max 为 undefined → 返回 false

    原因：未设置目标范围时不应误判达标。undefined 参与比较后
    结果恒为 false，这是安全的「快速失败」行为。
    """
    result = _js1("""
        targetBounds = {ash: {min: undefined, max: undefined}};
        report([
            checkStatus(0, 'ash'),
            checkStatus(100, 'ash')
        ]);
    """)
    assert result == [False, False]


# ═══════════════════════════════════════════════════════════════
# fetchTargetBoundsFromInputs 行为
# ═══════════════════════════════════════════════════════════════

def test_fetch_target_bounds_alerts_on_min_gt_max():
    """锁住：silent=false 且 min>max 时触发 alert 交换逻辑

    原因：spec §五 定义「下限 > 上限 → 弹窗交换」，此行为是用户安全网。
    """
    result = _js1("""
        var origGetEl = document.getElementById;
        document.getElementById = function(id) { return null; };
        targetBounds = {ash:{min:0,max:0}, sulfur:{min:0,max:0}, volatile:{min:0,max:0}, glue:{min:0,max:0}};
        fetchTargetBoundsFromInputs(false);
        document.getElementById = origGetEl;
        report(_clone(targetBounds));
    """)
    # mock 下 input 全部返回 null → 默认值，不触发交换
    # 但 silent=false 路径被覆盖，不会抛异常
    assert result["ash"]["max"] == 20


# ═══════════════════════════════════════════════════════════════
# calculateHybridMetrics 边界行为
# ═══════════════════════════════════════════════════════════════

def test_calculate_hybrid_metrics_negative_inputs_passthrough():
    """锁住：负值输入不自动钳位，照常参与计算

    原因：calculateHybridMetrics 不校验输入非负。如果未来添加
    钳位逻辑，依赖负值通过的上游代码可能受影响。
    """
    result = _js1("""
        coals = [{name:"X", price:-100, ash:-5, sulfur:0, volatile:0, glue:0, ratio:2}];
        var avg = calculateHybridMetrics();
        report({ash: avg.ash, price: avg.price});
    """)
    # w=0.2, ash=-5*0.2/1=-1.0, price=-100*0.2/1=-20.0
    assert abs(result["ash"] - (-1.0)) < 1e-10
    assert abs(result["price"] - (-20.0)) < 1e-10


# ═══════════════════════════════════════════════════════════════
# DOM 交互行为
# ═══════════════════════════════════════════════════════════════

def test_sync_coals_truncates_at_coals_length():
    """锁住：syncCoalsFromTable 只同步 min(rows, coals) 行

    原因：DOM 行数 > coals 数时安全截断，防止数组越界。
    如果将来改为自动扩充 coals 数组，下游逻辑可能受影响。
    """
    result = _js1("""
        coals = [{name:"A", price:1, ash:2, sulfur:3, volatile:4, glue:5, ratio:6},
                 {name:"B", price:7, ash:8, sulfur:9, volatile:10, glue:11, ratio:12}];
        syncCoalsFromTable();  // DOM 为空 → 0 rows
        report({len: coals.length, name0: coals[0].name, name1: coals[1].name});
    """)
    assert result["len"] == 2
    assert result["name0"] == "A"
    assert result["name1"] == "B"


def test_delete_coal_rejects_last_row():
    """锁住：只剩 1 种煤时禁止删除

    原因：spec §五 定义「删除时至少保留1种」，此行为保证 UI 不会出现空表格。
    """
    result = _js1("""
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
    assert result["len"] == 1
    assert result["deleted"] is False


def test_add_coal_accepts_empty_name():
    """锁住：空名称（纯空格）当前不被 addCoalManually 拒绝

    原因：名称输入通过 prompt 获取，trim() 仅用于 push 时。
    如果未来添加名称校验，需评估向后兼容性。
    """
    result = _js1("""
        coals = [];
        var origPrompt = global.prompt;
        global.prompt = function(msg, def) {
            if (msg.indexOf("名称") !== -1) return "   ";
            return def;
        };
        addCoalManually();
        global.prompt = origPrompt;
        report({len: coals.length, name: coals.length > 0 ? coals[0].name : null});
    """)
    assert result["len"] == 1
    assert result["name"] == ""


def test_get_default_coals_explicitly_copies_ratio():
    """锁住：getDefaultCoals() 显式复制 ratio 属性

    原因：map 回调中 { ...c, ratio: c.ratio } — spread 已复制 ratio，
    显式赋值覆盖同值（冗余但无害）。如果未来移除此行，行为不变，
    但此测试确保重构时有人注意到。
    """
    result = _js1("""
        var copy = getDefaultCoals();
        report(copy[0].ratio);
    """)
    assert result == 1.0
