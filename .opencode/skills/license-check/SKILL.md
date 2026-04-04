---
name: license-check
description: "Identify license type and classify into four categories for an Android library"
metadata:
  category: "android-analysis"
---

## Goal
识别 Android 三方库的 License 类型，归入四分类之一。

## Steps

### Step 1 — 读取 LICENSE 文件

```bash
ls LICENSE* 2>/dev/null
cat LICENSE 2>/dev/null || cat LICENSE.md 2>/dev/null || cat LICENSE.txt 2>/dev/null || echo "NO_LICENSE_FILE"
```

### Step 2 — 读取 README 和 build.gradle

```bash
head -100 README.md 2>/dev/null || head -100 readme.md 2>/dev/null || echo "NO_README"
cat build.gradle 2>/dev/null | head -50 || cat build.gradle.kts 2>/dev/null | head -50 || echo "NO_BUILD_GRADLE"
```

从 README 或 build.gradle 中提取 license 信息：
- README 中常见的 license 声明格式：`License: MIT`、`Licensed under the Apache License`
- gradle.properties 中可能有 `POM_LICENSE_NAME` 或类似字段

```bash
cat gradle.properties 2>/dev/null | grep -i license | head -10
```

### Step 3 — 四分类归类

| category | 说明 | 典型协议 |
|----------|------|---------|
| `permissive` | 宽松友好 | MIT、Apache-2.0、BSD-2-Clause、BSD-3-Clause、ISC、Unlicense、CC0-1.0、Zlib、PSF |
| `copyleft` | 有传染性 | GPL-2.0、GPL-3.0、AGPL-3.0、LGPL-2.1、LGPL-3.0、MPL-2.0、EUPL-1.2 |
| `proprietary` | 专有许可 | LICENSE 含 `proprietary` / `all rights reserved` / `commercial` 等字样；闭源商业 SDK 用户协议 |
| `undeclared` | 未声明 | 无 LICENSE 文件且无法识别为任何已知协议 |

## Output

```json
{
  "declared_license": "MIT",
  "category": "permissive",
  "evidence": ["LICENSE:1 (MIT License)"]
}