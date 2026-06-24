"""单元测试：达标判定与目标范围 — checkStatus() / targetBounds 初始值

从 test_status_and_bounds.py 精简而来（13 → 8 tests）。
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
# checkStatus() 测试
# ═══════════════════════════════════════════════════════════════

@pytest.mark.parametrize("value,type_name,bounds,expected,desc", [
    # 值在范围内应达标
    (5.0, "ash", {"ash": {"min": 0, "max": 11.0}}, True, "值在范围内应达标"),
    (0.0, "ash", {"ash": {"min": 0, "max": 11.0}}, True, "等于下限应达标"),
    (11.0, "ash", {"ash": {"min": 0, "max": 11.0}}, True, "等于上限应达标"),
    # 值低于下限应超标
    (4.99, "ash", {"ash": {"min": 5.0, "max": 11.0}}, False, "略低于下限应超标"),
    (0, "ash", {"ash": {"min": 5.0, "max": 11.0}}, False, "远低于下限应超标"),
    (-1, "ash", {"ash": {"min": 5.0, "max": 11.0}}, False, "负值低于下限应超标"),
    # 值高于上限应超标
    (10.01, "ash", {"ash": {"min": 0, "max": 10.0}}, False, "略高于上限应超标"),
    (100, "ash", {"ash": {"min": 0, "max": 10.0}}, False, "远高于上限应超标"),
    # 边界值包含性
    (0.5, "sulfur", {"sulfur": {"min": 0.5, "max": 1.5}}, True, "等于下限(硫分)应达标"),
    (1.5, "sulfur", {"sulfur": {"min": 0.5, "max": 1.5}}, True, "等于上限(硫分)应达标"),
])
def test_check_status_range_behavior(value, type_name, bounds, expected, desc):
    """checkStatus 范围判定行为（parametrize 合并 5 个原测试）"""
    import json
    bounds_json = json.dumps(bounds)
    result = _js1(f"""
        targetBounds = {bounds_json};
        report(checkStatus({value}, '{type_name}'));
    """)
    assert result == expected, f"{desc}：got {result}"


def test_four_standard_types():
    """四种标准指标类型均可正确判定达标/超标"""
    result = _js1("""
        targetBounds = {
            ash: {min: 0, max: 11},
            sulfur: {min: 0, max: 1.0},
            volatile: {min: 28, max: 34},
            glue: {min: 75, max: 100}
        };
        report([
            checkStatus(5, 'ash'),        // 达标
            checkStatus(0.5, 'sulfur'),   // 达标
            checkStatus(30, 'volatile'),  // 达标
            checkStatus(80, 'glue'),      // 达标
            checkStatus(15, 'ash'),       // 超标
            checkStatus(2.0, 'sulfur'),   // 超标
            checkStatus(20, 'volatile'),  // 超标
            checkStatus(50, 'glue'),      // 超标
        ]);
    """)
    assert result == [True, True, True, True, False, False, False, False]


# ═══════════════════════════════════════════════════════════════
# targetBounds 初始值测试
# ═══════════════════════════════════════════════════════════════

def test_initial_target_bounds_values():
    """初始化后的目标范围默认值"""
    result = _js1("""
        targetBounds = {
            ash: { min: 11, max: 12 },
            sulfur: { min: 1, max: 2 },
            volatile: { min: 28, max: 33 },
            glue: { min: 85, max: 100 }
        };
        report(_clone(targetBounds));
    """)
    assert result["ash"]["min"] == 11
    assert result["ash"]["max"] == 12
    assert result["sulfur"]["min"] == 1
    assert result["sulfur"]["max"] == 2
    assert result["volatile"]["min"] == 28
    assert result["volatile"]["max"] == 33
    assert result["glue"]["min"] == 85
    assert result["glue"]["max"] == 100


def test_target_bounds_structure_only_has_four_keys():
    """targetBounds 只包含 ash/sulfur/volatile/glue 四种指标"""
    result = _js1("""
        targetBounds = {
            ash: { min: 0, max: 11.0 },
            sulfur: { min: 0, max: 1.0 },
            volatile: { min: 28, max: 34 },
            glue: { min: 75, max: 100 }
        };
        report(Object.keys(targetBounds).sort());
    """)
    assert result == ["ash", "glue", "sulfur", "volatile"]


# ═══════════════════════════════════════════════════════════════
# fetchTargetBoundsFromInputs() 测试
# ═══════════════════════════════════════════════════════════════

def test_silent_true_no_alerts():
    """silent=true → 交换时不弹 alert（静默处理）"""
    result = _js1("""
        var origGetEl = document.getElementById;
        document.getElementById = function(id) { return null; };
        targetBounds = {ash:{min:0,max:0}, sulfur:{min:0,max:0}, volatile:{min:0,max:0}, glue:{min:0,max:0}};
        fetchTargetBoundsFromInputs(true);
        document.getElementById = origGetEl;
        report(_clone(targetBounds));
    """)
    assert result["ash"]["min"] == 0
    assert result["ash"]["max"] == 20   # ash max 默认 20
    assert result["sulfur"]["max"] == 5
    assert result["volatile"]["max"] == 50
    assert result["glue"]["max"] == 120


def test_fetch_target_bounds_with_missing_inputs():
    """输入框缺失或 silent=false 时的默认行为：min=0, max 按指标类型取默认值（2合1）

    空值→0 是 spec §五 明确要求的行为。
    """
    # 场景1: silent=false 且 min>max 时（mock 下不抛异常，值正确回落）
    result1 = _js1("""
        var origGetEl = document.getElementById;
        document.getElementById = function(id) { return null; };
        targetBounds = {ash:{min:0,max:0}, sulfur:{min:0,max:0}, volatile:{min:0,max:0}, glue:{min:0,max:0}};
        fetchTargetBoundsFromInputs(false);
        document.getElementById = origGetEl;
        report(_clone(targetBounds));
    """)
    assert result1["ash"]["max"] == 20

    # 场景2: 输入框缺失 → min 默认 0, max 按指标类型取不同默认值
    result2 = _js1("""
        var origGetEl = document.getElementById;
        document.getElementById = function(id) { return null; };
        targetBounds = {ash:{min:99,max:99}, sulfur:{min:99,max:99}, volatile:{min:99,max:99}, glue:{min:99,max:99}};
        fetchTargetBoundsFromInputs(true);
        document.getElementById = origGetEl;
        report(_clone(targetBounds));
    """)
    assert result2["ash"]["min"] == 0
    assert result2["ash"]["max"] == 20
    assert result2["sulfur"]["min"] == 0
    assert result2["sulfur"]["max"] == 5
    assert result2["volatile"]["min"] == 0
    assert result2["volatile"]["max"] == 50
    assert result2["glue"]["min"] == 0
    assert result2["glue"]["max"] == 120


def test_default_coals_against_default_targets():
    """默认煤种对默认目标范围的达标判定（实际总配比=10，标准加权平均）"""
    result = _js1("""
        targetBounds = {
            ash: { min: 11, max: 12 },
            sulfur: { min: 1, max: 2 },
            volatile: { min: 28, max: 33 },
            glue: { min: 85, max: 100 }
        };
        coals = getDefaultCoals();
        var avg = calculateHybridMetrics();
        report({
            ash: checkStatus(avg.ash, 'ash'),
            sulfur: checkStatus(avg.sulfur, 'sulfur'),
            volatile: checkStatus(avg.volatile, 'volatile'),
            glue: checkStatus(avg.glue, 'glue'),
            values: avg
        });
    """)
    status = result
    # avg（总配比=10）: ash=11.67, sulfur=1.44, volatile=33.16, glue=84.5
    assert status["ash"], "默认灰分 11.67 应在 [11, 12] 内 → 达标"
    assert status["sulfur"], "默认硫分 1.44 在 [1, 2] 内 → 达标"
    assert not status["volatile"], (
        "默认挥发分 33.16 超出上限 33 → 超标"
    )
    assert not status["glue"], (
        "默认粘结 84.5 低于下限 85 → 超标"
    )
