"""单元测试：默认数据与初始化 — DEFAULT_COALS / getDefaultCoals() / initCoals()

从 test_initial_data.py 精简而来（20 → 10 tests）。
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
# DEFAULT_COALS 数据测试
# ═══════════════════════════════════════════════════════════════

def test_default_coals_count():
    """默认 8 种煤"""
    result = _js1("report(DEFAULT_COALS.length);")
    assert result == 8


def test_default_coal_names():
    """8 种煤的名称（顺序敏感）"""
    result = _js1("report(DEFAULT_COALS.map(function(c) { return c.name; }));")
    assert result == [
        "神华9层", "11#主焦混洗", "四股权", "金河煤",
        "免洗煤", "圆通2硫", "圆通1.5硫", "温明煤"
    ]


def test_default_coal_prices_and_ash():
    """8 种煤的煤价和灰分（同一数值类型合并）"""
    result = _js1("""
        var prices = DEFAULT_COALS.map(function(c) { return c.price; });
        var ashes = DEFAULT_COALS.map(function(c) { return c.ash; });
        report({prices: prices, ashes: ashes});
    """)
    assert result["prices"] == [650, 900, 1150, 600, 500, 1000, 700, 1020]
    assert result["ashes"] == [6.5, 9.0, 11.5, 6.0, 5.0, 15.0, 15.0, 15.0]


def test_default_coal_sulfur_and_volatile():
    """8 种煤的硫分和挥发分（同一数值类型合并）"""
    result = _js1("""
        var sulfurs = DEFAULT_COALS.map(function(c) { return c.sulfur; });
        var volatiles = DEFAULT_COALS.map(function(c) { return c.volatile; });
        report({sulfurs: sulfurs, volatiles: volatiles});
    """)
    assert result["sulfurs"] == [3.0, 0.8, 3.4, 0.2, 0.5, 2.0, 1.5, 1.0]
    assert result["volatiles"] == [31, 29, 34, 30, 32, 31, 32, 33]


def test_default_coal_glue_and_ratios():
    """8 种煤的粘结和配比（同一数值类型合并）"""
    result = _js1("""
        var glues = DEFAULT_COALS.map(function(c) { return c.glue; });
        var ratios = DEFAULT_COALS.map(function(c) { return c.ratio; });
        report({glues: glues, ratios: ratios});
    """)
    assert result["glues"] == [90, 90, 90, 20, 0, 88, 86, 90]
    assert result["ratios"] == [1.0, 2.0, 1.5, 0.6, 0.5, 0.5, 1.0, 0.9]


def test_default_coal_structure_and_properties():
    """结构验证：keys + 属性类型 + 所有煤种都有 7 个必填属性（3合1）"""
    result = _js1("""
        var keys = Object.keys(DEFAULT_COALS[0]).sort();
        var c = DEFAULT_COALS[0];
        var types = [
            typeof c.name, typeof c.price, typeof c.ash,
            typeof c.sulfur, typeof c.volatile, typeof c.glue, typeof c.ratio
        ];
        var required = ["name", "price", "ash", "sulfur", "volatile", "glue", "ratio"];
        var missing = [];
        DEFAULT_COALS.forEach(function(coal, i) {
            required.forEach(function(key) {
                if (!(key in coal)) missing.push("coal[" + i + "]." + key);
            });
        });
        report({keys: keys, types: types, missing: missing});
    """)
    assert result["keys"] == ["ash", "glue", "name", "price", "ratio", "sulfur", "volatile"]
    assert result["types"][0] == "string"  # name
    for i in range(1, 7):
        assert result["types"][i] == "number", f"属性 {i} 应为 number 类型"
    assert result["missing"] == []


# ═══════════════════════════════════════════════════════════════
# getDefaultCoals() 测试
# ═══════════════════════════════════════════════════════════════

def test_get_default_coals_returns_independent_copy():
    """getDefaultCoals() 返回独立拷贝：8 个元素、不影响 DEFAULT_COALS、不影响全局 coals（3合1）"""
    result = _js1("""
        var copy = getDefaultCoals();
        copy[0].name = "MODIFIED";
        coals = [{name:"test", price:0, ash:0, sulfur:0, volatile:0, glue:0, ratio:0}];
        var result2 = getDefaultCoals();
        report({
            copyLen: copy.length,
            defaultName0: DEFAULT_COALS[0].name,
            coalsLen: coals.length,
            coalsName0: coals[0].name
        });
    """)
    assert result["copyLen"] == 8
    assert result["defaultName0"] == "神华9层", "修改拷贝不应影响 DEFAULT_COALS"
    assert result["coalsLen"] == 1, "getDefaultCoals 不应修改 coals 数组长度"
    assert result["coalsName0"] == "test", "getDefaultCoals 不应修改 coals 内容"


# ═══════════════════════════════════════════════════════════════
# initCoals() 测试
# ═══════════════════════════════════════════════════════════════

def test_init_coals_populates_default():
    """initCoals() 将全局 coals 设置为默认 8 种煤"""
    result = _js1("""
        coals = [];
        initCoals();
        report({len: coals.length, name0: coals[0].name});
    """)
    assert result["len"] == 8
    assert result["name0"] == "神华9层"


def test_first_and_last_coal_complete_data():
    """验证首尾煤种的完整数据"""
    result = _js1("""
        initCoals();
        report({first: _clone(coals[0]), last: _clone(coals[coals.length - 1])});
    """)
    assert result["first"] == {
        "name": "神华9层", "price": 650, "ash": 6.5,
        "sulfur": 3.0, "volatile": 31, "glue": 90, "ratio": 1.0
    }
    assert result["last"] == {
        "name": "温明煤", "price": 1020, "ash": 15.0,
        "sulfur": 1.0, "volatile": 33, "glue": 90, "ratio": 0.9
    }


# ═══════════════════════════════════════════════════════════════
# 调料煤识别测试 — isSeasoningCoal()
# ═══════════════════════════════════════════════════════════════

def test_is_seasoning_coal_matching():
    """isSeasoningCoal 精确匹配清单 8 个名（含别名），非清单名/空名返回 false"""
    result = _js1("""
        var seasoning = ["免洗煤", "金河煤", "金河精煤",
                         "魏矿", "魏矿精煤",
                         "无烟沫子", "无烟煤", "无烟沫子精煤"];
        var nonSeasoning = ["神华9层", "11#主焦混洗", "四股权", "温明煤", "x", ""];
        report({
            seasoning: seasoning.map(isSeasoningCoal),
            nonSeasoning: nonSeasoning.map(isSeasoningCoal),
            nullName: isSeasoningCoal(null),
            undefinedName: isSeasoningCoal(undefined)
        });
    """)
    assert result["seasoning"] == [True] * 8
    # 非清单名、空串、null、undefined 均为 false
    assert result["nonSeasoning"] == [False, False, False, False, False, False]
    assert result["nullName"] is False
    assert result["undefinedName"] is False


def test_default_coals_seasoning_flags():
    """默认 8 煤中仅金河煤(3)、免洗煤(4) 为调料煤"""
    result = _js1("""
        coals = getDefaultCoals();
        report(coals.map(function(c){return isSeasoningCoal(c.name);}));
    """)
    expected = [False, False, False, True, True, False, False, False]
    assert result == expected
