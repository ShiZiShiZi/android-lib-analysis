---
name: mobile-platform-check
description: "Identify which mobile vendor platform an Android library targets (HMS, GMS, XIAOMI, OPPO, VIVO, HONOR, MEIZU, AGGREGATOR, or NONE)"
metadata:
  category: "android-analysis"
---

## Goal
识别 Android 三方库属于哪个**手机厂商服务平台**。厂商专属库只能在该厂商设备/生态上运行，对其他设备不适用。

**路径约定**：以下所有命令均需在仓库根目录下执行，或显式指定仓库路径。

---

## Steps

### Step 1 — 检查 build.gradle 依赖

```bash
cat build.gradle 2>/dev/null || cat build.gradle.kts 2>/dev/null || echo "NO_BUILD_GRADLE"
find . \( -name "build.gradle" -o -name "build.gradle.kts" \) ! -path "*/.gradle/*" ! -path "*/build/*" 2>/dev/null | head -10
```

搜索 gradle 插件声明和 Maven 依赖：

```bash
grep -rn "google-services\|agcp\|agconnect\|play-services\|com\.huawei\|com\.xiaomi\|com\.vivo\|com\.hihonor\|com\.meizu\|com\.heytap\|com\.oppo\|com\.google\.android\.gms\|com\.google\.firebase" \
  --include="*.gradle" --include="*.kts" . 2>/dev/null | grep -v "build/" | head -30
```

---

### Step 2 — 检查 AndroidManifest.xml

```bash
find . -name "AndroidManifest.xml" ! -path "*/build/*" ! -path "*/.gradle/*" 2>/dev/null | head -5
grep -rn "huawei\|xiaomi\|vivo\|oppo\|heytap\|hihonor\|meizu\|google.*play\|firebase" --include="*.xml" . 2>/dev/null | grep -v "build/" | head -20
```

---

### Step 3 — 检查 Java/Kotlin 源码 import

```bash
grep -rn "import com\.huawei\|import com\.google\.android\.gms\|import com\.google\.firebase\|HmsInstanceId\|AppGallery" \
  --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/" | head -20

grep -rn "import com\.xiaomi\|XiaomiPush\|MiPush\|import com\.vivo\|VivoPush\|import com\.hihonor\|HonorPush\|import com\.meizu\|MeizuPush\|import com\.heytap\|import com\.oppo\|OPPOPush" \
  --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/" | head -20

grep -rn "umeng\|jiguang\|jpush\|getui\|rongcloud" \
  --include="*.java" --include="*.kt" --include="*.gradle" . 2>/dev/null | grep -v "build/" | head -20
```

---

### Step 4 — 判定逻辑

**单厂商判定**（按以下顺序逐一匹配，第一个命中即停止）：

| 优先级 | 条件 | 标签 |
| |------|------|
| 1 | 检测到 `com.huawei.*` / `agcp` / `agconnect` / `HmsInstanceId` | `HMS` |
| 2 | 检测到 `play-services-*` / `com.google.android.gms.*` / `com.google.firebase.*` / `google-services` gradle 插件 | `GMS` |
| 3 | 检测到 `com.xiaomi.*` / `XiaomiPush` / `MiPush` | `XIAOMI_OPEN` |
| 4 | 检测到 `com.heytap.*` / `com.oppo.*` / `OPPOPush` / `heytap` | `OPPO_OPEN` |
| 5 | 检测到 `com.vivo.*` / `VivoPush` | `VIVO_OPEN` |
| 6 | 检测到 `com.hihonor.*` / `HonorPush` | `HONOR_OPEN` |
| 7 | 检测到 `com.meizu.*` / `MeizuPush` / `flyme` | `MEIZU_OPEN` |

**AGGREGATOR_PLATFORM 判定**（满足任意一项）：
- 上表中 ≥2 个不同厂商信号同时命中（库自身集成多厂商 SDK）
- 检测到友盟（`umeng`）/ 极光（`jiguang` / `jpush`）/ 个推（`getui`）/ 融云（`rongcloud`）等第三方聚合推送 SDK

**NONE**：无任何厂商特征，属于通用工具/UI/网络库等。

---

### Step 5 — confidence 判定

| confidence | 条件 |
|------------|------|
| `high` | build.gradle 中发现明确厂商 Maven 依赖或插件声明 |
| `medium` | 仅在 Java/Kotlin 源码 import 或类名中发现 |
| `low` | 仅在注释、字符串常量或 README 中出现厂商关键词，无 import 或 gradle 配置 |

---

## Output

```json
{
  "mobile_platform": {
    "label": "HMS | GMS | XIAOMI_OPEN | OPPO_OPEN | VIVO_OPEN | HONOR_OPEN | MEIZU_OPEN | AGGREGATOR_PLATFORM | NONE",
    "confidence": "high | medium | low",
    "evidence": ["build.gradle:5 (apply plugin: 'com.huawei.agcp')", "build.gradle:28 (com.huawei.hms:push:6.3.0)"]
  }
}