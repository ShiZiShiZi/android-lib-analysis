---
name: code-stats-check
description: "Count source lines of code across Java, Kotlin, and C/C++ layers in an Android library"
metadata:
  category: "android-analysis"
---

## Goal
统计 Android 三方库各层源码规模，分三层：Java、Kotlin、C/C++。

**路径约定**：以下所有命令均需在仓库根目录下执行，或显式指定仓库路径。

**排除规则**（所有层通用）：
- 测试代码：`test/` `tests/` `androidTest/` `*Test.java` `*Test.kt` `*Spec.java` `*Spec.kt`
- 示例代码：`example/` `examples/` `sample/` `samples/` `demo/`
- 构建产物：`build/` `.gradle/` `out/` `target/`
- 生成代码：`Generated.java` `*.generated.*`

**有效行计算**（排除空行和纯注释行）：
```bash
find <path> <filters> | xargs cat 2>/dev/null | grep -cEv '^\s*(//|/\*|\*+/|\*|$)'
```

每个语言条目格式：`{"files": N, "lines": N, "effective_lines": N}`，无该语言源码则为 `null`。

---

## Step 1 — Java 层

```bash
# 文件数
find . -name "*.java" ! -path "*/build/*" ! -path "*/.gradle/*" ! -path "*/test/*" ! -path "*/androidTest/*" ! -path "*/example/*" ! -path "*/sample/*" ! -name "*Test.java" ! -name "*Spec.java" 2>/dev/null | wc -l

# 总行数
find . -name "*.java" ! -path "*/build/*" ! -path "*/.gradle/*" ! -path "*/test/*" ! -path "*/androidTest/*" ! -path "*/example/*" ! -path "*/sample/*" ! -name "*Test.java" ! -name "*Spec.java" 2>/dev/null | xargs cat 2>/dev/null | wc -l

# 有效行数
find . -name "*.java" ! -path "*/build/*" ! -path "*/.gradle/*" ! -path "*/test/*" ! -path "*/androidTest/*" ! -path "*/example/*" ! -path "*/sample/*" ! -name "*Test.java" ! -name "*Spec.java" 2>/dev/null | xargs cat 2>/dev/null | grep -cEv '^\s*(//|/\*|\*+/|\*|$)'
```

---

## Step 2 — Kotlin 层

```bash
# 文件数
find . -name "*.kt" ! -path "*/build/*" ! -path "*/.gradle/*" ! -path "*/test/*" ! -path "*/androidTest/*" ! -path "*/example/*" ! -path "*/sample/*" ! -name "*Test.kt" ! -name "*Spec.kt" 2>/dev/null | wc -l

# 总行数
find . -name "*.kt" ! -path "*/build/*" ! -path "*/.gradle/*" ! -path "*/test/*" ! -path "*/androidTest/*" ! -path "*/example/*" ! -path "*/sample/*" ! -name "*Test.kt" ! -name "*Spec.kt" 2>/dev/null | xargs cat 2>/dev/null | wc -l

# 有效行数
find . -name "*.kt" ! -path "*/build/*" ! -path "*/.gradle/*" ! -path "*/test/*" ! -path "*/androidTest/*" ! -path "*/example/*" ! -path "*/sample/*" ! -name "*Test.kt" ! -name "*Spec.kt" 2>/dev/null | xargs cat 2>/dev/null | grep -cEv '^\s*(//|/\*|\*+/|\*|$)'
```

---

## Step 3 — C/C++ 层

