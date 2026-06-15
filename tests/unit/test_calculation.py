"""单元测试：核心计算逻辑 — calculateHybridMetrics()

从 test_core_calculation.py 精简而来（18 → 10 tests）。
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from helpers import run_js


def _avg(coals_js):
    """以指定 coals 数组调用 calculateHybridMetrics()，返回结果对象。"""
    results = run_js(f"""
        coals = {coals_js};
        report(calculateHybridMetrics());
    """)
    return results[0]


# ═══════════════════════════════════════════════════════════════
# 正常计算路径
# ═══════════════════════════════════════════════════════════════

def test_basic_two_coals_matches_spec_example():
    """规格文档示例 — 两种煤，分母固定 1.0（隐含十成满配）"""
    avg = _avg("""
        [{name:"A", price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:2},
         {name:"B", price:0, ash:20, sulfur:0, volatile:0, glue:0, ratio:3}]
    """)
    # 权重A=2*0.1=0.2, B=3*0.1=0.3, 混合灰分=10*0.2+20*0.3=2+6=8.0（分母=1.0）
    assert avg["ash"] == pytest.approx(8.0)
    assert avg["sulfur"] == 0.0


def test_single_coal_weighted_value_divided_by_one():
    """单煤种 → 指标×权重÷1 = 指标×权重"""
    avg = _avg("""
        [{name:"神华", price:650, ash:10, sulfur:2, volatile:30, glue:80, ratio:5}]
    """)
    # w=0.5, ash=10*0.5/1=5, sulfur=2*0.5/1=1, volatile=30*0.5/1=15
    # glue=80*0.5/1=40, price=650*0.5/1=325
    assert avg["ash"] == pytest.approx(5.0)
    assert avg["sulfur"] == pytest.approx(1.0)
    assert avg["volatile"] == pytest.approx(15.0)
    assert avg["glue"] == pytest.approx(40.0)
    assert avg["price"] == pytest.approx(325.0)


def test_three_coals_with_mixed_ratios():
    """三种煤不同配比的混合计算（分母=1.0，含配比=0 煤种）"""
    avg = _avg("""
        [{name:"A", price:100, ash:10, sulfur:1, volatile:30, glue:90, ratio:4},
         {name:"B", price:200, ash:20, sulfur:2, volatile:20, glue:80, ratio:6},
         {name:"C", price:300, ash:30, sulfur:0, volatile:25, glue:70, ratio:0}]
    """)
    # A w=0.4, B w=0.6, C w=0
    assert avg["ash"] == pytest.approx(16.0)
    assert avg["sulfur"] == pytest.approx(1.6)
    assert avg["volatile"] == pytest.approx(24.0)
    assert avg["glue"] == pytest.approx(84.0)
    assert avg["price"] == pytest.approx(160.0)


def test_return_structure_always_five_keys():
    """返回对象固定包含 ash/sulfur/volatile/glue/price 五个键"""
    avg = _avg("[{name:'X', price:0, ash:0, sulfur:0, volatile:0, glue:0, ratio:1}]")
    assert set(avg.keys()) == {"ash", "sulfur", "volatile", "glue", "price"}


def test_default_eight_coals_exact_result():
    """8 种默认煤种的计算结果（精确值，分母=1.0）"""
    avg = _avg("getDefaultCoals()")
    assert avg["ash"] == pytest.approx(8.385, abs=1e-6)
    assert avg["sulfur"] == pytest.approx(1.347, abs=1e-6)
    assert avg["volatile"] == pytest.approx(25.12, abs=1e-6)
    assert avg["glue"] == pytest.approx(62.8, abs=1e-6)
    assert avg["price"] == pytest.approx(690.3, abs=1e-6)


def test_price_participates_in_same_weighted_average():
    """煤价与其他指标使用完全相同的加权公式（分母固定 1.0）"""
    avg = _avg("""
        [{name:"A", price:100, ash:0, sulfur:0, volatile:0, glue:0, ratio:2},
         {name:"B", price:200, ash:0, sulfur:0, volatile:0, glue:0, ratio:4}]
    """)
    # A w=0.2, B w=0.4, price=100*0.2+200*0.4=20+80=100
    assert avg["price"] == pytest.approx(100.0)


# ═══════════════════════════════════════════════════════════════
# 边界条件 / 空值处理
# ═══════════════════════════════════════════════════════════════

def test_nullish_values_treated_as_zero():
    """null/undefined 的配比和指标值被当作 0 处理（3合1）

    spec §五：缺失数值自动当作 0。
    """
    # null ratio
    avg1 = _avg("[{name:'X', price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:null}]")
    assert avg1["ash"] == 0.0, "配比为 null → 权重=0 → 结果为 0"

    # undefined ratio (missing property)
    avg2 = _avg("[{name:'X', price:0, ash:10, sulfur:0, volatile:0, glue:0}]")
    assert avg2["ash"] == 0.0, "缺少配比属性 → undefined → 权重=0"

    # null ash
    avg3 = _avg("[{name:'X', price:0, ash:null, sulfur:0, volatile:0, glue:0, ratio:5}]")
    assert avg3["ash"] == 0.0, "灰分为 null → 当作 0 计算"


def test_empty_or_zero_coals_return_all_zeros():
    """空数组或全部配比=0 → 加权和全为 0 → 混合指标全 0（2合1）"""
    # 空数组
    avg1 = _avg("[]")
    assert avg1["ash"] == 0.0
    assert avg1["sulfur"] == 0.0
    assert avg1["volatile"] == 0.0
    assert avg1["glue"] == 0.0
    assert avg1["price"] == 0.0

    # 全部配比=0
    avg2 = _avg("""
        [{name:"A", price:100, ash:10, sulfur:1, volatile:30, glue:90, ratio:0},
         {name:"B", price:200, ash:20, sulfur:2, volatile:30, glue:80, ratio:0}]
    """)
    assert avg2["ash"] == 0.0
    assert avg2["sulfur"] == 0.0


def test_extreme_values():
    """大配比和小数值配比的浮点计算（2合1）"""
    # 大配比
    avg1 = _avg("[{name:'X', price:0, ash:50, sulfur:0, volatile:0, glue:0, ratio:999}]")
    # w=999*0.1=99.9, ash=50*99.9/1=4995
    assert avg1["ash"] == pytest.approx(4995.0)

    # 小数值配比
    avg2 = _avg("[{name:'X', price:0, ash:100, sulfur:0, volatile:0, glue:0, ratio:0.001}]")
    # w=0.0001, ash=100*0.0001/1=0.01
    assert avg2["ash"] == pytest.approx(0.01)


def test_zero_ratio_coal_does_not_dilute():
    """配比=0 的煤种计不入分子（权重为0），分母固定 1.0 不会稀释结果"""
    avg_with_zero = _avg("""
        [{name:"A", price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:5},
         {name:"B", price:0, ash:0, sulfur:0, volatile:0, glue:0, ratio:0}]
    """)
    assert avg_with_zero["ash"] == pytest.approx(5.0)

    # 如果没有 B，结果应该相同
    avg_without_zero = _avg("[{name:'A', price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:5}]")
    assert avg_without_zero["ash"] == pytest.approx(5.0)
    # 加不加零配比煤种，结果一致
    assert avg_with_zero["ash"] == avg_without_zero["ash"]
