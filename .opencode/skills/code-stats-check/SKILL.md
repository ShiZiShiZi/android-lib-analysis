---
name: code-stats-check
description: "Count source lines of code across JavaScript/TypeScript, Android, and iOS layers in a React Native library"
metadata:
  category: "rn-analysis"
---

## Goal
统计 React Native 三方库各层源码规模，分四层：JavaScript/TypeScript、Android 原生、iOS 原生。

**路径约定**：以下所有命令均需在仓库根目录下执行，或显式指定仓库路径。

**排除规则**（所有层通用）：
- 测试代码：`__tests__/` `*.test.js` `*.test.ts` `*.spec.js` `*.spec.ts` `test/` `tests/`
- 示例代码：`example/` `examples/`
- 生成代码：`*.d.ts`（声明文件）
- 构建产物：`node_modules/` `dist/` `build/` `.gradle/` `Pods/`
- 配置文件：`*.config.js` `*.config.ts`（如 babel.config.js、metro.config.js）

**有效行计算**（排除空行和纯注释行）：
```bash
find <path> <filters> | xargs cat 2>/dev/null | grep -cEv '^\s*(//|/\*|\*+/|\*|<!--|$)'
```

每个语言条目格式：`{"files": N, "lines": N, "effective_lines": N}`，无该语言源码则为 `null`。

---

## Step 1 — JavaScript 层

```bash
# 文件数（src/ 递归 + 根目录顶层，去重）
{ find src/ -name "*.js" ! -name "*.config.js" ! -name "*.test.js" ! -name "*.spec.js" 2>/dev/null; \
  find . -maxdepth 1 -name "*.js" ! -name "*.config.js" ! -name "*.test.js" ! -name "*.spec.js" 2>/dev/null; } \
  | sort -u | wc -l

# 总行数
{ find src/ -name "*.js" ! -name "*.config.js" ! -name "*.test.js" ! -name "*.spec.js" 2>/dev/null; \
  find . -maxdepth 1 -name "*.js" ! -name "*.config.js" ! -name "*.test.js" ! -name "*.spec.js" 2>/dev/null; } \
  | sort -u | xargs cat 2>/dev/null | wc -l

# 有效行数
{ find src/ -name "*.js" ! -name "*.config.js" ! -name "*.test.js" ! -name "*.spec.js" 2>/dev/null; \
  find . -maxdepth 1 -name "*.js" ! -name "*.config.js" ! -name "*.test.js" ! -name "*.spec.js" 2>/dev/null; } \
  | sort -u | xargs cat 2>/dev/null | grep -cEv '^\s*(//|/\*|\*+/|\*|<!--|$)'
```

---

## Step 2 — TypeScript 层

```bash
# 文件数（src/ 递归 + 根目录顶层，排除 .d.ts，去重）
{ find src/ \( -name "*.ts" -o -name "*.tsx" \) ! -name "*.d.ts" ! -name "*.test.ts" ! -name "*.test.tsx" ! -name "*.spec.ts" ! -name "*.spec.tsx" 2>/dev/null; \
  find . -maxdepth 1 \( -name "*.ts" -o -name "*.tsx" \) ! -name "*.d.ts" ! -name "*.test.ts" ! -name "*.test.tsx" ! -name "*.spec.ts" ! -name "*.spec.tsx" 2>/dev/null; } \
  | sort -u | wc -l

# 总行数
{ find src/ \( -name "*.ts" -o -name "*.tsx" \) ! -name "*.d.ts" ! -name "*.test.ts" ! -name "*.test.tsx" ! -name "*.spec.ts" ! -name "*.spec.tsx" 2>/dev/null; \
  find . -maxdepth 1 \( -name "*.ts" -o -name "*.tsx" \) ! -name "*.d.ts" ! -name "*.test.ts" ! -name "*.test.tsx" ! -name "*.spec.ts" ! -name "*.spec.tsx" 2>/dev/null; } \
  | sort -u | xargs cat 2>/dev/null | wc -l

# 有效行数
{ find src/ \( -name "*.ts" -o -name "*.tsx" \) ! -name "*.d.ts" ! -name "*.test.ts" ! -name "*.test.tsx" ! -name "*.spec.ts" ! -name "*.spec.tsx" 2>/dev/null; \
  find . -maxdepth 1 \( -name "*.ts" -o -name "*.tsx" \) ! -name "*.d.ts" ! -name "*.test.ts" ! -name "*.test.tsx" ! -name "*.spec.ts" ! -name "*.spec.tsx" 2>/dev/null; } \
  | sort -u | xargs cat 2>/dev/null | grep -cEv '^\s*(//|/\*|\*+/|\*|<!--|$)'
```