```bash
# 文件数（含 .h 头文件）
find . \( -name "*.c" -o -name "*.cpp" -o -name "*.cc" -o -name "*.cxx" -o -name "*.h" -o -name "*.hpp" \) \
  ! -path "*/build/*" ! -path "*/.gradle/*" ! -path "*/test/*" ! -path "*/example/*" ! -path "*/sample/*" 2>/dev/null | wc -l

# 总行数
find . \( -name "*.c" -o -name "*.cpp" -o -name "*.cc" -o -name "*.cxx" -o -name "*.h" -o -name "*.hpp" \) \
  ! -path "*/build/*" ! -path "*/.gradle/*" ! -path "*/test/*" ! -path "*/example/*" ! -path "*/sample/*" 2>/dev/null | xargs cat 2>/dev/null | wc -l

# 有效行数
find . \( -name "*.c" -o -name "*.cpp" -o -name "*.cc" -o -name "*.cxx" -o -name "*.h" -o -name "*.hpp" \) \
  ! -path "*/build/*" ! -path "*/.gradle/*" ! -path "*/test/*" ! -path "*/example/*" ! -path "*/sample/*" 2>/dev/null | xargs cat 2>/dev/null | grep -cEv '^\s*(//|/\*|\*+/|\*|$)'
```

---

## Step 4 — 公开 API 面积（公开类和方法数）

使用 Python 解析 Java/Kotlin 源码中的公开类和方法：

```bash
python3 << 'PYEOF'
import re, json, sys
from pathlib import Path

def find_source_files():
    java_files = []
    kotlin_files = []
    for p in Path('.').rglob('*.java'):
        if any(x in str(p) for x in ['build', '.gradle', 'test', 'androidTest', 'example', 'sample']):
            continue
        if p.name.endswith('Test.java') or p.name.endswith('Spec.java'):
            continue
        java_files.append(str(p))
    for p in Path('.').rglob('*.kt'):
        if any(x in str(p) for x in ['build', '.gradle', 'test', 'androidTest', 'example', 'sample']):
            continue
        if p.name.endswith('Test.kt') or p.name.endswith('Spec.kt'):
            continue
        kotlin_files.append(str(p))
    return java_files, kotlin_files

def strip_comments(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'[^\n]*//.*', '', text)
    return text

exported_classes = 0
exported_methods = 0

java_files, kotlin_files = find_source_files()

# Java: public class/interface + public methods
for f in java_files:
    try:
        text = Path(f).read_text(errors='replace')
        text = strip_comments(text)
        # public class/interface/enum
        exported_classes += len(re.findall(r'public\s+(?:abstract\s+|final\s+)?(?:class|interface|enum)\s+\w+', text))
        # public methods (excluding class declarations)
        exported_methods += len(re.findall(r'public\s+(?:static\s+|synchronized\s+|native\s+|abstract\s+|final\s+)?(?:[\w<>\[\],\s]+\s+)?\w+\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{?', text))
    except Exception:
        continue

# Kotlin: class/interface/object + fun
for f in kotlin_files:
    try:
        text = Path(f).read_text(errors='replace')
        text = strip_comments(text)
        # public/open class/interface/object
        exported_classes += len(re.findall(r'(?:public\s+|open\s+|abstract\s+|sealed\s+)?(?:class|interface|object|data\s+class|enum\s+class)\s+\w+', text))
        # public fun
        exported_methods += len(re.findall(r'(?:public\s+|open\s+|override\s+|suspend\s+)?(?:inline\s+|inline\s+crossinline\s+)?fun\s+\w+\s*[<(]', text))
    except Exception:
        continue

total_exports = exported_classes + exported_methods

print(json.dumps({
    "exported_classes": exported_classes,
    "exported_methods": exported_methods,
    "total_exports": total_exports
}, indent=2))
PYEOF
```

**字段说明**：
- `exported_classes`：公开的类/接口/枚举数量（Java `public class`、Kotlin `class`/`interface`/`object`）
- `exported_methods`：公开的方法数量（Java `public method`、Kotlin `fun`）
- `total_exports`：对外暴露的 API 总数

---

## Output

```json
{
  "java": {"files": 25, "lines": 4200, "effective_lines": 3500},
  "kotlin": {"files": 12, "lines": 1800, "effective_lines": 1520},
  "c_cpp": {"files": 5, "lines": 380, "effective_lines": 310},
  "public_api": {
    "exported_classes": 15,
    "exported_methods": 120,
    "total_exports": 135
  }
}