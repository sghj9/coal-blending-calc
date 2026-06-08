"""特征测试：默认数据与初始化 — DEFAULT_COALS / getDefaultCoals() / initCoals()

锁住默认煤种数据的结构、数值、以及初始化函数的所有现状行为。
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from helpers import run_js


class TestDefaultCoals(unittest.TestCase):
    """锁住 DEFAULT_COALS 常量及其相关函数"""

    def test_eight_default_coals(self):
        """现状：默认 8 种煤"""
        results = run_js("report(DEFAULT_COALS.length);")
        self.assertEqual(results[0], 8)

    def test_default_coal_names(self):
        """现状：8 种煤的名称（顺序敏感）"""
        results = run_js("""
            report(DEFAULT_COALS.map(function(c) { return c.name; }));
        """)
        names = results[0]
        self.assertEqual(names, [
            "神华9层", "11#主焦混洗", "四股权", "金河煤",
            "免洗煤", "圆通2硫", "圆通1.5硫", "温明煤"
        ])

    def test_default_coal_prices(self):
        """现状：8 种煤的煤价"""
        results = run_js("""
            report(DEFAULT_COALS.map(function(c) { return c.price; }));
        """)
        self.assertEqual(results[0], [650, 900, 1150, 600, 500, 1000, 700, 1020])

    def test_default_coal_ash(self):
        """现状：8 种煤的灰分"""
        results = run_js("""
            report(DEFAULT_COALS.map(function(c) { return c.ash; }));
        """)
        self.assertEqual(results[0], [6.5, 9.0, 11.5, 6.0, 5.0, 15.0, 15.0, 15.0])

    def test_default_coal_sulfur(self):
        """现状：8 种煤的硫分"""
        results = run_js("""
            report(DEFAULT_COALS.map(function(c) { return c.sulfur; }));
        """)
        self.assertEqual(results[0], [3.0, 0.8, 3.4, 0.2, 0.5, 2.0, 1.5, 1.0])

    def test_default_coal_volatile(self):
        """现状：8 种煤的挥发分"""
        results = run_js("""
            report(DEFAULT_COALS.map(function(c) { return c.volatile; }));
        """)
        self.assertEqual(results[0], [31, 29, 34, 30, 32, 31, 32, 33])

    def test_default_coal_glue(self):
        """现状：8 种煤的粘结"""
        results = run_js("""
            report(DEFAULT_COALS.map(function(c) { return c.glue; }));
        """)
        self.assertEqual(results[0], [90, 90, 90, 20, 0, 88, 86, 90])

    def test_default_coal_ratios(self):
        """现状：8 种煤的配比（成）"""
        results = run_js("""
            report(DEFAULT_COALS.map(function(c) { return c.ratio; }));
        """)
        self.assertEqual(results[0], [1.0, 2.0, 1.5, 0.6, 0.5, 0.5, 1.0, 0.9])

    def test_default_coal_structure_keys(self):
        """现状：每个默认煤种对象包含 7 个属性"""
        results = run_js("""
            var keys = Object.keys(DEFAULT_COALS[0]).sort();
            report(keys);
        """)
        self.assertEqual(results[0], ["ash", "glue", "name", "price", "ratio", "sulfur", "volatile"])

    def test_default_coal_property_types(self):
        """现状：属性类型——name 为 string，其余均为 number"""
        results = run_js("""
            var c = DEFAULT_COALS[0];
            report([
                typeof c.name,
                typeof c.price,
                typeof c.ash,
                typeof c.sulfur,
                typeof c.volatile,
                typeof c.glue,
                typeof c.ratio
            ]);
        """)
        types = results[0]
        self.assertEqual(types[0], "string")  # name
        for i in range(1, 7):
            self.assertEqual(types[i], "number", f"属性 {i} 应为 number 类型")

    def test_each_coal_has_all_required_properties(self):
        """现状：所有 8 种默认煤种都包含全部 7 个属性，无缺失"""
        results = run_js("""
            var required = ["name", "price", "ash", "sulfur", "volatile", "glue", "ratio"];
            var missing = [];
            DEFAULT_COALS.forEach(function(c, i) {
                required.forEach(function(key) {
                    if (!(key in c)) missing.push("coal[" + i + "]." + key);
                });
            });
            report(missing);
        """)
        self.assertEqual(results[0], [])


class TestGetDefaultCoals(unittest.TestCase):
    """锁住 getDefaultCoals() 的现状行为"""

    def test_returns_array_of_eight(self):
        """现状：返回 8 个元素的数组"""
        results = run_js("report(getDefaultCoals().length);")
        self.assertEqual(results[0], 8)

    def test_returns_deep_copy_not_same_reference(self):
        """现状：返回的是浅拷贝（新对象），修改返回值不影响 DEFAULT_COALS"""
        results = run_js("""
            var copy = getDefaultCoals();
            copy[0].name = "MODIFIED";
            // 检查 DEFAULT_COALS 是否被影响
            report(DEFAULT_COALS[0].name);
        """)
        # ...spread 运算符做浅拷贝，name 是基本类型所以不会被影响
        self.assertEqual(results[0], "神华9层")

    def test_ratio_property_explicitly_copied__现状(self):
        """现状：map 回调中显式写了 ratio: c.ratio（冗余但无害）

        { ...c, ratio: c.ratio } — spread 已复制 ratio，显式赋值覆盖同值。
        """
        results = run_js("""
            var copy = getDefaultCoals();
            report(copy[0].ratio);
        """)
        self.assertEqual(results[0], 1.0)

    def test_does_not_modify_global_coals(self):
        """现状：getDefaultCoals 不修改全局 coals 变量"""
        results = run_js("""
            coals = [{name:"test", price:0, ash:0, sulfur:0, volatile:0, glue:0, ratio:0}];
            var result = getDefaultCoals();
            report(coals.length);   // 应该仍为 1
            report(coals[0].name);  // 应该仍为 "test"
        """)
        self.assertEqual(results[0], 1)
        self.assertEqual(results[1], "test")


class TestInitCoals(unittest.TestCase):
    """锁住 initCoals() 的现状行为"""

    def test_initializes_coals_to_default_coals(self):
        """现状：initCoals() 将全局 coals 设置为 getDefaultCoals() 的返回值"""
        results = run_js("""
            coals = [];
            initCoals();
            report(coals.length);
            report(coals[0].name);
        """)
        self.assertEqual(results[0], 8)
        self.assertEqual(results[1], "神华9层")

    def test_overwrites_existing_coals__现状(self):
        """现状：initCoals() 直接覆盖 coals，无论之前内容是什么"""
        results = run_js("""
            coals = [{name:"自定义", price:0, ash:0, sulfur:0, volatile:0, glue:0, ratio:0}];
            initCoals();
            report(coals.length);
        """)
        self.assertEqual(results[0], 8)  # 被覆盖为默认 8 种

    def test_first_and_last_coal_complete_data(self):
        """现状：验证首尾煤种的完整数据"""
        results = run_js("""
            initCoals();
            report(_clone(coals[0]));
            report(_clone(coals[coals.length - 1]));
        """)
        first = results[0]
        last = results[1]
        self.assertEqual(first, {
            "name": "神华9层", "price": 650, "ash": 6.5,
            "sulfur": 3.0, "volatile": 31, "glue": 90, "ratio": 1.0
        })
        self.assertEqual(last, {
            "name": "温明煤", "price": 1020, "ash": 15.0,
            "sulfur": 1.0, "volatile": 33, "glue": 90, "ratio": 0.9
        })


class TestGlobalStateIsolation(unittest.TestCase):
    """验证：每个测试之间全局变量不会相互污染"""

    def test_coals_is_mutable_global(self):
        """现状：coals 是一个全局可变数组——测试间需手动重置

        本测试确认 coals 确实是全局可变的（此为架构现状）。
        """
        results = run_js("""
            coals = [{name:"isolated_test", price:1, ash:2, sulfur:3, volatile:4, glue:5, ratio:6}];
            report(coals.length);
            report(coals[0].name);
            coals = [];  // 清理
        """)
        self.assertEqual(results[0], 1)
        self.assertEqual(results[1], "isolated_test")

    def test_targetBounds_is_mutable_global(self):
        """现状：targetBounds 是一个全局可变对象——测试间需手动重置"""
        results = run_js("""
            targetBounds.ash = {min: 100, max: 200};
            report(targetBounds.ash.min);
            // 恢复
            targetBounds.ash = {min: 0, max: 11.0};
        """)
        self.assertEqual(results[0], 100)


if __name__ == '__main__':
    unittest.main()