---

## Step 3 — Android 原生层

分语言单独统计（搜索范围：`android/src/main/`）：

**Java：**
```bash
find android/src/main -name "*.java" 2>/dev/null | wc -l
find android/src/main -name "*.java" 2>/dev/null | xargs cat 2>/dev/null | wc -l
find android/src/main -name "*.java" 2>/dev/null | xargs cat 2>/dev/null | grep -cEv '^\s*(//|/\*|\*+/|\*|$)'
```

**Kotlin：**
```bash
find android/src/main -name "*.kt" 2>/dev/null | wc -l
find android/src/main -name "*.kt" 2>/dev/null | xargs cat 2>/dev/null | wc -l
find android/src/main -name "*.kt" 2>/dev/null | xargs cat 2>/dev/null | grep -cEv '^\s*(//|/\*|\*+/|\*|$)'
```

**C/C++（含 .h）：**
```bash
find android/ \( -name "*.c" -o -name "*.cpp" -o -name "*.cc" -o -name "*.h" \) \
  ! -path "*/.gradle/*" ! -path "*/build/*" ! -path "*/node_modules/*" 2>/dev/null | wc -l
find android/ \( -name "*.c" -o -name "*.cpp" -o -name "*.cc" -o -name "*.h" \) \
  ! -path "*/.gradle/*" ! -path "*/build/*" ! -path "*/node_modules/*" 2>/dev/null | xargs cat 2>/dev/null | wc -l
find android/ \( -name "*.c" -o -name "*.cpp" -o -name "*.cc" -o -name "*.h" \) \
  ! -path "*/.gradle/*" ! -path "*/build/*" ! -path "*/node_modules/*" 2>/dev/null \
  | xargs cat 2>/dev/null | grep -cEv '^\s*(//|/\*|\*+/|\*|$)'
```

---

## Step 4 — iOS 原生层

分语言单独统计（排除 `Pods/` `example/` `build/`）：

**Swift：**
```bash
find ios/ -name "*.swift" ! -path "*/Pods/*" ! -path "*/example/*" ! -path "*/build/*" 2>/dev/null | wc -l
find ios/ -name "*.swift" ! -path "*/Pods/*" ! -path "*/example/*" ! -path "*/build/*" 2>/dev/null | xargs cat 2>/dev/null | wc -l
find ios/ -name "*.swift" ! -path "*/Pods/*" ! -path "*/example/*" ! -path "*/build/*" 2>/dev/null | xargs cat 2>/dev/null | grep -cEv '^\s*(//|/\*|\*+/|\*|$)'
```

**ObjC / ObjC++（.m / .mm）：**
```bash
find ios/ \( -name "*.m" -o -name "*.mm" \) ! -path "*/Pods/*" ! -path "*/example/*" ! -path "*/build/*" 2>/dev/null | wc -l
find ios/ \( -name "*.m" -o -name "*.mm" \) ! -path "*/Pods/*" ! -path "*/example/*" ! -path "*/build/*" 2>/dev/null | xargs cat 2>/dev/null | wc -l
find ios/ \( -name "*.m" -o -name "*.mm" \) ! -path "*/Pods/*" ! -path "*/example/*" ! -path "*/build/*" 2>/dev/null | xargs cat 2>/dev/null | grep -cEv '^\s*(//|/\*|\*+/|\*|$)'
```

