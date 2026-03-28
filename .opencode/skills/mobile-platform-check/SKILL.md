---
name: mobile-platform-check
description: "Identify which mobile vendor platform a React Native library targets (HMS, GMS, XIAOMI, OPPO, VIVO, HONOR, MEIZU, AGGREGATOR, or NONE)"
metadata:
  category: "rn-analysis"
---

## Goal
识别 React Native 三方库属于哪个**手机厂商服务平台**。厂商专属库只能在该厂商设备/生态上运行，对其他设备不适用。

**路径约定**：以下所有命令均需在仓库根目录下执行，或显式指定仓库路径。

---

## Steps

### Step 1 — 检查 package.json 依赖包名

```bash
cat package.json 2>/dev/null
```

匹配 `dependencies` / `peerDependencies` 中的包名前缀/关键词：

| 包名关键词 | 信号 |
|------|------|
| `@react-native-hms/`、`react-native-hms-` | HMS |
| `@react-native-firebase/`、`react-native-firebase`、`@react-native-google-signin` | GMS |
| `react-native-xiaomi-`、`mipush-` | XIAOMI_OPEN |
| `react-native-vivo-`、`vivo-push` | VIVO_OPEN |

> `react-native-google-mobile-ads`、`react-native-maps`（Google Maps）→ GMS 信号

---

### Step 2 — 检查 Android build.gradle

```bash
cat android/build.gradle 2>/dev/null || cat android/app/build.gradle 2>/dev/null || echo "NO_ANDROID_BUILD"
find android/ \( -name "build.gradle" -o -name "build.gradle.kts" \) 2>/dev/null | head -5
```

搜索 gradle 插件声明和 maven 仓库地址：

```bash
grep -rn "google-services\|agcp\|agconnect\|play-services\|com\.huawei\|com\.xiaomi\|com\.vivo\|com\.hihonor\|com\.meizu\|com\.heytap\|com\.oppo" \
  android/ --include="*.gradle" --include="*.kts" 2>/dev/null | head -30
```

---

### Step 3 — 检查 JS/TS 源码 import 和 Native Modules

```bash
# 厂商 SDK import（JS/TS 层）
grep -rn "import.*@react-native-hms\|import.*@react-native-firebase\|import.*react-native-google-signin\|HmsInstanceId\|AppGallery" \
  --include="*.js" --include="*.ts" --include="*.tsx" \
  --exclude-dir=node_modules --exclude-dir=example --exclude-dir=dist . 2>/dev/null | head -20

# 厂商 SDK import（Java/Kotlin 原生层）
grep -rn "import com\.huawei\|import com\.google\.android\.gms\|import com\.google\.firebase\|HmsInstanceId\|AppGallery" \
  android/src/ --include="*.java" --include="*.kt" 2>/dev/null | head -20

grep -rn "import com\.xiaomi\|XiaomiPush\|MiPush\|import com\.vivo\|VivoPush\|import com\.hihonor\|HonorPush\|import com\.meizu\|MeizuPush\|import com\.heytap\|import com\.oppo\|OPPOPush" \
  android/src/ --include="*.java" --include="*.kt" 2>/dev/null | head -20

# 第三方聚合推送 SDK
grep -rn "umeng\|jiguang\|jpush\|getui\|rongcloud" \
  --include="*.js" --include="*.ts" --include="*.tsx" --include="*.java" --include="*.kt" \
  --exclude-dir=node_modules --exclude-dir=example -i . android/src/ 2>/dev/null | head -20

# Native Module 名称检测（React Native 特有）
grep -rn "NativeModules\.\|TurboModuleRegistry\|NativeEventEmitter" \
  --include="*.js" --include="*.ts" --include="*.tsx" \
  --exclude-dir=node_modules --exclude-dir=example . 2>/dev/null | head -20
```

---

### Step 4 — 判定逻辑

**单厂商判定**（按以下顺序逐一匹配，第一个命中即停止）：

| 优先级 | 条件 | 标签 |
| |------|------|
| 1 | 检测到 `com.huawei.*` / `agcp` / `agconnect` / `@react-native-hms` / `HmsInstanceId` | `HMS` |
| 2 | 检测到 `play-services-*` / `com.google.android.gms.*` / `@react-native-firebase` / `google-services` gradle 插件 | `GMS` |
| 3 | 检测到 `com.xiaomi.*` / `XiaomiPush` / `MiPush` / `react-native-xiaomi` | `XIAOMI_OPEN` |
| 4 | 检测到 `com.heytap.*` / `com.oppo.*` / `OPPOPush` / `heytap` | `OPPO_OPEN` |
| 5 | 检测到 `com.vivo.*` / `VivoPush` / `react-native-vivo` | `VIVO_OPEN` |
| 6 | 检测到 `com.hihonor.*` / `HonorPush` | `HONOR_OPEN` |
| 7 | 检测到 `com.meizu.*` / `MeizuPush` / `flyme` | `MEIZU_OPEN` |

**AGGREGATOR_PLATFORM 判定**（满足任意一项）：
- 上表中 ≥2 个不同厂商信号同时命中（库自身集成多厂商 SDK）
- 检测到友盟（`umeng`）/ 极光（`jiguang` / `jpush`）/ 个推（`getui`）/ 融云（`rongcloud`）等第三方聚合推送 SDK，且其目的是同时覆盖多厂商推送通道

> **注意区分**：若库功能本身就是推送聚合器（如封装多厂商推送通道），判 `AGGREGATOR_PLATFORM`；若库只是恰好将极光/友盟作为单一依赖用于自身功能（如 IM、分析），则按实际主要厂商或 `NONE` 判定。

**NONE**：无任何厂商特征，属于通用工具/UI/网络库等。

---

### Step 5 — confidence 判定

| confidence | 条件 |
|------------|------|
| `high` | package.json 包名前缀 或 build.gradle 中发现明确厂商声明 |
| `medium` | 仅在 Java/Kotlin/JS/TS 源码 import 或类名中发现 |
| `low` | 仅在注释、字符串常量或 README 中出现厂商关键词，无 import 或 gradle 配置 |

---

## Output

```json
{
  "mobile_platform": {
    "label": "HMS | GMS | XIAOMI_OPEN | OPPO_OPEN | VIVO_OPEN | HONOR_OPEN | MEIZU_OPEN | AGGREGATOR_PLATFORM | NONE",
    "confidence": "high | medium | low",
    "evidence": ["android/build.gradle:5 (apply plugin: 'com.huawei.agcp')", "package.json:12 (@react-native-hms/push: ^6.3.0)"]
  }
}