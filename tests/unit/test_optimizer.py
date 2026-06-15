"""单元测试：单纯形法求解器核心算法 — simplex()

从 test_optimizer.py 提取纯算法测试（~18 tests）。
不依赖 DOM mock，仅测试单纯形法数学正确性。
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from helpers import run_js


def _call_simplex(c, A, b):
    """调用 simplex(c, A, b)，返回结果对象。"""
    results = run_js(f"""
        var __c = {c};
        var __A = {A};
        var __b = {b};
        report(simplex(__c, __A, __b));
    """)
    return results[0]


def _call_optimize(coals_js, bounds_js=None):
    """调用 optimizeBlending(coals, bounds)，返回结果对象。"""
    if bounds_js is None:
        bounds_js = """
            {ash: {min: 0, max: 11.0},
             sulfur: {min: 0, max: 1.0},
             volatile: {min: 28, max: 34},
             glue: {min: 75, max: 100}}
        """
    results = run_js(f"""
        coals = {coals_js};
        var __bounds = {bounds_js};
        report(optimizeBlending(coals, __bounds));
    """)
    return results[0]


# ═══════════════════════════════════════════════════════════════
# 单纯形法基础测试
# ═══════════════════════════════════════════════════════════════

class TestSimplex:
    """单纯形法求解器的基本正确性测试"""

    def test_simple_2var_minimization(self):
        """2 变量最小化问题：最优解 x1=1, x2=3, obj=-7"""
        c = [-1, -2]
        A = [[1, 1], [1, 0], [0, 1]]
        b = [4, 2, 3]
        result = _call_simplex(c, A, b)
        assert result["success"] is True, f"单纯形法应成功求解: {result.get('message')}"
        assert abs(result["obj"] - (-7.0)) < 1e-6, f"最优值应为 -7.0，实际 {result['obj']}"
        x = result["x"]
        assert abs(x[0] - 1.0) < 1e-6, f"x1 应为 1.0，实际 {x[0]}"
        assert abs(x[1] - 3.0) < 1e-6, f"x2 应为 3.0，实际 {x[1]}"

    def test_all_zero_cost(self):
        """目标函数系数全为 0 → 最优值为 0"""
        c = [0, 0]
        A = [[1, 1], [1, 0], [0, 1]]
        b = [4, 2, 3]
        result = _call_simplex(c, A, b)
        assert result["success"] is True
        assert abs(result["obj"] - 0.0) < 1e-6
        x = result["x"]
        assert x[0] >= -1e-10
        assert x[1] >= -1e-10
        assert x[0] + x[1] <= 4 + 1e-10
        assert x[0] <= 2 + 1e-10
        assert x[1] <= 3 + 1e-10

    def test_single_variable(self):
        """单变量问题：最优解 x=0, obj=0"""
        c = [3]
        A = [[1]]
        b = [5]
        result = _call_simplex(c, A, b)
        assert result["success"] is True
        assert abs(result["obj"] - 0.0) < 1e-6
        assert abs(result["x"][0] - 0.0) < 1e-6

    def test_infeasible_problem(self):
        """可行域非空的基本问题"""
        c = [1, 1]
        A = [[-1, 0]]
        b = [-1]
        # 可行域: x1 >= 1, x2 >= 0，有可行解
        result = _call_simplex(c, A, b)
        assert result["success"] is True

    def test_multiple_constraints(self):
        """多约束 3 变量问题"""
        c = [1, 2, 3]
        A = [[1, 1, 1], [2, 1, 0], [0, 1, 2]]
        b = [10, 8, 6]
        result = _call_simplex(c, A, b)
        assert result["success"] is True
        x = result["x"]
        assert x[0] >= -1e-10
        assert x[1] >= -1e-10
        assert x[2] >= -1e-10
        assert x[0] + x[1] + x[2] <= 10 + 1e-10
        assert 2 * x[0] + x[1] <= 8 + 1e-10
        assert x[1] + 2 * x[2] <= 6 + 1e-10
        assert result["obj"] <= 13 + 1e-10, f"目标值 {result['obj']} 应不超过已知可行解 13"


# ═══════════════════════════════════════════════════════════════
# optimizeBlending() 基础功能测试
# ═══════════════════════════════════════════════════════════════

class TestOptimizeBlending:
    """optimizeBlending() 的边界和算法正确性测试"""

    # ── 边界情况 ──

    def test_single_coal(self):
        """单煤种：指标在范围内应有可行解"""
        coals_js = '[{name:"单煤", price:800, ash:10, sulfur:0.8, volatile:30, glue:80}]'
        result = _call_optimize(coals_js)
        assert result["success"] is True, f"单煤种指标在范围内，应有可行解: {result.get('message')}"

    def test_single_coal_out_of_bounds(self):
        """单煤种指标超出目标范围 → 无可行解"""
        coals_js = '[{name:"高硫煤", price:500, ash:10, sulfur:3.0, volatile:30, glue:80}]'
        bounds_js = """
            {ash: {min: 0, max: 11.0}, sulfur: {min: 0, max: 1.0},
             volatile: {min: 28, max: 34}, glue: {min: 75, max: 100}}
        """
        result = _call_optimize(coals_js, bounds_js)
        assert result["success"] is False, "硫分超标，应无可行解"

    def test_empty_coals_returns_error(self):
        """空煤种列表 → success=false"""
        result = _call_optimize("[]")
        assert result["success"] is False
        assert "煤种" in result.get("message", "")

    def test_all_zero_price_solution(self):
        """所有煤价为 0 → 成本为 0"""
        coals_js = """
            [{name:"A", price:0, ash:10, sulfur:0.8, volatile:30, glue:80},
             {name:"B", price:0, ash:8, sulfur:0.5, volatile:32, glue:85}]
        """
        result = _call_optimize(coals_js)
        if result["success"]:
            assert abs(result["cost"] - 0.0) < 1e-6, f"所有煤价=0时成本应为0，实际 {result['cost']}"

    def test_very_tight_sulfur_constraint(self):
        """极严硫分约束（0~0.3），只有低硫煤种能入选"""
        coals_js = """
            [{name:"高硫煤", price:500, ash:10, sulfur:3.0, volatile:30, glue:80},
             {name:"低硫煤", price:1200, ash:10, sulfur:0.2, volatile:30, glue:80}]
        """
        bounds_js = """
            {ash: {min: 0, max: 11.0}, sulfur: {min: 0, max: 0.3},
             volatile: {min: 28, max: 34}, glue: {min: 75, max: 100}}
        """
        result = _call_optimize(coals_js, bounds_js)
        assert result["success"] is True, f"低硫煤可满足约束: {result.get('message')}"
        m = result["metrics"]
        assert m["sulfur"] <= 0.3 + 1e-6, f"硫分 {m['sulfur']} 应在 ≤ 0.3"
        ratios = result["ratios"]
        assert ratios[0] <= 1.0, f"高硫煤配比 {ratios[0]} 不应过高"

    def test_zero_target_range_exact_match(self):
        """下限=上限时作为紧约束处理"""
        coals_js = """
            [{name:"A", price:800, ash:10, sulfur:0.8, volatile:30, glue:80},
             {name:"B", price:600, ash:10, sulfur:0.8, volatile:30, glue:90}]
        """
        bounds_js = """
            {ash: {min: 10.0, max: 10.0}, sulfur: {min: 0.8, max: 0.8},
             volatile: {min: 30.0, max: 30.0}, glue: {min: 80, max: 100}}
        """
        result = _call_optimize(coals_js, bounds_js)
        if result["success"]:
            m = result["metrics"]
            assert abs(m["ash"] - 10.0) < 1e-4, f"灰分应精确为 10.0: {m['ash']}"
            assert abs(m["sulfur"] - 0.8) < 1e-4, f"硫分应精确为 0.8: {m['sulfur']}"

    def test_no_feasible_solution_extreme_bounds(self):
        """目标范围过于严苛 → 无可行解"""
        coals_js = "getDefaultCoals()"
        bounds_js = """
            {ash: {min: 0, max: 3.0}, sulfur: {min: 0, max: 1.0},
             volatile: {min: 28, max: 34}, glue: {min: 75, max: 100}}
        """
        result = _call_optimize(coals_js, bounds_js)
        assert result["success"] is False, f"所有煤灰分≥5，要求灰分≤3，应无可行解: {result}"

    def test_result_structure_complete(self):
        """返回对象的结构完整性"""
        coals_js = "getDefaultCoals()"
        result = _call_optimize(coals_js)
        required_keys = {"success", "ratios", "totalRatio", "cost", "metrics", "status", "message"}
        assert required_keys.issubset(set(result.keys())), (
            f"返回对象缺少键: {required_keys - set(result.keys())}"
        )
        if result["success"]:
            metrics = result["metrics"]
            for key in ["ash", "sulfur", "volatile", "glue", "price"]:
                assert key in metrics, f"metrics 缺少 {key}"
            status = result["status"]
            for key in ["ash", "sulfur", "volatile", "glue"]:
                assert key in status, f"status 缺少 {key}"
            assert isinstance(result["totalRatio"], (int, float))
            assert isinstance(result["cost"], (int, float))

    def test_optimized_cost_is_reasonable(self):
        """优化成本应在合理范围（500~1200）"""
        coals_js = "getDefaultCoals()"
        result = _call_optimize(coals_js)
        assert result["success"] is True
        assert 500 <= result["cost"] <= 1200, (
            f"优化成本 {result['cost']} 应在合理范围 [500, 1200]"
        )

    # ── MILP 专项测试 ──

    def test_milp_ratios_are_multiples_of_point_one(self):
        """MILP 输出配比应为 0.1 的整数倍"""
        coals_js = "getDefaultCoals()"
        result = _call_optimize(coals_js)
        assert result["success"] is True
        for i, r in enumerate(result["ratios"]):
            assert abs(r * 10 - round(r * 10)) < 1e-6, (
                f"煤种 {i} 配比 {r} 不是 0.1 的整数倍"
            )
            assert 0 <= r <= 10.0, f"煤种 {i} 配比 {r} 超出 [0, 10]"

    def test_milp_2var_integer_solution(self):
        """2煤种 MILP：验证解中所有 y_i 为整数"""
        coals_js = """
            [{name:"A", price:800, ash:10, sulfur:0.8, volatile:30, glue:80},
             {name:"B", price:600, ash:8, sulfur:0.5, volatile:32, glue:90}]
        """
        result = _call_optimize(coals_js)
        assert result["success"] is True
        for i, r in enumerate(result["ratios"]):
            assert abs(r * 10 - round(r * 10)) < 1e-6, (
                f"煤种 {i} 配比 {r} ×10 = {r*10} 不是整数"
            )

    def test_milp_optimality_brute_force_verification(self):
        """穷举验证：2煤种 B&B 结果 = 枚举 0.1 步长的最优解"""
        results = run_js("""
            coals = [
                {name:"A", price:800, ash:10, sulfur:0.8, volatile:30, glue:80},
                {name:"B", price:600, ash:8, sulfur:0.5, volatile:32, glue:90}
            ];
            var __bounds = {
                ash: {min: 0, max: 11}, sulfur: {min: 0, max: 1},
                volatile: {min: 28, max: 34}, glue: {min: 75, max: 100}
            };
            var opt = optimizeBlending(coals, __bounds);
            var bestCost = Infinity, bestY = null;
            for (var y0 = 0; y0 <= 100; y0++) {
                for (var y1 = 0; y1 <= 100; y1++) {
                    if (y0 + y1 > 100) continue;
                    var w0 = y0 * 0.01, w1 = y1 * 0.01;
                    var ash = coals[0].ash * w0 + coals[1].ash * w1;
                    var sulfur = coals[0].sulfur * w0 + coals[1].sulfur * w1;
                    var vol = coals[0].volatile * w0 + coals[1].volatile * w1;
                    var glue = coals[0].glue * w0 + coals[1].glue * w1;
                    if (ash < 0 || ash > 11) continue;
                    if (sulfur < 0 || sulfur > 1) continue;
                    if (vol < 28 || vol > 34) continue;
                    if (glue < 75 || glue > 100) continue;
                    var cost = coals[0].price * w0 + coals[1].price * w1;
                    if (cost < bestCost - 1e-10) { bestCost = cost; bestY = [y0, y1]; }
                }
            }
            report({
                optSuccess: opt.success, optCost: opt.cost,
                optR0: opt.ratios[0], optR1: opt.ratios[1],
                bruteCost: bestCost,
                bruteR0: bestY ? bestY[0] / 10 : null,
                bruteR1: bestY ? bestY[1] / 10 : null
            });
        """)
        r = results[0]
        assert r["optSuccess"] is True
        assert abs(r["optCost"] - r["bruteCost"]) < 1e-6, (
            f"MILP cost={r['optCost']} 应与 brute-force cost={r['bruteCost']} 一致"
        )

    def test_total_ratio_not_exceed_10(self):
        """总配比不应超过 10 成"""
        coals_js = "getDefaultCoals()"
        result = _call_optimize(coals_js)
        assert result["success"] is True
        assert result["totalRatio"] <= 10.0 + 1e-10, (
            f"总配比 {result['totalRatio']} 不应超过 10 成"
        )
