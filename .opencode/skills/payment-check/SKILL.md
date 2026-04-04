---
name: payment-check
description: "Detect payment, monetization, and paid cloud service dependencies in an Android library codebase"
metadata:
  category: "android-analysis"
---

## Goal
分析 Android 三方库两个维度的付费情况：
1. **库本身是否收费**（商业许可证、双重授权、需要购买激活码）
2. **使用库需要付费的云服务**（付费云端后端依赖）

**路径约定**：以下所有命令均需在仓库根目录下执行，或显式指定仓库路径。

## Steps

### Step 1：检查库本身是否收费（plugin_paid）

```bash
grep -i "proprietary\|All Rights Reserved\|not free for commercial use\|commercial use requires\|dual license\|dual-licensed\|license key\|activation key\|pricing\|商业授权\|购买授权\|授权码" \
  LICENSE* README* build.gradle* 2>/dev/null | head -40
```

**信号判断**：
- 出现 `proprietary`、`All Rights Reserved`、`not free for commercial use` → `commercial_license`
- 出现 `dual license` / `dual-licensed` 且同时含 `GPL` + (`commercial` 或 `enterprise`) → `commercial_license`
- 出现 `license key`、`activation key`、`pricing`、`商业授权`、`授权码` → `commercial_license`

> 若前序 license-check 结论为 `category=proprietary`，可直接判定 `plugin_paid=true`，跳过本步扫描。

---

### Step 2：检查付费云服务依赖

**2a. 读取 build.gradle，匹配已知付费服务包名**

```bash
cat build.gradle 2>/dev/null || cat build.gradle.kts 2>/dev/null || echo "NO_BUILD_GRADLE"
```

按如下分类判断（匹配 dependencies 中的包名）：

| 分类 | 包名关键词 | payment_type |
|---|---|---|
| 内购/订阅管理 | `com.android.billingclient`、`com.revenuecat`、`com.adapty`、`com.qonversion` | `in_app_purchase` / `subscription_management` |
| 支付处理（国际） | `com.stripe`、`com.razorpay`、`com.paytm`、`com.braintree` | `payment_processing` |
| 支付处理（国内） | `com.alipay.sdk`、`com.tencent.mm`（微信支付）、`com.unionpay` | `payment_processing` |
| 广告变现 | `com.google.android.gms:play-services-ads`、`com.facebook.ads`、`com.unity3d.ads`、`com.applovin`、`com.pangle` | `ad_monetization` |
| 实时音视频 RTC | `com.agora`、`com.zego`、`com.tencent.trtc` | `real_time_communication` |
| 即时通讯 IM | `com.stream-io`、`com.sendbird`、`com.rongcloud`、`com.netease.nim` | `paid_cloud_service` |
| 推送通知 | `com.onesignal`、`com.jiguang`、`com.igexin`（个推）、`com.aliyun.push` | `paid_cloud_service` |
| 归因/营销分析 | `com.appsflyer`、`com.adjust`、`com.branch` | `attribution_analytics` |
| 用户行为分析 | `com.mixpanel`、`com.amplitude`、`com.segment`、`com.braze` | `paid_cloud_service` |
| 监控/APM | `com.sentry`、`com.datadog` | `paid_cloud_service` |
| 地图服务 | `com.google.android.gms:play-services-maps`、`com.mapbox`、`com.amap`、`com.baidu.map` | `paid_cloud_service` |
| AI/ML API | `com.openai`、`com.anthropic`、`com.google.ai`、`com.baidu.aip` | `paid_cloud_service` |
| 云存储 | `com.qiniu`、`com.tencent.cos`、`com.aliyun.oss`、`com.amazonaws` | `paid_cloud_service` |
| 短信/邮件 | `com.twilio`、`com.sendgrid` | `paid_cloud_service` |

**2b. 检查 AndroidManifest.xml**

```bash
find . -name "AndroidManifest.xml" ! -path "*/build/*" 2>/dev/null | head -5
grep -rn "uses-permission" --include="*.xml" . 2>/dev/null | head -20
```

**2c. 检查源码中的 API Key 配置**

```bash
EXCL="--exclude-dir=build --exclude-dir=.gradle --exclude-dir=test --exclude-dir=example"
grep -r "ApiKey\|APP_KEY\|APP_SECRET\|APPID\|apiKey\|secretKey\|accessKey\|appkey\|AppId\|appId" \
  --include="*.java" --include="*.kt" -l $EXCL . 2>/dev/null | head -10
```

---

### Step 3：源码 grep 补充扫描

```bash
# 付费服务 API Key 配置信号
grep -r "ApiKey\|APP_KEY\|APP_SECRET\|APPID\|apiKey\|secretKey\|accessKey\|appkey" \
  --include="*.java" --include="*.kt" -l $EXCL . 2>/dev/null | head -10

# 定价相关文案（README）
grep -i "pricing\|free tier\|quota\|rate limit\|enterprise\|商业授权\|收费\|付费\|按量" README* 2>/dev/null | head -20

# 内购/支付核心 API 调用
grep -r "Purchases\.configure\|RevenueCat\|BillingClient\|IAP\|paywall\|AppsFlyer\|Adjust\|Agora\|ZegoExpressEngine" \
  --include="*.java" --include="*.kt" -l $EXCL . 2>/dev/null | head -10
```

---

## Output

```json
{
  "involves_payment": true,
  "plugin_paid": false,
  "cloud_paid": true,
  "payment_type": ["payment_processing", "paid_cloud_service"],
  "evidence": ["build.gradle:12 (com.alipay.sdk:alipaysdk-android:15.8.14)", "build.gradle:28 (com.google.firebase:firebase-analytics)"]
}