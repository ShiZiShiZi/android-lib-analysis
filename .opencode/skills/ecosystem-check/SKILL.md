---
name: ecosystem-check
description: "Identify ecosystem-sensitive capability categories in an Android library and distinguish single vs aggregated implementations"
metadata:
  category: "android-analysis"
---

## Goal

基于前序 **features-check 的分析结论**，识别库是否涉及以下生态敏感型能力，并区分**单一接入**还是**聚合接入**。

| category | label | 说明 |
|----------|-------|------|
| `ads` | 广告 | 广告变现 SDK |
| `account_login` | 账号登录 | 第三方登录 / 一键登录 |
| `payment` | 支付 | 支付渠道 SDK |
| `cashier` | 收银台 | 聚合支付 UI 层 |
| `web_engine` | Web 内核 | 系统 WebView 或第三方内核 |
| `hot_update` | 热更新 | 动态字节码加载 / 热修复 |
| `ime` | 输入法 | 第三方输入法 SDK |

---

## 检测策略

大部分信号直接从 features-check 结论推导，**无需重复 grep**。仅对 features 未覆盖的三类（web 内核、输入法、收银台）执行补充扫描。

---

## Step 1 — 从 features 结论直接推导

读取上一步 features-check 输出的 `taxonomy1`、`android_permissions` 字段，**不执行任何 bash 命令**：

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

**热更新（hot_update）**
- `android_permissions.PROHIBITED` 含 `DexClassLoader` / `PathClassLoader` / `BaseDexClassLoader` → 命中
- 热更新无单一/聚合之分，type 固定填 `single`

---

## Step 2 — 补充 grep（仅针对 features 未覆盖的三类）

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
        "type": "single",
        "sdks": ["alipay"],
        "note": "仅接入支付宝单一渠道"
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
- `category`：`ads` | `account_login` | `payment` | `cashier` | `web_engine` | `hot_update` | `ime`
- `label`：对应中文名
- `type`：`single` | `aggregated` | `system` | `third_party`（web_engine 专用）
- `sdks`：具体识别到的 SDK / 平台名列表
- `note`：一句话中文说明

> 若无任何生态敏感型能力，items 为空数组，has_sensitive 为 false。