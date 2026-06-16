"""集成测试：优化器端到端 — optimizeBlending() + calculateHybridMetrics() + checkStatus()

从 test_optimizer.py 提取集成测试（~5 tests）。
验证优化→计算→达标判定的完整链路一致性。
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from helpers import run_js


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
# 优化→计算→判定 全链路测试
# ═══════════════════════════════════════════════════════════════

class TestOptimizerE2E:
    """优化器端到端：跨模块协作的一致性验证"""

    def test_default_8_coals_finds_feasible_solution(self):
        """8 种默认煤 + 默认目标范围 → 应找到可行解"""
        result = _call_optimize("getDefaultCoals()")
        assert result["success"] is True, f"默认煤种应对默认目标范围存在可行解: {result.get('message')}"
        assert result["ratios"] is not None
        assert len(result["ratios"]) == 8
        for i, r in enumerate(result["ratios"]):
            assert r >= -1e-10, f"煤种 {i} 配比 {r} 不应为负数"

    def test_milp_solution_satisfies_ash_volatile_constraints(self):
        """MILP 解满足灰分和挥发分约束，硫分/粘结 status 为 null（参考值）"""
        coals_js = "getDefaultCoals()"
        bounds_js = """
            {ash: {min: 0, max: 11.0}, sulfur: {min: 0, max: 1.0},
             volatile: {min: 28, max: 34}, glue: {min: 75, max: 100}}
        """
        result = _call_optimize(coals_js, bounds_js)
        assert result["success"] is True, f"MILP应找到可行解: {result.get('message')}"
        m = result["metrics"]
        EPS = 1e-6
        assert 0 - EPS <= m["ash"] <= 11.0 + EPS, f"灰分 {m['ash']} 应在 [0, 11.0]"
        assert 28 - EPS <= m["volatile"] <= 34 + EPS, f"挥发分 {m['volatile']} 应在 [28, 34]"
        assert result["status"]["ash"] is True
        assert result["status"]["volatile"] is True
        # 硫分和粘结不作为优化约束，status 为 null（参考值）
        assert result["status"]["sulfur"] is None
        assert result["status"]["glue"] is None

    def test_status_consistent_with_metrics(self):
        """status 与 metrics 相对于 bounds 的一致性正确（仅灰分/挥发分）"""
        coals_js = "getDefaultCoals()"
        bounds_js = """
            {ash: {min: 0, max: 11.0}, sulfur: {min: 0, max: 1.0},
             volatile: {min: 28, max: 34}, glue: {min: 75, max: 100}}
        """
        result = _call_optimize(coals_js, bounds_js)
        assert result["success"] is True
        status = result["status"]
        m = result["metrics"]
        EPS = 1e-10
        assert status["ash"] == (0 - EPS <= m["ash"] <= 11.0 + EPS), (
            f"灰分 status={status['ash']} 与 m={m['ash']} 不一致"
        )
        assert status["volatile"] == (28 - EPS <= m["volatile"] <= 34 + EPS), (
            f"挥发分 status={status['volatile']} 与 m={m['volatile']} 不一致"
        )
        # 硫分和粘结为参考值，status 为 None
        assert status["sulfur"] is None, f"sulfur status 应为 None，实际 {status['sulfur']}"
        assert status["glue"] is None, f"glue status 应为 None，实际 {status['glue']}"

    def test_milp_ratios_consistent_with_hybrid_calculation(self):
        """MILP ratios 代入 calculateHybridMetrics → 价格/指标与 opt 输出一致"""
        results = run_js("""
            coals = getDefaultCoals();
            var __bounds = {ash:{min:0,max:11}, sulfur:{min:0,max:1},
                          volatile:{min:28,max:34}, glue:{min:75,max:100}};
            var opt = optimizeBlending(coals, __bounds);
            if (opt.success) {
                for (var i = 0; i < coals.length; i++) coals[i].ratio = opt.ratios[i];
                var avg = calculateHybridMetrics();
                report({
                    optCost: opt.cost, avgPrice: avg.price,
                    optAsh: opt.metrics.ash, avgAsh: avg.ash,
                    optVolatile: opt.metrics.volatile, avgVolatile: avg.volatile
                });
            } else { report({optSuccess: false}); }
        """)
        r = results[0]
        assert abs(r["optCost"] - r["avgPrice"]) < 1e-6, (
            f"opt.cost={r['optCost']} 应与 avg.price={r['avgPrice']} 一致"
        )
        assert abs(r["optAsh"] - r["avgAsh"]) < 1e-6
        assert abs(r["optVolatile"] - r["avgVolatile"]) < 1e-6

    def test_milp_solution_is_feasible_and_reasonable(self):
        """MILP 求解 8 煤种：手动不可行 → MILP 可行 → 全部达标且成本合理"""
        results = run_js("""
            coals = getDefaultCoals();
            var manualAvg = calculateHybridMetrics();
            var __bounds = {
                ash: { min: 0, max: 11.0 }, sulfur: { min: 0, max: 1.0 },
                volatile: { min: 28, max: 34 }, glue: { min: 75, max: 100 }
            };
            var opt = optimizeBlending(coals, __bounds);
            report({
                manualCost: manualAvg.price,
                manualFeasible: manualAvg.volatile >= 28 && manualAvg.glue >= 75,
                optSuccess: opt.success, optCost: opt.cost,
                optRatios: opt.ratios, totalRatio: opt.totalRatio,
                optVolatile: opt.metrics.volatile, optGlue: opt.metrics.glue,
                optAsh: opt.metrics.ash, optSulfur: opt.metrics.sulfur
            });
        """)
        r = results[0]
        assert r["optSuccess"] is True, "MILP应找到可行解"
        assert r["manualFeasible"] is False, "默认手动配比应该不达标"
        assert r["optVolatile"] >= 28 - 1e-6, f"挥发分 {r['optVolatile']} ≥ 28"
        assert r["optAsh"] <= 11.0 + 1e-6, f"灰分 {r['optAsh']} ≤ 11.0"
        assert 300 <= r["optCost"] <= 1200, f"优化成本 {r['optCost']} 应在合理范围"
