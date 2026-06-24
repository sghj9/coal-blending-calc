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
        """单煤种硫分超出目标范围 → 无可行解（灰分/挥发分/硫分均参与约束）"""
        coals_js = '[{name:"高硫煤", price:500, ash:10, sulfur:3.0, volatile:30, glue:80}]'
        bounds_js = """
            {ash: {min: 0, max: 11.0}, sulfur: {min: 0, max: 1.0},
             volatile: {min: 28, max: 34}, glue: {min: 75, max: 100}}
        """
        result = _call_optimize(coals_js, bounds_js)
        # 硫分现为约束，单煤硫分 3.0 > 1.0 → 无可行解
        assert result["success"] is False, f"硫分超标应无可行解: {result.get('message')}"

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
        """硫分作为约束 → 优化器被迫多用低硫煤（ash/volatile相同）"""
        coals_js = """
            [{name:"高硫煤", price:500, ash:10, sulfur:3.0, volatile:30, glue:80},
             {name:"低硫煤", price:1200, ash:10, sulfur:0.2, volatile:30, glue:80}]
        """
        bounds_js = """
            {ash: {min: 0, max: 11.0}, sulfur: {min: 0, max: 0.3},
             volatile: {min: 28, max: 34}, glue: {min: 75, max: 100}}
        """
        result = _call_optimize(coals_js, bounds_js)
        assert result["success"] is True, f"ash/volatile在范围内，应有可行解: {result.get('message')}"
        # 硫分约束 ≤0.3，高硫煤(3.0)最多只能用约 0.35 成，其余用低硫煤(0.2)
        ratios = result["ratios"]
        assert ratios[1] > ratios[0], f"低硫煤应比高硫煤使用更多配比以满足硫分约束: {ratios}"

    def test_zero_target_range_exact_match(self):
        """下限=上限时作为紧约束处理（仅灰分/挥发分参与约束）"""
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
            assert abs(m["volatile"] - 30.0) < 1e-4, f"挥发分应精确为 30.0: {m['volatile']}"

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
            # 灰分、挥发分、硫分为约束指标，status 为布尔值
            assert isinstance(status["ash"], bool), f"ash status 应为布尔值，实际 {type(status['ash'])}"
            assert isinstance(status["volatile"], bool), f"volatile status 应为布尔值，实际 {type(status['volatile'])}"
            assert isinstance(status["sulfur"], bool), f"sulfur status 应为布尔值，实际 {type(status['sulfur'])}"
            # 粘结为参考值，status 为 null（Python None）
            assert status["glue"] is None, f"glue status 应为 None，实际 {status['glue']}"
            assert isinstance(result["totalRatio"], (int, float))
            assert isinstance(result["cost"], (int, float))

    def test_optimized_cost_is_reasonable(self):
        """优化成本应在合理范围（灰分/挥发分/硫分约束下）"""
        coals_js = "getDefaultCoals()"
        result = _call_optimize(coals_js)
        assert result["success"] is True
        assert 300 <= result["cost"] <= 1500, (
            f"优化成本 {result['cost']} 应在合理范围 [300, 1500]"
        )

    # ── MILP 专项测试 ──

    def test_milp_ratios_are_multiples_of_point_zero_one(self):
        """MILP 输出配比应为 0.01 的整数倍（2 位小数）"""
        coals_js = "getDefaultCoals()"
        result = _call_optimize(coals_js)
        assert result["success"] is True
        for i, r in enumerate(result["ratios"]):
            assert abs(r * 100 - round(r * 100)) < 1e-6, (
                f"煤种 {i} 配比 {r} 不是 0.01 的整数倍"
            )
            assert 0 <= r <= 10.0, f"煤种 {i} 配比 {r} 超出 [0, 10]"

    def test_milp_2var_integer_solution(self):
        """2煤种 MILP：验证解中所有 y_i 为整数（步长 0.01 成）"""
        coals_js = """
            [{name:"A", price:800, ash:10, sulfur:0.8, volatile:30, glue:80},
             {name:"B", price:600, ash:8, sulfur:0.5, volatile:32, glue:90}]
        """
        result = _call_optimize(coals_js)
        assert result["success"] is True
        for i, r in enumerate(result["ratios"]):
            assert abs(r * 100 - round(r * 100)) < 1e-6, (
                f"煤种 {i} 配比 {r} ×100 = {r*100} 不是整数"
            )

    def test_milp_optimality_brute_force_verification(self):
        """穷举验证：2煤种 B&B 结果 = 枚举 0.01 步长、等式总配比=10、含硫分约束的最优解"""
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
            // 等式总配比 Σy = 1000（即 Σr = 10），步长 0.01 成
            for (var y0 = 0; y0 <= 1000; y0++) {
                var y1 = 1000 - y0;
                var w0 = y0 / 1000, w1 = y1 / 1000;
                var ash = coals[0].ash * w0 + coals[1].ash * w1;
                var sulfur = coals[0].sulfur * w0 + coals[1].sulfur * w1;
                var vol = coals[0].volatile * w0 + coals[1].volatile * w1;
                if (ash < 0 || ash > 11) continue;
                if (vol < 28 || vol > 34) continue;
                if (sulfur < 0 || sulfur > 1) continue;
                var cost = coals[0].price * w0 + coals[1].price * w1;
                if (cost < bestCost - 1e-10) { bestCost = cost; bestY = [y0, y1]; }
            }
            report({
                optSuccess: opt.success, optCost: opt.cost,
                optR0: opt.ratios[0], optR1: opt.ratios[1],
                bruteCost: bestCost,
                bruteR0: bestY ? bestY[0] / 100 : null,
                bruteR1: bestY ? bestY[1] / 100 : null
            });
        """)
        r = results[0]
        assert r["optSuccess"] is True
        assert abs(r["optCost"] - r["bruteCost"]) < 1e-6, (
            f"MILP cost={r['optCost']} 应与 brute-force cost={r['bruteCost']} 一致"
        )

    def test_total_ratio_equals_10(self):
        """总配比恒等于 10 成（等式约束）"""
        coals_js = "getDefaultCoals()"
        result = _call_optimize(coals_js)
        assert result["success"] is True
        assert abs(result["totalRatio"] - 10.0) < 1e-10, (
            f"总配比 {result['totalRatio']} 应等于 10 成（等式约束）"
        )


# ═══════════════════════════════════════════════════════════════
# 调料煤约束测试
# ═══════════════════════════════════════════════════════════════

class TestSeasoningCoalConstraint:
    """调料煤：单种 ≤1 成、合计 ≤1.5 成"""

    def test_seasoning_coal_single_capped_at_1(self):
        """调料煤（免洗煤）单种 ≤1 成：自定义 2 煤，免洗煤低价高指标本可被大量选用"""
        coals_js = """
            [{name:"普通煤", price:900, ash:10, sulfur:0.8, volatile:30, glue:90},
             {name:"免洗煤", price:300, ash:6, sulfur:0.3, volatile:30, glue:90}]
        """
        bounds_js = """
            {ash: {min: 0, max: 11.0}, sulfur: {min: 0, max: 1.0},
             volatile: {min: 28, max: 34}, glue: {min: 75, max: 100}}
        """
        result = _call_optimize(coals_js, bounds_js)
        assert result["success"] is True, f"应有可行解: {result.get('message')}"
        # 免洗煤(索引1)为调料煤，单种配比 ≤1 成
        assert result["ratios"][1] <= 1.0 + 1e-6, (
            f"调料煤配比 {result['ratios'][1]} 应 ≤ 1 成"
        )

    def test_seasoning_coal_sum_capped_at_1_5(self):
        """调料煤合计 ≤1.5 成：自定义 3 煤含 2 种调料煤（免洗煤+金河煤），均低价且指标达标"""
        coals_js = """
            [{name:"普通煤", price:900, ash:10, sulfur:0.8, volatile:30, glue:90},
             {name:"免洗煤", price:300, ash:6, sulfur:0.3, volatile:30, glue:90},
             {name:"金河煤", price:350, ash:6, sulfur:0.4, volatile:30, glue:90}]
        """
        bounds_js = """
            {ash: {min: 0, max: 11.0}, sulfur: {min: 0, max: 1.0},
             volatile: {min: 28, max: 34}, glue: {min: 75, max: 100}}
        """
        result = _call_optimize(coals_js, bounds_js)
        assert result["success"] is True, f"应有可行解: {result.get('message')}"
        EPS = 1e-6
        # 索引 1（免洗煤）、2（金河煤）各 ≤1 成
        for i in (1, 2):
            assert result["ratios"][i] <= 1.0 + EPS, (
                f"调料煤(索引{i}) 配比 {result['ratios'][i]} 应 ≤ 1 成"
            )
        # 两种调料煤合计 ≤1.5 成
        seasoning_sum = result["ratios"][1] + result["ratios"][2]
        assert seasoning_sum <= 1.5 + EPS, f"调料煤合计 {seasoning_sum} 应 ≤ 1.5 成"

    def test_seasoning_coal_alias_recognized(self):
        """别名（金河精煤/魏矿精煤/无烟沫子精煤）被识别为调料煤，单种 ≤ 1 成"""
        coals_js = """
            [{name:"普通煤", price:900, ash:10, sulfur:0.8, volatile:30, glue:80},
             {name:"金河精煤", price:500, ash:6, sulfur:0.2, volatile:30, glue:20},
             {name:"魏矿精煤", price:510, ash:6, sulfur:0.3, volatile:31, glue:20},
             {name:"无烟沫子精煤", price:520, ash:6, sulfur:0.4, volatile:31, glue:20}]
        """
        # 目标范围宽松，让低成本调料煤本可被大量选用，但受 ≤1 成约束
        bounds_js = """
            {ash: {min: 0, max: 11.0}, sulfur: {min: 0, max: 1.0},
             volatile: {min: 28, max: 34}, glue: {min: 0, max: 100}}
        """
        result = _call_optimize(coals_js, bounds_js)
        assert result["success"] is True, f"应有可行解: {result.get('message')}"
        EPS = 1e-6
        # 索引 1/2/3 为调料煤，各自 ≤ 1 成
        for i in (1, 2, 3):
            assert result["ratios"][i] <= 1.0 + EPS, (
                f"调料煤(索引{i}) 配比 {result['ratios'][i]} 应 ≤ 1 成"
            )
        # 三种调料煤合计 ≤ 1.5 成
        seasoning_sum = sum(result["ratios"][i] for i in (1, 2, 3))
        assert seasoning_sum <= 1.5 + EPS, f"调料煤合计 {seasoning_sum} 应 ≤ 1.5 成"

    def test_seasoning_coal_brute_force_verification(self):
        """穷举验证：3 煤种（含 2 调料煤）下 MILP 解 = 含调料煤约束的穷举最优"""
        results = run_js("""
            coals = [
                {name:"普通煤", price:900, ash:10, sulfur:0.8, volatile:30, glue:80},
                {name:"免洗煤", price:500, ash:5, sulfur:0.5, volatile:32, glue:0},
                {name:"金河煤", price:600, ash:6, sulfur:0.2, volatile:30, glue:20}
            ];
            var __bounds = {
                ash: {min: 0, max: 11}, sulfur: {min: 0, max: 1},
                volatile: {min: 28, max: 34}, glue: {min: 0, max: 100}
            };
            var opt = optimizeBlending(coals, __bounds);
            // 穷举：等式 y0+y1+y2=1000，调料煤 y1,y2 各 ≤100，y1+y2 ≤150
            var bestCost = Infinity, bestY = null;
            for (var y1 = 0; y1 <= 100; y1++) {
                for (var y2 = 0; y2 <= 100; y2++) {
                    if (y1 + y2 > 150) continue;
                    var y0 = 1000 - y1 - y2;
                    if (y0 < 0 || y0 > 1000) continue;
                    var w0 = y0/1000, w1 = y1/1000, w2 = y2/1000;
                    var ash = coals[0].ash*w0 + coals[1].ash*w1 + coals[2].ash*w2;
                    var sulfur = coals[0].sulfur*w0 + coals[1].sulfur*w1 + coals[2].sulfur*w2;
                    var vol = coals[0].volatile*w0 + coals[1].volatile*w1 + coals[2].volatile*w2;
                    if (ash < 0 || ash > 11) continue;
                    if (vol < 28 || vol > 34) continue;
                    if (sulfur < 0 || sulfur > 1) continue;
                    var cost = coals[0].price*w0 + coals[1].price*w1 + coals[2].price*w2;
                    if (cost < bestCost - 1e-10) { bestCost = cost; bestY = [y0,y1,y2]; }
                }
            }
            report({
                optSuccess: opt.success, optCost: opt.cost,
                bruteCost: bestCost,
                optR1: opt.ratios[1], optR2: opt.ratios[2]
            });
        """)
        r = results[0]
        assert r["optSuccess"] is True
        assert r["bruteCost"] is not None, "穷举应找到可行解"
        assert abs(r["optCost"] - r["bruteCost"]) < 1e-6, (
            f"MILP cost={r['optCost']} 应与 brute-force cost={r['bruteCost']} 一致"
        )

