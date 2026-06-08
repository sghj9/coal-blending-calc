"""特征测试：核心计算逻辑 — calculateHybridMetrics()

锁住当前混合煤指标加权计算的全部行为。
关键现状：分母为「煤种数量」而非「总权重」。
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
        """现状：规格文档示例 — 两种煤，分母=煤种数量(2)"""
        avg = self._avg("""
            [{name:"A", price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:2},
             {name:"B", price:0, ash:20, sulfur:0, volatile:0, glue:0, ratio:3}]
        """)
        # 权重A=2*0.1=0.2, B=3*0.1=0.3
        # 加权和=10*0.2+20*0.3=2+6=8, 混合灰分=8/2=4.0
        self.assertAlmostEqual(avg["ash"], 4.0)
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
        """现状：三种煤不同配比的混合计算"""
        avg = self._avg("""
            [{name:"A", price:100, ash:10, sulfur:1, volatile:30, glue:90, ratio:4},
             {name:"B", price:200, ash:20, sulfur:2, volatile:20, glue:80, ratio:6},
             {name:"C", price:300, ash:30, sulfur:0, volatile:25, glue:70, ratio:0}]
        """)
        # A w=0.4, B w=0.6, C w=0
        # ash: (10*0.4+20*0.6+30*0)/3 = (4+12+0)/3 = 16/3 ≈ 5.333...
        # sulfur: (1*0.4+2*0.6+0*0)/3 = (0.4+1.2)/3 = 1.6/3 ≈ 0.5333...
        # volatile: (30*0.4+20*0.6+25*0)/3 = (12+12)/3 = 8.0
        # glue: (90*0.4+80*0.6+70*0)/3 = (36+48)/3 = 28.0
        # price: (100*0.4+200*0.6+300*0)/3 = (40+120)/3 = 160/3 ≈ 53.333...
        self.assertAlmostEqual(avg["ash"], 5.333333, places=5)
        self.assertAlmostEqual(avg["sulfur"], 0.533333, places=5)
        self.assertAlmostEqual(avg["volatile"], 8.0)
        self.assertAlmostEqual(avg["glue"], 28.0)
        self.assertAlmostEqual(avg["price"], 53.333333, places=5)

    def test_return_structure_always_five_keys(self):
        """现状：返回对象固定包含 ash/sulfur/volatile/glue/price 五个键"""
        avg = self._avg("""
            [{name:"X", price:0, ash:0, sulfur:0, volatile:0, glue:0, ratio:1}]
        """)
        self.assertEqual(set(avg.keys()), {"ash", "sulfur", "volatile", "glue", "price"})

    def test_default_eight_coals_exact_result(self):
        """现状：8 种默认煤种的计算结果（精确值，锁住不改）"""
        avg = self._avg("getDefaultCoals()")
        self.assertAlmostEqual(avg["ash"], 1.048125, places=6)
        self.assertAlmostEqual(avg["sulfur"], 0.168375, places=6)
        self.assertAlmostEqual(avg["volatile"], 3.14, places=6)
        self.assertAlmostEqual(avg["glue"], 7.85, places=6)
        self.assertAlmostEqual(avg["price"], 86.2875, places=6)

    # ══════════════════════════════════════════════
    # 现状：分母=煤种数量的行为特征
    # ══════════════════════════════════════════════

    def test_denominator_is_coal_count_not_total_weight__现状(self):
        """现状「分母=煤种数量」：两种煤总配比不同但煤种数相同→分母相同

        若分母是总权重，两种煤配比1+1=2成（总权重0.2）与配比5+5=10成（总权重1.0）
        结果会不同。当前实现分母=煤种数量=2，所以：
          配比(1,1): ash=(10*0.1+20*0.1)/2=(1+2)/2=1.5
          配比(5,5): ash=(10*0.5+20*0.5)/2=(5+10)/2=7.5
        """
        avg1 = self._avg("""
            [{name:"A", price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:1},
             {name:"B", price:0, ash:20, sulfur:0, volatile:0, glue:0, ratio:1}]
        """)
        avg2 = self._avg("""
            [{name:"A", price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:5},
             {name:"B", price:0, ash:20, sulfur:0, volatile:0, glue:0, ratio:5}]
        """)
        self.assertAlmostEqual(avg1["ash"], 1.5)
        self.assertAlmostEqual(avg2["ash"], 7.5)
        # 验证分母不是总权重：若分母=总权重，avg2["ash"]=(10*0.5+20*0.5)/(0.5+0.5)=15/1=15
        self.assertNotEqual(avg2["ash"], 15.0)  # 证实分母不是总权重

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
        """现状：煤价与其他指标使用完全相同的加权平均公式（也除以煤种数量）"""
        avg = self._avg("""
            [{name:"A", price:100, ash:0, sulfur:0, volatile:0, glue:0, ratio:2},
             {name:"B", price:200, ash:0, sulfur:0, volatile:0, glue:0, ratio:4}]
        """)
        # A w=0.2, B w=0.4, price=(100*0.2+200*0.4)/2=(20+80)/2=50
        self.assertAlmostEqual(avg["price"], 50.0)

    def test_coal_with_zero_ratio_excluded_from_numerator_only(self):
        """现状：配比=0 的煤种不计入分子（权重为0），但仍计入分母（煤种数量）

        即「零配比煤种会稀释结果」——此为关键现状。
        """
        avg_with_zero = self._avg("""
            [{name:"A", price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:5},
             {name:"B", price:0, ash:0, sulfur:0, volatile:0, glue:0, ratio:0}]
        """)
        # A w=0.5, B w=0
        # ash = (10*0.5 + 0*0) / 2 = 5/2 = 2.5
        self.assertAlmostEqual(avg_with_zero["ash"], 2.5)

        # 如果没有 B，结果应该是 10*0.5/1 = 5.0
        avg_without_zero = self._avg("""
            [{name:"A", price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:5}]
        """)
        self.assertAlmostEqual(avg_without_zero["ash"], 5.0)
        # 5.0 ≠ 2.5 —— 零配比煤种稀释了结果
        self.assertNotEqual(avg_with_zero["ash"], avg_without_zero["ash"])


if __name__ == '__main__':
    unittest.main()