**Headers（.h）：**
```bash
find ios/ -name "*.h" ! -path "*/Pods/*" ! -path "*/example/*" ! -path "*/build/*" 2>/dev/null | wc -l
find ios/ -name "*.h" ! -path "*/Pods/*" ! -path "*/example/*" ! -path "*/build/*" 2>/dev/null | xargs cat 2>/dev/null | wc -l
find ios/ -name "*.h" ! -path "*/Pods/*" ! -path "*/example/*" ! -path "*/build/*" 2>/dev/null | xargs cat 2>/dev/null | grep -cEv '^\s*(//|/\*|\*+/|\*|$)'
```

---

## Step 5 — 公开 API 面积（JS/TS 对外暴露接口数）

使用 Node.js 解析 index.js / index.ts / src/index.ts 中的 export 语句：

```bash
python3 << 'PYEOF'
import re, json, sys
from pathlib import Path

# 优先从 package.json main/module/exports 字段确定入口
entry_candidates = []
pkg = Path('package.json')
if pkg.exists():
    try:
        meta = json.loads(pkg.read_text(errors='replace'))
        for field in ('main', 'module', 'source'):
            val = meta.get(field)
            if val and isinstance(val, str):
                entry_candidates.append(val)
    except Exception:
        pass

# 补充常见默认路径
entry_candidates += ['index.js', 'index.ts', 'src/index.ts', 'src/index.tsx', 'src/index.js']

# 去重并筛选存在的文件
entry_files = []
seen = set()
for p in entry_candidates:
    if p not in seen and Path(p).exists():
        entry_files.append(p)
        seen.add(p)

if not entry_files:
    print(json.dumps({"exported_modules": 0, "exported_functions": 0, "exported_classes": 0, "total_exports": 0}))
    sys.exit(0)

def strip_comments(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'//[^\n]*', '', text)
    return text

exported_modules = 0
exported_functions = 0
exported_classes = 0
total_exports = 0

for entry in entry_files:
    try:
        text = Path(entry).read_text(errors='replace')
        text = strip_comments(text)

        # export default（排除 class/function/async，避免与下面的规则重复计数）
        exported_modules += len(re.findall(r'export\s+default\s+(?!class\b|function\b|async\b)', text))
        # export * from 'module'
        exported_modules += len(re.findall(r'export\s+\*\s+from', text))

        # export function / export async function / export default function
        exported_functions += len(re.findall(r'export\s+(?:default\s+)?(?:async\s+)?function\s+\w+', text))
        # export const/let/var X = (...) =>
        exported_functions += len(re.findall(r'export\s+(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?\(', text))

        # export class / export default class
        exported_classes += len(re.findall(r'export\s+(?:default\s+)?class\s+\w+', text))

        # export { foo, bar as baz }
        named_exports = re.findall(r'export\s+\{([^}]+)\}', text)
        for ne in named_exports:
            exports = [e.strip() for e in ne.split(',') if e.strip()]
            total_exports += len(exports)

    except Exception:
        continue

total_exports += exported_modules + exported_functions + exported_classes

print(json.dumps({
    "exported_modules": exported_modules,
    "exported_functions": exported_functions,
    "exported_classes": exported_classes,
    "total_exports": total_exports
}, indent=2))
PYEOF
```

**字段说明**：
- `exported_modules`：`export default` 和 `export * from` 数量
- `exported_functions`：导出的函数数量（`export function` / `export const xxx = ()`）
- `exported_classes`：导出的类数量（`export class`）
- `total_exports`：对外暴露的可调用 API 总数

---

## Output

```json
{
  "javascript": {"files": 5, "lines": 820, "effective_lines": 680},
  "typescript": {"files": 12, "lines": 1840, "effective_lines": 1520},
  "android": {
    "java": null,
    "kotlin": {"files": 3, "lines": 420, "effective_lines": 380},
    "c_cpp": {"files": 5, "lines": 380, "effective_lines": 310}
  },
  "ios": {
    "swift": null,
    "objc": {"files": 4, "lines": 610, "effective_lines": 540},
    "headers": {"files": 2, "lines": 80, "effective_lines": 60}
  },
  "public_api": {
    "exported_modules": 3,
    "exported_functions": 42,
    "exported_classes": 8,
    "total_exports": 53
  }
}