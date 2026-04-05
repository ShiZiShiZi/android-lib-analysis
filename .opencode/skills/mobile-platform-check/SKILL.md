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

### Step 3a — 检测服务类型

检测 7 种服务类型，统计每种类型下的厂商/平台数量。

**支付服务**：
```bash
grep -rn "play-services-wallet\|play-services-pay\|apple-pay\|ApplePay\|alipay\|wechatpay\|wechat-pay\|paypal\|stripe" \
  --include="*.gradle" --include="*.kts" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/" | head -30
```

**推送服务**：
```bash
grep -rn "firebase-messaging\|com\.huawei\.hms:push\|com\.xiaomi.*push\|MiPush\|com\.heytap\|com\.oppo.*push\|com\.vivo.*push\|VivoPush\|com\.hihonor.*push\|HonorPush\|com\.meizu.*push\|MeizuPush" \
  --include="*.gradle" --include="*.kts" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/" | head -30
```

**地图服务**：
```bash
grep -rn "play-services-maps\|com\.amap\|amap\|baidu.*map\|tencent.*map\|TencentMap" \
  --include="*.gradle" --include="*.kts" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/" | head -30
```

**登录服务**：
```bash
grep -rn "play-services-auth\|facebook.*login\|FacebookSdk\|wechat.*login\|qq.*login\|Tencent.*login\|apple.*sign\|SignInWithApple" \
  --include="*.gradle" --include="*.kts" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/" | head -30
```

**广告服务**：
```bash
grep -rn "play-services-ads\|facebook.*ads\|pangle\|bytedance.*ads\|gromore\|kuaishou.*ads\|优量汇\|admob\|AdMob" \
  --include="*.gradle" --include="*.kts" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/" | head -30
```

**分享服务**：
```bash
grep -rn "wechat.*share\|qq.*share\|Tencent.*share\|weibo.*share\|facebook.*share\|share.*sdk" \
  --include="*.gradle" --include="*.kts" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/" | head -30
```

**IM 服务**：
```bash
grep -rn "easemob\|rongyun\|jmessage\|jiguang.*im\|nim\|网易云信" \
  --include="*.gradle" --include="*.kts" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/" | head -30
```

**服务类型识别规则**：

| 服务类型 | 厂商/平台信号 |
|---------|-------------|
| **支付** | Google Pay, Apple Pay, 支付宝, 微信支付, PayPal, Stripe |
| **推送** | FCM, HMS推送, 小米推送, OPPO推送, vivo推送, 荣耀推送, 魅族推送 |
| **地图** | Google Maps, 高德地图, 百度地图, 腾讯地图 |
| **登录** | Google登录, Facebook登录, 微信登录, QQ登录, Apple登录 |
| **广告** | AdMob, Facebook Ads, 穿山甲, GroMore, 快手广告, 优量汇 |
| **分享** | 微信分享, QQ分享, 微博分享, Facebook分享 |
| **IM** | 环信, 融云, 极光IM, 网易云信 |

**统计规则**：
- 统计每种服务类型下检测到的不同厂商/平台数量（count）
- 记录具体的厂商/平台名称（providers）

---

### Step 4 — 判定逻辑

**优先级顺序**：聚合库判定 → 单厂商判定 → NONE

---

**优先级 0：AGGREGATOR_PLATFORM 判定**（最高优先级）

基于 Step 3a 检测的服务类型统计结果，若**任意服务类型**下检测到 **≥2 个不同厂商/平台**，判定为 `AGGREGATOR_PLATFORM`。

**判定规则**：

| 服务类型 | 聚合判定条件 |
|---------|-------------|
| 支付 | ≥2 种支付平台（Google Pay + 支付宝 + 微信支付 等） |
| 推送 | ≥2 个厂商推送（FCM + HMS + 小米推送 等） |
| 地图 | ≥2 种地图平台（Google Maps + 高德 + 百度 等） |
| 登录 | ≥2 种登录平台（Google登录 + Facebook登录 + 微信登录 等） |
| 广告 | ≥2 种广告平台（AdMob + Facebook Ads + 穿山甲 等） |
| 分享 | ≥2 种分享平台（微信分享 + QQ分享 + 微博分享 等） |
| IM | ≥2 种IM平台（环信 + 融云 + 极光IM 等） |

**第三方聚合推送 SDK**（单独判定）：
- 友盟（`umeng`）
- 极光（`jiguang` / `jpush`）
- 个推（`getui`）
- 融云（`rongcloud`）

**evidence 格式**：
```
[
  "<文件路径> (<厂商服务> - <服务类型>)",
  "<文件路径> (<厂商服务> - <服务类型>)",
  "检测到 N 种<服务类型>，判定为聚合库"
]
```

---

**优先级 1-7：单厂商判定**

若未命中 AGGREGATOR_PLATFORM，按以下顺序逐一匹配（第一个命中即停止）：

