"""特征测试：核心计算逻辑 — calculateHybridMetrics()

锁住当前混合煤指标加权计算的全部行为。
关键现状：分母固定为 1.0（隐含十成满配），不再除以煤种数量。
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from helpers import run_js


class TestCalculateHybridMetrics(unittest.TestCase):
    """锁住 calculateHybridMetrics() 的全部现状行为"""

    # ── 辅助方法 ──

    @staticmethod
    def _avg(coals_js):
        """以指定 coals 数组调用 calculateHybridMetrics()，返回结果对象。"""
        results = run_js(f"""
            coals = {coals_js};
            report(calculateHybridMetrics());
        """)
        return results[0]

    # ══════════════════════════════════════════════
    # 正常计算路径
    # ══════════════════════════════════════════════

    def test_basic_two_coals_matches_spec_example(self):
        """规格文档示例 — 两种煤，分母固定 1.0（隐含十成满配）"""
        avg = self._avg("""
            [{name:"A", price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:2},
             {name:"B", price:0, ash:20, sulfur:0, volatile:0, glue:0, ratio:3}]
        """)
        # 权重A=2*0.1=0.2, B=3*0.1=0.3
        # 混合灰分=10*0.2+20*0.3=2+6=8.0（分母=1.0，剩余5成由无属性煤种填补）
        self.assertAlmostEqual(avg["ash"], 8.0)
        self.assertEqual(avg["sulfur"], 0.0)

    def test_single_coal_weighted_value_divided_by_one(self):
        """现状：单煤种 → 指标×权重÷1 = 指标×权重"""
        avg = self._avg("""
            [{name:"神华", price:650, ash:10, sulfur:2, volatile:30, glue:80, ratio:5}]
        """)
        # w=0.5, ash=10*0.5/1=5, sulfur=2*0.5/1=1, volatile=30*0.5/1=15
        # glue=80*0.5/1=40, price=650*0.5/1=325
        self.assertAlmostEqual(avg["ash"], 5.0)
        self.assertAlmostEqual(avg["sulfur"], 1.0)
        self.assertAlmostEqual(avg["volatile"], 15.0)
        self.assertAlmostEqual(avg["glue"], 40.0)
        self.assertAlmostEqual(avg["price"], 325.0)

    def test_weight_is_ratio_times_0_1(self):
        """现状：权重 = 配比(成) × 0.1"""
        avg = self._avg("""
            [{name:"X", price:0, ash:100, sulfur:0, volatile:0, glue:0, ratio:10}]
        """)
        # w=10*0.1=1.0, ash=100*1.0/1=100
        self.assertAlmostEqual(avg["ash"], 100.0)

    def test_three_coals_with_mixed_ratios(self):
        """三种煤不同配比的混合计算（分母=1.0）"""
        avg = self._avg("""
            [{name:"A", price:100, ash:10, sulfur:1, volatile:30, glue:90, ratio:4},
             {name:"B", price:200, ash:20, sulfur:2, volatile:20, glue:80, ratio:6},
             {name:"C", price:300, ash:30, sulfur:0, volatile:25, glue:70, ratio:0}]
        """)
        # A w=0.4, B w=0.6, C w=0
        # ash: 10*0.4+20*0.6+30*0 = 4+12+0 = 16.0
        # sulfur: 1*0.4+2*0.6+0*0 = 0.4+1.2 = 1.6
        # volatile: 30*0.4+20*0.6+25*0 = 12+12 = 24.0
        # glue: 90*0.4+80*0.6+70*0 = 36+48 = 84.0
        # price: 100*0.4+200*0.6+300*0 = 40+120 = 160.0
        self.assertAlmostEqual(avg["ash"], 16.0)
        self.assertAlmostEqual(avg["sulfur"], 1.6)
        self.assertAlmostEqual(avg["volatile"], 24.0)
        self.assertAlmostEqual(avg["glue"], 84.0)
        self.assertAlmostEqual(avg["price"], 160.0)

    def test_return_structure_always_five_keys(self):
        """现状：返回对象固定包含 ash/sulfur/volatile/glue/price 五个键"""
        avg = self._avg("""
            [{name:"X", price:0, ash:0, sulfur:0, volatile:0, glue:0, ratio:1}]
        """)
        self.assertEqual(set(avg.keys()), {"ash", "sulfur", "volatile", "glue", "price"})

    def test_default_eight_coals_exact_result(self):
        """8 种默认煤种的计算结果（精确值，分母=1.0）"""
        avg = self._avg("getDefaultCoals()")
        self.assertAlmostEqual(avg["ash"], 8.385, places=6)
        self.assertAlmostEqual(avg["sulfur"], 1.347, places=6)
        self.assertAlmostEqual(avg["volatile"], 25.12, places=6)
        self.assertAlmostEqual(avg["glue"], 62.8, places=6)
        self.assertAlmostEqual(avg["price"], 690.3, places=6)

    # ══════════════════════════════════════════════
    # 分母=1.0 （隐含十成满配）的行为特征
    # ══════════════════════════════════════════════

    def test_denominator_is_fixed_one_not_coal_count(self):
        """分母固定为 1.0：两种煤总配比不同但指标相同 → 结果与配比成比例

        配比(1,1): ash=10*0.1+20*0.1=1+2=3.0
        配比(5,5): ash=10*0.5+20*0.5=5+10=15.0
        若分母=煤种数量，两者比例应为 1:5，即 3.0 vs 15.0
        若分母=总权重，配比(5,5)结果=(5+10)/1.0=15.0 仍相同（总权重=1.0时）
        """
        avg1 = self._avg("""
            [{name:"A", price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:1},
             {name:"B", price:0, ash:20, sulfur:0, volatile:0, glue:0, ratio:1}]
        """)
        avg2 = self._avg("""
            [{name:"A", price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:5},
             {name:"B", price:0, ash:20, sulfur:0, volatile:0, glue:0, ratio:5}]
        """)
        self.assertAlmostEqual(avg1["ash"], 3.0)
        self.assertAlmostEqual(avg2["ash"], 15.0)
        # 验证结果与配比成比例（5倍配比 → 5倍结果）
        self.assertAlmostEqual(avg2["ash"], avg1["ash"] * 5.0)

    # ══════════════════════════════════════════════
    # 空值/null/undefined 处理
    # ══════════════════════════════════════════════

    def test_null_ratio_treated_as_zero__现状(self):
        """现状：配比为 null → c.ratio || 0 → 权重=0"""
        avg = self._avg("""
            [{name:"X", price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:null}]
        """)
        self.assertEqual(avg["ash"], 0.0)

    def test_undefined_ratio_treated_as_zero__现状(self):
        """现状：缺少配比属性 → undefined → c.ratio || 0 → 权重=0"""
        avg = self._avg("""
            [{name:"X", price:0, ash:10, sulfur:0, volatile:0, glue:0}]
        """)
        self.assertEqual(avg["ash"], 0.0)

    def test_null_ash_treated_as_zero__现状(self):
        """现状：灰分为 null → c.ash || 0 → 当作 0 计算"""
        avg = self._avg("""
            [{name:"X", price:0, ash:null, sulfur:0, volatile:0, glue:0, ratio:5}]
        """)
        self.assertEqual(avg["ash"], 0.0)

    def test_zero_valued_fields_not_mistaken_for_falsy__现状(self):
        """现状：指标值为 0 时，c.ash || 0 仍为 0 —— 行为正确但依赖 || 运算符

        注意：|| 会把 0 当作 falsy，但由于 fallback 也是 0，结果恰好正确。
        如果未来 fallback 改为其他默认值，0 会被错误替换。
        """
        avg = self._avg("""
            [{name:"X", price:0, ash:0, sulfur:0, volatile:0, glue:0, ratio:5}]
        """)
        self.assertEqual(avg["ash"], 0.0)

    # ══════════════════════════════════════════════
    # 边界条件
    # ══════════════════════════════════════════════

    def test_empty_coals_array_returns_all_zeros(self):
        """现状：煤种数组为空 → 提前返回全零对象"""
        avg = self._avg("[]")
        self.assertEqual(avg["ash"], 0.0)
        self.assertEqual(avg["sulfur"], 0.0)
        self.assertEqual(avg["volatile"], 0.0)
        self.assertEqual(avg["glue"], 0.0)
        self.assertEqual(avg["price"], 0.0)

    def test_all_ratios_zero_returns_all_zeros(self):
        """现状：所有配比为 0 → 加权和全为 0 → 混合指标全 0"""
        avg = self._avg("""
            [{name:"A", price:100, ash:10, sulfur:1, volatile:30, glue:90, ratio:0},
             {name:"B", price:200, ash:20, sulfur:2, volatile:30, glue:80, ratio:0}]
        """)
        self.assertEqual(avg["ash"], 0.0)
        self.assertEqual(avg["sulfur"], 0.0)

    def test_negative_inputs_not_clamped__现状(self):
        """现状：calculateHybridMetrics 不校验输入非负——负值照常参与计算"""
        avg = self._avg("""
            [{name:"X", price:-100, ash:-5, sulfur:0, volatile:0, glue:0, ratio:2}]
        """)
        # w=0.2, ash=-5*0.2/1=-1.0, price=-100*0.2/1=-20.0
        self.assertAlmostEqual(avg["ash"], -1.0)
        self.assertAlmostEqual(avg["price"], -20.0)

    def test_large_ratio_values(self):
        """现状：大配比值的计算——无上限校验"""
        avg = self._avg("""
            [{name:"X", price:0, ash:50, sulfur:0, volatile:0, glue:0, ratio:999}]
        """)
        # w=999*0.1=99.9, ash=50*99.9/1=4995
        self.assertAlmostEqual(avg["ash"], 4995.0)

    def test_extreme_decimal_ratios(self):
        """现状：小数值配比（如 0.001 成）的浮点计算"""
        avg = self._avg("""
            [{name:"X", price:0, ash:100, sulfur:0, volatile:0, glue:0, ratio:0.001}]
        """)
        # w=0.0001, ash=100*0.0001/1=0.01
        self.assertAlmostEqual(avg["ash"], 0.01)

    def test_price_participates_in_same_weighted_average(self):
        """煤价与其他指标使用完全相同的加权公式（分母固定 1.0）"""
        avg = self._avg("""
            [{name:"A", price:100, ash:0, sulfur:0, volatile:0, glue:0, ratio:2},
             {name:"B", price:200, ash:0, sulfur:0, volatile:0, glue:0, ratio:4}]
        """)
        # A w=0.2, B w=0.4, price=100*0.2+200*0.4=20+80=100
        self.assertAlmostEqual(avg["price"], 100.0)

    def test_coal_with_zero_ratio_does_not_dilute_result(self):
        """配比=0 的煤种计不入分子（权重为0），分母固定 1.0 不会稀释结果

        相比旧公式（分母=煤种数量），零配比煤种不再稀释混合指标。
        """
        avg_with_zero = self._avg("""
            [{name:"A", price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:5},
             {name:"B", price:0, ash:0, sulfur:0, volatile:0, glue:0, ratio:0}]
        """)
        # A w=0.5, B w=0, 分母=1.0
        # ash = 10*0.5 + 0*0 = 5.0
        self.assertAlmostEqual(avg_with_zero["ash"], 5.0)

        # 如果没有 B，结果应该相同
        avg_without_zero = self._avg("""
            [{name:"A", price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:5}]
        """)
        self.assertAlmostEqual(avg_without_zero["ash"], 5.0)
        # 加不加零配比煤种，结果一致
        self.assertEqual(avg_with_zero["ash"], avg_without_zero["ash"])


if __name__ == '__main__':
    unittest.main()
