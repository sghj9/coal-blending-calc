"""特征测试辅助模块

从 JS 模块文件中提取 JavaScript 业务逻辑，
通过 Node.js 子进程执行，返回结果供 Python 测试断言使用。

依赖：Node.js（已在环境变量 PATH 中）。
"""

import subprocess
import json
import os
import re
import tempfile
import unittest

# 项目根目录
_PROJECT_DIR = os.path.join(os.path.dirname(__file__), '..')
_JS_DIR = os.path.join(_PROJECT_DIR, 'js')

# 缓存拼接后的脚本内容
_SCRIPT_CACHE = None

# Node.js 可执行文件路径
_NODE_PATH = os.path.expandvars(r'D:\SLDownload\Nodejs\node.exe')

# JS 文件加载顺序（依赖顺序：main 先定义全局变量和核心函数）
_JS_FILES = ['main.js', 'ui.js', 'validation.js', 'storage.js']


def _get_script():
    """按依赖顺序读取所有 JS 模块文件并拼接为一个脚本。

    加载顺序保证：
    - main.js 定义全局变量（coals, targetBounds）和核心函数
    - ui.js 中的函数引用 main.js 中的全局，运行时调用
    - validation.js 独立，确认/校验函数
    - storage.js 为空占位
    """
    global _SCRIPT_CACHE
    if _SCRIPT_CACHE is not None:
        return _SCRIPT_CACHE

    parts = []
    for filename in _JS_FILES:
        filepath = os.path.join(_JS_DIR, filename)
        if not os.path.exists(filepath):
            continue  # 跳过不存在的文件（如 storage.js 可能还没创建）
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        parts.append(content)

    script = '\n'.join(parts)
    # 移除底部的 init() 调用，测试代码自行控制执行时机
    script = re.sub(r'\n\s*init\(\);?\s*$', '\n// [测试] init() 已禁用，由测试代码控制执行', script)
    _SCRIPT_CACHE = script
    return _SCRIPT_CACHE


def run_js(test_code, timeout=15):
    """运行 JavaScript 测试代码，返回上报的结果列表。

    工作流程：
    1. 注入最小化的浏览器全局对象 mock（document/alert/confirm/prompt）
    2. 加载应用脚本
    3. 注入测试上报函数 report()
    4. 执行 test_code
    5. 收集 report() 上报的值并返回

    参数：
        test_code: 要执行的 JavaScript 测试代码（可使用 report() 上报结果）
        timeout: 子进程超时秒数

    返回：
        list: 所有 report() 上报的值（已从 JSON 反序列化）

    异常：
        RuntimeError: JS 执行失败或结果解析失败
    """
    script = _get_script()

    full_js = f"""// ===== 浏览器全局对象 Mock =====
// 提供通用 mock：getElementById 返回可用对象（避免 null 访问崩溃）
// querySelectorAll 返回空数组；createElement 返回通用 mock 元素
global.document = {{
    getElementById: function(id) {{
        return {{
            innerHTML: '',
            value: '0',
            style: {{}},
            textContent: '',
            addEventListener: function(evt, fn) {{}},
            appendChild: function(c) {{}},
            setAttribute: function(k, v) {{}},
            getAttribute: function(k) {{ return null; }},
            insertRow: function() {{
                return {{
                    rowIndex: -1,
                    cells: [],
                    insertCell: function() {{
                        var cell = {{
                            appendChild: function(c) {{}},
                            querySelector: function(sel) {{ return null; }}
                        }};
                        this.cells.push(cell);
                        return cell;
                    }}
                }};
            }},
            querySelector: function(sel) {{ return null; }},
            querySelectorAll: function(sel) {{ return []; }}
        }};
    }},
    querySelectorAll: function(sel) {{ return []; }},
    createElement: function(tag) {{
        return {{
            type: 'number',
            value: '0',
            step: '1',
            checked: false,
            className: '',
            style: {{}},
            innerHTML: '',
            addEventListener: function(evt, fn) {{}},
            removeEventListener: function(evt, fn) {{}},
            appendChild: function(c) {{}},
            setAttribute: function(k, v) {{}},
            getAttribute: function(k) {{ return null; }},
            insertRow: function() {{
                return {{
                    rowIndex: -1,
                    cells: [],
                    insertCell: function() {{
                        var cell = {{
                            appendChild: function(c) {{}},
                            querySelector: function(sel) {{ return null; }}
                        }};
                        this.cells.push(cell);
                        return cell;
                    }}
                }};
            }},
            querySelector: function(sel) {{ return null; }},
            querySelectorAll: function(sel) {{ return []; }}
        }};
    }}
}};
global.alert = function(msg) {{ /* mock: no-op */ }};
global.confirm = function(msg) {{ return true; }};  // 默认确认
global.prompt = function(msg, defaultVal) {{ return defaultVal || ''; }};
global.window = global;
// 注意：不要 mock console，因为测试代码使用 console.log 输出结果

// ===== 应用代码 =====
{script}

// ===== 测试辅助 =====
var _testReports = [];
function report(value) {{
    _testReports.push(value);
}}

// 辅助：深拷贝对象用于比较
function _clone(obj) {{
    return JSON.parse(JSON.stringify(obj));
}}

// ===== 测试代码 =====
{test_code}

// ===== 输出结果 =====
console.log(JSON.stringify(_testReports));
"""

    # Windows 下 node -e 有命令行长度限制（~8191 字符），
    # 完整 JS 约 23000+ 字符，必须写入临时文件再执行。
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.js', delete=False, encoding='utf-8'
    ) as tmp:
        tmp.write(full_js)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [_NODE_PATH, tmp_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=timeout
        )
    finally:
        os.unlink(tmp_path)

    stdout = result.stdout or ''
    stderr = result.stderr or ''

    if result.returncode != 0:
        raise RuntimeError(
            f"JavaScript 执行失败 (exit={result.returncode}):\n"
            f"--- STDERR ---\n{stderr}\n"
            f"--- STDOUT ---\n{stdout}"
        )

    try:
        return json.loads(stdout.strip())
    except json.JSONDecodeError:
        raise RuntimeError(
            f"无法将 JS 输出解析为 JSON:\n"
            f"--- STDOUT ---\n{stdout}\n"
            f"--- STDERR ---\n{stderr}"
        )


# ── 便捷断言辅助 ──

class CoalCalcTestCase(unittest.TestCase):
    """基类：提供 run_js 快捷方法"""

    @staticmethod
    def js(test_code, timeout=15):
        """执行 JS 测试代码并返回结果列表。"""
        return run_js(test_code, timeout=timeout)

    @staticmethod
    def js1(test_code, timeout=15):
        """执行 JS 测试代码，返回第一个 report() 的值。"""
        results = run_js(test_code, timeout=timeout)
        if not results:
            raise RuntimeError("JS 测试代码未调用 report()，无返回值")
        return results[0]
