---
name: ecosystem-check
description: "Identify ecosystem-sensitive capability categories in an Android library and distinguish single vs aggregated implementations"
metadata:
  category: "android-analysis"
---

## Goal

基于前序 **mobile-platform-check** 和 **features-check** 的分析结论，识别库是否涉及以下生态敏感型能力，并区分**单一接入**还是**聚合接入**。

| category | label | 说明 |
|----------|-------|------|
| `ads` | 广告 | 广告变现 SDK |
| `account_login` | 账号登录 | 第三方登录 / 一键登录 |
| `payment` | 支付 | 支付渠道 SDK |
| `map` | 地图 | 地图服务 SDK |
| `cashier` | 收银台 | 聚合支付 UI 层 |
| `web_engine` | Web 内核 | 系统 WebView 或第三方内核 |
| `hot_update` | 热更新 | 动态字节码加载 / 热修复 |
| `ime` | 输入法 | 第三方输入法 SDK |

---

## 检测策略

**优先读取 mobile-platform-check 的 detected_services**（避免重复检测）：
- 支付、广告、登录、地图等服务类型已在 mobile-platform-check 中检测

**仅对以下四类执行补充 grep**（detected_services 未覆盖）：
- Web 内核
- 输入法
- 收银台
- 热更新

---

## Step 1 — 优先读取 detected_services

**若前序 mobile-platform-check 已输出 `detected_services`，则直接使用**：

**支付（payment）**
- 读取 `detected_services.payment`
- `count ≥ 2` → **聚合**
- `count = 1` → **单一**
- `count = 0` → 未命中

**广告（ads）**
- 读取 `detected_services.ads`
- `count ≥ 2` → **聚合**
- `count = 1` → **单一**
- `count = 0` → 未命中

**账号登录（account_login）**
- 读取 `detected_services.account_login`
- `count ≥ 2` → **聚合**
- `count = 1` → **单一**
- `count = 0` → 未命中

**地图（map）**
- 读取 `detected_services.map`
- `count ≥ 2` → **聚合**
- `count = 1` → **单一**
- `count = 0` → 未命中

---

**若 detected_services 不存在**，则从 features-check 结论推导：

**广告（ads）**
- `taxonomy1.categories` 含 `ads` → 命中
- 统计 `taxonomy1.tags` 中的广告网络数量：
  `admob` / `pangle` / `unity_ads` / `facebook_ads` / `applovin` / `ironsource` / `mintegral` / `vungle` / `chartboost`
  - 出现 `topon` / `gromore` → **聚合**
  - 广告网络 tags ≥ 2 → **聚合**
  - 广告网络 tags = 1 → **单一**

**账号登录（account_login）**
- `taxonomy1.categories` 含 `auth_security` → 命中
- 统计 `taxonomy1.tags` 中的登录方式数量：
  `google_sign_in` / `apple_sign_in` / `wechat_auth` / `phone_auth` / `oauth2` / `firebase_auth` / `two_factor_auth`
  - 登录方式 tags ≥ 2 → **聚合**
  - 登录方式 tags = 1 → **单一**

**支付（payment）**
- `taxonomy1.categories` 含 `payment` → 命中
- 统计 `taxonomy1.tags` 中的支付渠道数量：
  `alipay` / `wechat_pay` / `stripe` / `apple_pay` / `google_pay` / `unionpay` / `razorpay` / `paypal` / `paytm`
  - 支付渠道 tags ≥ 2 → **聚合支付**
  - 支付渠道 tags = 1 → **单一支付**

**地图（map）**
- `taxonomy1.categories` 含 `map_location` → 命中
- 统计 `taxonomy1.tags` 中的地图平台数量：
  `google_maps` / `amap` / `baidu_maps` / `tencent_maps`
  - 地图平台 tags ≥ 2 → **聚合**
  - 地图平台 tags = 1 → **单一**

**热更新（hot_update）**
- `android_permissions.PROHIBITED` 含 `DexClassLoader` / `PathClassLoader` / `BaseDexClassLoader` → 命中
- 热更新无单一/聚合之分，type 固定填 `single`

