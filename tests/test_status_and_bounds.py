"""特征测试：达标判定与目标范围 — checkStatus() / targetBounds / fetchTargetBoundsFromInputs()

锁住当前达标判定逻辑、目标范围默认值、以及从DOM读取范围时的所有边界行为。
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from helpers import run_js


class TestCheckStatus(unittest.TestCase):
    """锁住 checkStatus(value, type) 的现状行为"""

    # ── 正常路径 ──

    def test_value_within_range_returns_true(self):
        """现状：min ≤ value ≤ max → true（达标）"""
        result = run_js("""
            targetBounds = {ash: {min: 0, max: 11.0}};
            report(checkStatus(5.0, 'ash'));
            report(checkStatus(0.0, 'ash'));
            report(checkStatus(11.0, 'ash'));
        """)
        self.assertTrue(result[0])   # 5.0 在 [0, 11] 内
        self.assertTrue(result[1])   # 0.0 刚好在下边界 → 达标
        self.assertTrue(result[2])   # 11.0 刚好在上边界 → 达标

    def test_value_below_min_returns_false(self):
        """现状：value < min → false（超标）"""
        results = run_js("""
            targetBounds = {ash: {min: 5.0, max: 11.0}};
            report(checkStatus(4.99, 'ash'));
            report(checkStatus(0, 'ash'));
            report(checkStatus(-1, 'ash'));
        """)
        self.assertFalse(results[0])
        self.assertFalse(results[1])
        self.assertFalse(results[2])

    def test_value_above_max_returns_false(self):
        """现状：value > max → false（超标）"""
        results = run_js("""
            targetBounds = {ash: {min: 0, max: 10.0}};
            report(checkStatus(10.01, 'ash'));
            report(checkStatus(100, 'ash'));
        """)
        self.assertFalse(results[0])
        self.assertFalse(results[1])

    def test_boundary_values_inclusive(self):
        """现状：边界值是包含的（≤ 和 ≥），恰好等于 min 或 max 均返回 true"""
        results = run_js("""
            targetBounds = {sulfur: {min: 0.5, max: 1.5}};
            report(checkStatus(0.5, 'sulfur'));
            report(checkStatus(1.5, 'sulfur'));
        """)
        self.assertTrue(results[0])
        self.assertTrue(results[1])

    # ── 未知类型 / 缺失 bounds ──

    def test_unknown_type_returns_false__现状(self):
        """现状：传入未在 targetBounds 中定义的类型 → !bounds → false"""
        results = run_js("""
            targetBounds = {ash: {min: 0, max: 10}};
            report(checkStatus(5, 'unknown_type'));
            report(checkStatus(5, ''));
            report(checkStatus(5, null));
        """)
        self.assertFalse(results[0])
        self.assertFalse(results[1])
        self.assertFalse(results[2])

    def test_nullish_bounds_returns_false__现状(self):
        """现状：bounds 对象存在但 min/max 为 undefined → 比较结果依赖 JS 语义

        undefined >= undefined → false, undefined <= undefined → false
        所以任何值对比 undefined 边界都返回 false。
        """
        results = run_js("""
            targetBounds = {ash: {min: undefined, max: undefined}};
            report(checkStatus(0, 'ash'));
            report(checkStatus(100, 'ash'));
        """)
        self.assertFalse(results[0])
        self.assertFalse(results[1])

    # ── 不同指标类型 ──

    def test_four_standard_types(self):
        """现状：四种标准指标类型均可正确判定"""
        results = run_js("""
            targetBounds = {
                ash: {min: 0, max: 11},
                sulfur: {min: 0, max: 1.0},
                volatile: {min: 28, max: 34},
                glue: {min: 75, max: 100}
            };
            report(checkStatus(5, 'ash'));        // 达标
            report(checkStatus(0.5, 'sulfur'));   // 达标
            report(checkStatus(30, 'volatile'));  // 达标
            report(checkStatus(80, 'glue'));      // 达标
            report(checkStatus(15, 'ash'));       // 超标
            report(checkStatus(2.0, 'sulfur'));   // 超标
            report(checkStatus(20, 'volatile'));  // 超标
            report(checkStatus(50, 'glue'));      // 超标
        """)
        self.assertTrue(results[0])
        self.assertTrue(results[1])
        self.assertTrue(results[2])
        self.assertTrue(results[3])
        self.assertFalse(results[4])
        self.assertFalse(results[5])
        self.assertFalse(results[6])
        self.assertFalse(results[7])


class TestTargetBoundsInitial(unittest.TestCase):
    """锁住 targetBounds 初始默认值"""

    def test_initial_target_bounds_values(self):
        """现状：初始化后的目标范围默认值"""
        results = run_js("""
            targetBounds = {
                ash: { min: 0, max: 11.0 },
                sulfur: { min: 0, max: 1.0 },
                volatile: { min: 28, max: 34 },
                glue: { min: 75, max: 100 }
            };
            report(_clone(targetBounds));
        """)
        bounds = results[0]
        self.assertEqual(bounds["ash"]["min"], 0)
        self.assertEqual(bounds["ash"]["max"], 11.0)
        self.assertEqual(bounds["sulfur"]["min"], 0)
        self.assertEqual(bounds["sulfur"]["max"], 1.0)
        self.assertEqual(bounds["volatile"]["min"], 28)
        self.assertEqual(bounds["volatile"]["max"], 34)
        self.assertEqual(bounds["glue"]["min"], 75)
        self.assertEqual(bounds["glue"]["max"], 100)

    def test_target_bounds_structure_only_has_four_keys(self):
        """现状：targetBounds 只包含 ash/sulfur/volatile/glue 四种指标"""
        results = run_js("""
            targetBounds = {
                ash: { min: 0, max: 11.0 },
                sulfur: { min: 0, max: 1.0 },
                volatile: { min: 28, max: 34 },
                glue: { min: 75, max: 100 }
            };
            report(Object.keys(targetBounds).sort());
        """)
        self.assertEqual(results[0], ["ash", "glue", "sulfur", "volatile"])


class TestFetchTargetBoundsFromInputs(unittest.TestCase):
    """锁住 fetchTargetBoundsFromInputs(silent) 的现状行为

    该函数从 DOM 输入框读取目标范围，处理空值/NaN/颠倒，
    更新 targetBounds 全局变量和输入框 value。

    注意：测试中需要临时替换 getElementById 来模拟特定输入值。
    """

    def test_silent_true_no_alerts(self):
        """现状：silent=true → 交换时不弹 alert（静默处理）"""
        results = run_js("""
            // 覆盖 getElementById 让所有 input 返回 null（模拟输入框缺失）
            var origGetEl = document.getElementById;
            document.getElementById = function(id) { return null; };
            targetBounds = {ash:{min:0,max:0}, sulfur:{min:0,max:0}, volatile:{min:0,max:0}, glue:{min:0,max:0}};
            fetchTargetBoundsFromInputs(true);
            document.getElementById = origGetEl;
            report(_clone(targetBounds));
        """)
        bounds = results[0]
        # 输入框不存在 → parseFloat(null)=NaN → 全部用默认值
        self.assertEqual(bounds["ash"]["min"], 0)
        self.assertEqual(bounds["ash"]["max"], 20)   # ash max 默认 20
        self.assertEqual(bounds["sulfur"]["max"], 5)
        self.assertEqual(bounds["volatile"]["max"], 50)
        self.assertEqual(bounds["glue"]["max"], 120)

    def test_silent_false_would_alert_on_swap__现状(self):
        """现状：silent=false 且 min>max 时会调用 alert() —— mock 下不抛异常"""
        results = run_js("""
            // 覆盖 getElementById 让所有 input 返回 null
            var origGetEl = document.getElementById;
            document.getElementById = function(id) { return null; };
            targetBounds = {ash:{min:0,max:0}, sulfur:{min:0,max:0}, volatile:{min:0,max:0}, glue:{min:0,max:0}};
            fetchTargetBoundsFromInputs(false);
            document.getElementById = origGetEl;
            report(_clone(targetBounds));
        """)
        bounds = results[0]
        self.assertEqual(bounds["ash"]["max"], 20)

    def test_missing_inputs_default_min_zero_max_type_specific__现状(self):
        """现状：输入框缺失 → min 默认 0，max 按指标类型取不同默认值"""
        results = run_js("""
            // 覆盖 getElementById 让所有 input 返回 null
            var origGetEl = document.getElementById;
            document.getElementById = function(id) { return null; };
            targetBounds = {ash:{min:99,max:99}, sulfur:{min:99,max:99}, volatile:{min:99,max:99}, glue:{min:99,max:99}};
            fetchTargetBoundsFromInputs(true);
            document.getElementById = origGetEl;
            report(_clone(targetBounds));
        """)
        bounds = results[0]
        self.assertEqual(bounds["ash"]["min"], 0)
        self.assertEqual(bounds["ash"]["max"], 20)
        self.assertEqual(bounds["sulfur"]["min"], 0)
        self.assertEqual(bounds["sulfur"]["max"], 5)
        self.assertEqual(bounds["volatile"]["min"], 0)
        self.assertEqual(bounds["volatile"]["max"], 50)
        self.assertEqual(bounds["glue"]["min"], 0)
        self.assertEqual(bounds["glue"]["max"], 120)


class TestDefaultCoalsStatusWithInitialBounds(unittest.TestCase):
    """锁住：用默认 8 种煤 + 默认目标范围 → 各指标的达标/超标状态"""

    def test_default_coals_against_default_targets(self):
        """默认煤种对默认目标范围的达标判定（分母=1.0）"""
        results = run_js("""
            targetBounds = {
                ash: { min: 0, max: 11.0 },
                sulfur: { min: 0, max: 1.0 },
                volatile: { min: 28, max: 34 },
                glue: { min: 75, max: 100 }
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
        status = results[0]
        # avg: ash=8.385, sulfur=1.347, volatile=25.12, glue=62.8
        self.assertTrue(status["ash"], "默认灰分 8.385 应在 [0, 11] 内 → 达标")
        self.assertFalse(status["sulfur"], "默认硫分 1.347 超出上限 1.0 → 超标")
        self.assertFalse(status["volatile"],
            "默认挥发分 25.12 低于下限 28 → 超标（总配比 8 成，不足十成）")
        self.assertFalse(status["glue"],
            "默认粘结 62.8 低于下限 75 → 超标（总配比 8 成，不足十成）")


if __name__ == '__main__':
    unittest.main()
