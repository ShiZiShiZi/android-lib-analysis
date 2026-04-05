---
name: monorepo-detection
description: "Detect monorepo structure, identify sub-modules, and filter out non-code modules"
metadata:
  category: "android-analysis"
---

## Goal
检测仓库是否为 monorepo，识别所有子模块，过滤无代码模块（如 bom、sample、demo 等）。

**此 skill 为前置 skill，在其他八步分析之前执行。**

---

## Steps

### Step 1 — 检测 settings.gradle

```bash
cat settings.gradle 2>/dev/null || cat settings.gradle.kts 2>/dev/null || echo "NOT_MONOREPO"
```

**判定规则**：
- 若文件存在且包含 `include ':module-name'` 或 `include("module-name")` → `is_monorepo = true`
- 若文件不存在或无 include 声明 → `is_monorepo = false`

---

### Step 2 — 提取子模块列表

从 settings.gradle/settings.gradle.kts 解析所有 include 的模块名：

**Groovy DSL（settings.gradle）**：
```groovy
include ':app'
include ':library'
include ':bom'
project(':bom').projectDir = new File('bom-dir')
```

**Kotlin DSL（settings.gradle.kts）**：
```kotlin
include(":app")
include(":library")
include(":bom")
```

**提取规则**：
- 使用正则匹配 `include\s+['":]([^'":\s]+)['":]` 或 `include\s*\(\s*['":]([^'":\s]+)['":]\s*\)`
- 提取模块名（去除 `:` 前缀）
- 若有 `projectDir` 指定，记录实际目录名

---

### Step 3 — 检查子模块是否存在源码目录

对每个识别到的子模块，检查是否存在源码：

```bash
# 对每个模块执行
ls <module_name>/src/main/java 2>/dev/null || ls <module_name>/src/main/kotlin 2>/dev/null || echo "NO_SOURCE"
```

**判定规则**：
- 存在 `src/main/java` 或 `src/main/kotlin` → 有效模块（加入 `sub_modules_analyzed`）
- 不存在源码目录 → 无效模块（加入 `skipped_modules`）

---

### Step 4 — 按模块名过滤无代码模块

即使有源码目录，以下模块名也应跳过：

| 模块名模式 | 跳过原因 |
|-----------|---------|
| `*bom*` | BOM 依赖管理，无实际代码 |
| `*sample*` / `*demo*` / `*example*` | 示例代码 |
| `*test-utils*` / `*test-lib*` | 测试辅助库 |
| `buildSrc` | Gradle 构建脚本 |
| `gradle-plugin*` | Gradle 插件（通常不作为库分析） |
| `*benchmark*` | 性能测试模块 |

**过滤命令**：
```bash
# 检查模块名是否匹配跳过模式
echo "<module_name>" | grep -E 'bom|sample|demo|example|test-utils|test-lib|buildSrc|gradle-plugin|benchmark'
```

---

### Step 5 — 读取根目录 LICENSE（顺手读取）

读取仓库根目录的 LICENSE 文件，供后续聚合使用：

```bash
cat LICENSE 2>/dev/null || cat LICENSE.md 2>/dev/null || cat LICENSE.txt 2>/dev/null || echo "NO_ROOT_LICENSE"
```

**输出 root_license 结构**：
```json
{
  "declared_license": "Apache-2.0",
  "category": "permissive",
  "evidence": ["LICENSE:1"]
}
```

---

## Output

```json
{
  "is_monorepo": true,
  "monorepo_metadata": {
    "root_path": "/path/to/repos/okhttp",
    "sub_modules_found": ["okhttp", "okhttp-bom", "okhttp-logging-interceptor", "okhttp-sse", "sample"],
    "sub_modules_analyzed": ["okhttp", "okhttp-logging-interceptor", "okhttp-sse"],
    "skipped_modules": [
      {"name": "okhttp-bom", "reason": "bom_metadata_no_source"},
      {"name": "sample", "reason": "example_demo_code"}
    ]
  },
  "root_license": {
    "declared_license": "Apache-2.0",
    "category": "permissive",
    "evidence": ["LICENSE:1 (Apache License 2.0)"]
  }
}
```

**字段说明**：
- `is_monorepo`：布尔值，是否为 monorepo
- `sub_modules_found`：settings.gradle 中声明的所有模块名
- `sub_modules_analyzed`：有效模块列表（需分析的模块）
- `skipped_modules`：跳过的模块列表及原因
- `root_license`：根目录 License 信息（供后续聚合使用）

---

## 单库场景（is_monorepo=false）

若检测结果为单库（无 settings.gradle 或无 include），输出：

```json
{
  "is_monorepo": false,
  "monorepo_metadata": {
    "root_path": "/path/to/repos/retrofit",
    "sub_modules_found": [],
    "sub_modules_analyzed": [],
    "skipped_modules": []
  },
  "root_license": {
    "declared_license": "Apache-2.0",
    "category": "permissive",
    "evidence": ["LICENSE:1"]
  },
  "single_module_path": "/path/to/repos/retrofit"
}
```

单库场景下，后续分析直接在 `single_module_path` 下执行八步分析。