---

## Step 2 — 补充 grep（仅针对 detected_services 未覆盖的四类）

```bash
EXCL="--exclude-dir=build --exclude-dir=.gradle --exclude-dir=test --exclude-dir=example --exclude-dir=sample"

# web 内核（系统 WebView）
grep -r "WebView\|WebSettings\|WebViewClient\|JsBridge" \
  --include="*.java" --include="*.kt" --include="*.xml" -l -i $EXCL . 2>/dev/null

# web 内核（第三方：腾讯 X5、UC 内核等）
grep -r "TBSWebView\|X5WebView\|QBSdk\|tbs_sdk\|UCWebView\|crosswalk\|XWalkView" \
  --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL . 2>/dev/null

# 输入法 SDK
grep -r "SogouIME\|BaiduIME\|iFlyIME\|sogou.*input\|baidu.*input\|iflytek.*input\|InputMethodService" \
  --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL . 2>/dev/null

# 收银台（聚合支付 UI 层）
grep -r "cashier\|收银台\|PaymentSheet\|CheckoutUI\|checkout.*sdk\|payment.*cashier\|CashierActivity\|PayUI" \
  --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL . 2>/dev/null

# Android 热修复框架
grep -r "Robust\|Tinker\|AndFix\|Nuwa\|Amigo\|Hotfix\|Sophix\|Aceso\|InstantRun\|patch\|hotfix" \
  --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL . 2>/dev/null
```

**grep 结果判定：**
- WebView 命中（无 X5/UC）→ type=`system`
- web 内核命中 X5/UC → type=`third_party`；同时命中 WebView → type=`aggregated`
- 输入法命中 → type=`single`
- 收银台命中 → type=`aggregated`（收银台本身即聚合形态）
- 热修复框架命中 → type=`single`

---

## 单一 vs 聚合 判定总表

| 类别 | single（单一接入）| aggregated（聚合接入）|
|------|----------------|-------------------|
| 广告 | 仅 1 个广告网络 | ≥2 个广告网络，或含 TopOn / Gromore 等 mediation |
| 账号登录 | 仅 1 种登录方式 | ≥2 种登录方式 |
| 支付 | 仅 1 个支付渠道 | ≥2 个支付渠道 |
| 地图 | 仅 1 种地图平台 | ≥2 种地图平台 |
| 收银台 | — | 收银台本身即聚合，固定为 aggregated |
| web 内核 | 系统 WebView（system）或单一第三方（third_party） | 系统+第三方共存 |
| 热更新 | 固定为 single | — |
| 输入法 | 固定为 single | — |

---

## Output

```json
{
  "ecosystem": {
    "has_sensitive": true,
    "items": [
      {
        "category": "ads",
        "label": "广告",
        "type": "aggregated",
        "sdks": ["pangle", "admob", "unity_ads"],
        "note": "含穿山甲+AdMob+Unity Ads，属聚合广告接入"
      },
      {
        "category": "payment",
        "label": "支付",
        "type": "aggregated",
        "sdks": ["Google Pay", "支付宝"],
        "note": "含 Google Pay+支付宝，属聚合支付"
      },
      {
        "category": "map",
        "label": "地图",
        "type": "single",
        "sdks": ["高德地图"],
        "note": "仅接入高德地图单一平台"
      },
      {
        "category": "hot_update",
        "label": "热更新",
        "type": "single",
        "sdks": ["Tinker"],
        "note": "集成腾讯 Tinker 热修复框架"
      }
    ]
  }
}
```

字段说明：
- `has_sensitive`：items 非空时为 true，否则为 false
- `category`：`ads` | `account_login` | `payment` | `map` | `cashier` | `web_engine` | `hot_update` | `ime`
- `label`：对应中文名
- `type`：`single` | `aggregated` | `system` | `third_party`（web_engine 专用）
- `sdks`：具体识别到的 SDK / 平台名列表
- `note`：一句话中文说明

> 若无任何生态敏感型能力，items 为空数组，has_sensitive 为 false。