| 优先级 | 条件 | 标签 |
|--------|------|------|
| 1 | 检测到 `com.huawei.*` / `agcp` / `agconnect` / `HmsInstanceId` | `HMS` |
| 2 | 检测到 `play-services-*` / `com.google.android.gms.*` / `com.google.firebase.*` / `google-services` 插件 | `GMS` |
| 3 | 检测到 `com.xiaomi.*` / `XiaomiPush` / `MiPush` | `XIAOMI_OPEN` |
| 4 | 检测到 `com.heytap.*` / `com.oppo.*` / `OPPOPush` | `OPPO_OPEN` |
| 5 | 检测到 `com.vivo.*` / `VivoPush` | `VIVO_OPEN` |
| 6 | 检测到 `com.hihonor.*` / `HonorPush` | `HONOR_OPEN` |
| 7 | 检测到 `com.meizu.*` / `MeizuPush` | `MEIZU_OPEN` |

**说明**：单厂商绑定意味着库的核心功能依赖该厂商服务，只能在该厂商设备上运行。

---

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

**重要**：此 skill 输出包含两个部分：
1. `mobile_platform`：最终判定结果
2. `detected_services`：检测到的服务类型（中间结果，供 ecosystem-check 使用）

---

**示例 1：支付聚合库**
```json
{
  "mobile_platform": {
    "label": "AGGREGATOR_PLATFORM",
    "confidence": "high",
    "evidence": [
      "googlepay/build.gradle:41 (play-services-wallet - Google Pay - 支付)",
      "alipay/build.gradle:28 (alipay-sdk - 支付宝 - 支付)",
      "wechatpay/build.gradle:35 (wechatpay-sdk - 微信支付 - 支付)",
      "检测到 3 种支付服务，判定为聚合库"
    ]
  },
  "detected_services": {
    "payment": {
      "count": 3,
      "providers": ["Google Pay", "支付宝", "微信支付"],
      "evidence": [
        "googlepay/build.gradle:41 (play-services-wallet - Google Pay)",
        "alipay/build.gradle:28 (alipay-sdk - 支付宝)",
        "wechatpay/build.gradle:35 (wechatpay-sdk - 微信支付)"
      ]
    },
    "push": {"count": 0, "providers": [], "evidence": []},
    "map": {"count": 0, "providers": [], "evidence": []},
    "account_login": {"count": 0, "providers": [], "evidence": []},
    "ads": {"count": 0, "providers": [], "evidence": []},
    "share": {"count": 0, "providers": [], "evidence": []},
    "im": {"count": 0, "providers": [], "evidence": []}
  }
}
```

**示例 2：地图聚合库**
```json
{
  "mobile_platform": {
    "label": "AGGREGATOR_PLATFORM",
    "confidence": "high",
    "evidence": [
      "build.gradle:35 (play-services-maps - Google Maps - 地图)",
      "build.gradle:42 (com.amap:map - 高德地图 - 地图)",
      "检测到 2 种地图服务，判定为聚合库"
    ]
  },
  "detected_services": {
    "payment": {"count": 0, "providers": [], "evidence": []},
    "push": {"count": 0, "providers": [], "evidence": []},
    "map": {
      "count": 2,
      "providers": ["Google Maps", "高德地图"],
      "evidence": [
        "build.gradle:35 (play-services-maps - Google Maps)",
        "build.gradle:42 (com.amap:map - 高德地图)"
      ]
    },
    "account_login": {"count": 0, "providers": [], "evidence": []},
    "ads": {"count": 0, "providers": [], "evidence": []},
    "share": {"count": 0, "providers": [], "evidence": []},
    "im": {"count": 0, "providers": [], "evidence": []}
  }
}
```

**示例 3：单厂商绑定（GMS）**
```json
{
  "mobile_platform": {
    "label": "GMS",
    "confidence": "high",
    "evidence": [
      "build.gradle:5 (apply plugin: 'com.google.gms.google-services')",
      "build.gradle:28 (com.google.firebase:firebase-messaging:23.0.0)"
    ]
  },
  "detected_services": {
    "payment": {"count": 0, "providers": [], "evidence": []},
    "push": {
      "count": 1,
      "providers": ["FCM"],
      "evidence": ["build.gradle:28 (com.google.firebase:firebase-messaging)"]
    },
    "map": {"count": 0, "providers": [], "evidence": []},
    "account_login": {"count": 0, "providers": [], "evidence": []},
    "ads": {"count": 0, "providers": [], "evidence": []},
    "share": {"count": 0, "providers": [], "evidence": []},
    "im": {"count": 0, "providers": [], "evidence": []}
  }
}
```

**示例 4：无厂商绑定**
```json
{
  "mobile_platform": {
    "label": "NONE",
    "confidence": "high",
    "evidence": []
  },
  "detected_services": {
    "payment": {"count": 0, "providers": [], "evidence": []},
    "push": {"count": 0, "providers": [], "evidence": []},
    "map": {"count": 0, "providers": [], "evidence": []},
    "account_login": {"count": 0, "providers": [], "evidence": []},
    "ads": {"count": 0, "providers": [], "evidence": []},
    "share": {"count": 0, "providers": [], "evidence": []},
    "im": {"count": 0, "providers": [], "evidence": []}
  }
}
```