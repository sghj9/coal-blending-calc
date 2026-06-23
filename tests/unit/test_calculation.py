"""单元测试：核心计算逻辑 — calculateHybridMetrics()

混合指标采用标准加权平均：Σ(指标×配比) / Σ(配比)，分母为实际总配比。
所有指标四舍五入到 2 位小数。
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
    """规格文档示例 — 两种煤，标准加权平均（分母=实际总配比 5）"""
    avg = _avg("""
        [{name:"A", price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:2},
         {name:"B", price:0, ash:20, sulfur:0, volatile:0, glue:0, ratio:3}]
    """)
    # 实际总配比=2+3=5，混合灰分=(10×2+20×3)/5=(20+60)/5=16.0
    assert avg["ash"] == pytest.approx(16.0)
    assert avg["sulfur"] == 0.0


def test_single_coal_metric_equals_itself():
    """单煤种 → 指标×配比/总配比 = 指标本身（总配比=该煤配比）"""
    avg = _avg("""
        [{name:"神华", price:650, ash:10, sulfur:2, volatile:30, glue:80, ratio:5}]
    """)
    # 总配比=5，ash=10×5/5=10，sulfur=2×5/5=2，volatile=30×5/5=30
    # glue=80×5/5=80，price=650×5/5=650
    assert avg["ash"] == pytest.approx(10.0)
    assert avg["sulfur"] == pytest.approx(2.0)
    assert avg["volatile"] == pytest.approx(30.0)
    assert avg["glue"] == pytest.approx(80.0)
    assert avg["price"] == pytest.approx(650.0)


def test_three_coals_with_mixed_ratios():
    """三种煤不同配比的混合计算（分母=实际总配比 10，含配比=0 煤种）"""
    avg = _avg("""
        [{name:"A", price:100, ash:10, sulfur:1, volatile:30, glue:90, ratio:4},
         {name:"B", price:200, ash:20, sulfur:2, volatile:20, glue:80, ratio:6},
         {name:"C", price:300, ash:30, sulfur:0, volatile:25, glue:70, ratio:0}]
    """)
    # 总配比=4+6+0=10
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
    """8 种默认煤种的计算结果（实际总配比=8，四舍五入到 2 位）"""
    avg = _avg("getDefaultCoals()")
    # 总配比=8
    # ash=83.85/8=10.48125→10.48, sulfur=13.47/8=1.68375→1.68
    # volatile=251.2/8=31.4, glue=628/8=78.5, price=6903/8=862.875→862.88
    assert avg["ash"] == pytest.approx(10.48, abs=1e-6)
    assert avg["sulfur"] == pytest.approx(1.68, abs=1e-6)
    assert avg["volatile"] == pytest.approx(31.4, abs=1e-6)
    assert avg["glue"] == pytest.approx(78.5, abs=1e-6)
    assert avg["price"] == pytest.approx(862.88, abs=1e-6)


def test_price_participates_in_same_weighted_average():
    """煤价与其他指标使用完全相同的加权公式（分母=实际总配比）"""
    avg = _avg("""
        [{name:"A", price:100, ash:0, sulfur:0, volatile:0, glue:0, ratio:2},
         {name:"B", price:200, ash:0, sulfur:0, volatile:0, glue:0, ratio:4}]
    """)
    # 总配比=6，price=(100×2+200×4)/6=(200+800)/6=166.666…→166.67
    assert avg["price"] == pytest.approx(166.67)


# ═══════════════════════════════════════════════════════════════
# 边界条件 / 空值处理
# ═══════════════════════════════════════════════════════════════

def test_nullish_values_treated_as_zero():
    """null/undefined 的配比和指标值被当作 0 处理（3合1）

    spec §五：缺失数值自动当作 0。
    """
    # null ratio → 总配比=0 → 结果为 0（除零保护）
    avg1 = _avg("[{name:'X', price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:null}]")
    assert avg1["ash"] == 0.0, "配比为 null → 总配比=0 → 结果为 0"

    # undefined ratio (missing property) → 总配比=0 → 结果为 0
    avg2 = _avg("[{name:'X', price:0, ash:10, sulfur:0, volatile:0, glue:0}]")
    assert avg2["ash"] == 0.0, "缺少配比属性 → undefined → 总配比=0"

    # null ash
    avg3 = _avg("[{name:'X', price:0, ash:null, sulfur:0, volatile:0, glue:0, ratio:5}]")
    assert avg3["ash"] == 0.0, "灰分为 null → 当作 0 计算"


def test_empty_or_zero_coals_return_all_zeros():
    """空数组或全部配比=0 → 总配比=0 → 混合指标全 0（除零保护，2合1）"""
    # 空数组
    avg1 = _avg("[]")
    assert avg1["ash"] == 0.0
    assert avg1["sulfur"] == 0.0
    assert avg1["volatile"] == 0.0
    assert avg1["glue"] == 0.0
    assert avg1["price"] == 0.0

    # 全部配比=0 → 总配比=0
    avg2 = _avg("""
        [{name:"A", price:100, ash:10, sulfur:1, volatile:30, glue:90, ratio:0},
         {name:"B", price:200, ash:20, sulfur:2, volatile:30, glue:80, ratio:0}]
    """)
    assert avg2["ash"] == 0.0
    assert avg2["sulfur"] == 0.0


def test_extreme_values():
    """大配比和小数值配比的浮点计算（2合1）

    实际分母模型下，单煤种大/小配比结果都=指标本身（被自身配比约掉）。
    """
    # 大配比：总配比=999，ash=50×999/999=50
    avg1 = _avg("[{name:'X', price:0, ash:50, sulfur:0, volatile:0, glue:0, ratio:999}]")
    assert avg1["ash"] == pytest.approx(50.0)

    # 小数值配比：总配比=0.001，ash=100×0.001/0.001=100
    avg2 = _avg("[{name:'X', price:0, ash:100, sulfur:0, volatile:0, glue:0, ratio:0.001}]")
    assert avg2["ash"] == pytest.approx(100.0)


def test_zero_ratio_coal_does_not_dilute():
    """配比=0 的煤种对分子分母贡献都为 0，不改变混合结果"""
    avg_with_zero = _avg("""
        [{name:"A", price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:5},
         {name:"B", price:0, ash:0, sulfur:0, volatile:0, glue:0, ratio:0}]
    """)
    # 总配比=5，ash=10×5/5=10.0
    assert avg_with_zero["ash"] == pytest.approx(10.0)

    # 如果没有 B，结果应该相同
    avg_without_zero = _avg("[{name:'A', price:0, ash:10, sulfur:0, volatile:0, glue:0, ratio:5}]")
    assert avg_without_zero["ash"] == pytest.approx(10.0)
    # 加不加零配比煤种，结果一致
    assert avg_with_zero["ash"] == avg_without_zero["ash"]
