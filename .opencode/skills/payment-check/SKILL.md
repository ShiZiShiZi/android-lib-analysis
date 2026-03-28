---
name: payment-check
description: "Detect payment, monetization, and paid cloud service dependencies in a React Native library codebase"
metadata:
  category: "rn-analysis"
---

## Goal
分析 React Native 三方库两个维度的付费情况：
1. **库本身是否收费**（商业许可证、双重授权、需要购买激活码）
2. **使用库需要付费的云服务**（付费云端后端依赖）

**路径约定**：以下所有命令均需在仓库根目录下执行，或显式指定仓库路径。

## Steps

### Step 1：检查库本身是否收费（plugin_paid）

```bash
grep -i "proprietary\|All Rights Reserved\|not free for commercial use\|commercial use requires\|dual license\|dual-licensed\|license key\|activation key\|pricing\|商业授权\|购买授权\|授权码" \
  LICENSE* README* package.json 2>/dev/null | head -40
```

**信号判断**：
- 出现 `proprietary`、`All Rights Reserved`、`not free for commercial use` → `commercial_license`
- 出现 `dual license` / `dual-licensed` 且同时含 `GPL` + (`commercial` 或 `enterprise`) → `commercial_license`
- 出现 `license key`、`activation key`、`pricing`、`商业授权`、`授权码` → `commercial_license`

> 若前序 license-check 结论为 `category=proprietary`，可直接判定 `plugin_paid=true`，跳过本步扫描。

---

### Step 2：检查付费云服务依赖

**2a. 读取 package.json，匹配已知付费服务包名**

```bash
cat package.json 2>/dev/null
```

按如下分类判断（匹配 dependencies / peerDependencies 中的包名）：

| 分类 | 包名关键词 | payment_type |
|---|---|---|
| 内购/订阅管理 | `react-native-iap`、`@react-native-iap/`、`react-native-purchases`、`@revenuecat/`、`react-native-adapty`、`react-native-qonversion` | `in_app_purchase` / `subscription_management` |
| 支付处理（国际） | `@stripe/stripe-react-native`、`@stripe/react-native`、`react-native-razorpay`、`react-native-paytm`、`braintree` | `payment_processing` |
| 支付处理（国内） | `react-native-alipay`、`@react-native-wechat/`、`react-native-wechat-pay`、`react-native-unionpay` | `payment_processing` |
| 广告变现 | `react-native-admob`、`@react-native-admob/`、`react-native-facebook-sdk`、`react-native-unityads`、`react-native-applovin` | `ad_monetization` |
| 实时音视频 RTC | `react-native-agora`、`@zegocloud/`、`react-native-zego`、`@tencentcloud/trtc-react-native` | `real_time_communication` |
| 即时通讯 IM | `@stream-io/chat-react-native`、`@sendbird/chat-react-native`、`@rongcloud/react-native-im`、`@netease/nim-react-native` | `paid_cloud_service` |
| 推送通知 | `react-native-onesignal`、`jpush-react-native`、`@getui/react-native`、`@aliyun/push-react-native` | `paid_cloud_service` |
| 归因/营销分析 | `react-native-appsflyer`、`react-native-adjust`、`react-native-branch` | `attribution_analytics` |
| 用户行为分析 | `@mixpanel/react-native`、`@amplitude/analytics-react-native`、`@segment/analytics-react-native`、`@braze/react-native-sdk` | `paid_cloud_service` |
| 监控/APM | `@sentry/react-native`、`@datadog/mobile-react-native` | `paid_cloud_service` |
| 地图服务 | `react-native-maps`、`@react-native-google-maps/`、`react-native-mapbox-gl`、`react-native-amap`、`react-native-baidu-map` | `paid_cloud_service` |
| AI/ML API | `openai`、`@anthropic-ai/`、`@google/generative-ai`、`@baidu/aip` | `paid_cloud_service` |
| 国内云存储 | `@qiniu/`、`@tencentcloud/cos-js-sdk`、`@aliyun/oss-sdk` | `paid_cloud_service` |
| 国际云平台 | `aws-amplify`、`@aws-amplify/`、`@supabase/supabase-js` | `paid_cloud_service` |
| 短信/邮件 | `twilio-react-native`、`@sendgrid/mail` | `paid_cloud_service` |

**2b. 检查 Android/iOS 原生依赖**

```bash
cat android/build.gradle 2>/dev/null | grep -i "implementation\|classpath\|maven" | head -20
grep -E "s\.dependency|s\.frameworks" ios/*.podspec 2>/dev/null | head -20
```

**2c. 检查 example 目录下的初始化代码（API key 配置集中处）**

```bash
grep -r "ApiKey\|APP_KEY\|APP_SECRET\|APPID\|apiKey\|secretKey\|accessKey\|appkey\|AppId\|appId" \
  example/ --include="*.js" --include="*.ts" --include="*.tsx" --include="*.java" --include="*.kt" --include="*.swift" -l 2>/dev/null | head -10
```

---

### Step 3：源码 grep 补充扫描

```bash
# 付费服务 API Key 配置信号（库主体代码，排除 example/）
grep -r "ApiKey\|APP_KEY\|APP_SECRET\|APPID\|apiKey\|secretKey\|accessKey\|appkey" \
  src/ android/src/ ios/ \
  --include="*.js" --include="*.ts" --include="*.tsx" --include="*.java" --include="*.kt" --include="*.swift" -l 2>/dev/null | head -10

# 定价相关文案（README）
grep -i "pricing\|free tier\|quota\|rate limit\|enterprise\|商业授权\|收费\|付费\|按量" README* 2>/dev/null | head -20

# 内购/支付核心 API 调用（精确模式，避免宽泛词误报）
grep -r "Purchases\.configure\|RevenueCat\|StoreKit\|BillingClient\|IAP\|paywall\|Superwall\|AppsFlyer\|Adjust\|Agora\|ZegoExpressEngine" \
  --include="*.js" --include="*.ts" --include="*.tsx" --include="*.java" --include="*.kt" --include="*.swift" -l 2>/dev/null | head -10
```

---

## Output

```json
{
  "involves_payment": true,
  "plugin_paid": false,
  "cloud_paid": true,
  "payment_type": ["payment_processing", "paid_cloud_service"],
  "evidence": ["package.json:12 (react-native-alipay: ^2.0.0)", "android/build.gradle:28 (com.alipay.sdk:alipaysdk-android)"]
}
```

**字段说明**：
- `involves_payment`：`plugin_paid` 或 `cloud_paid` 任一为 true 则为 true
- `plugin_paid`：库本身需购买授权时为 true（Step 1 命中）
- `cloud_paid`：库功能依赖付费云端服务时为 true（Step 2/3 命中）
- `payment_type`：仅填写实际命中的枚举值，枚举范围：
  - `commercial_license`：库本身需购买商业授权
  - `paid_cloud_service`：依赖付费云端服务（IM、推送、地图、AI 等）
  - `in_app_purchase`：集成 App 内购买（StoreKit / BillingClient）
  - `subscription_management`：订阅/Paywall 管理工具（RevenueCat、Superwall 等）
  - `payment_processing`：支付处理（Stripe、支付宝、微信支付等）
  - `ad_monetization`：广告变现 SDK
  - `real_time_communication`：实时音视频（Agora/ZEGO，按分钟计费）
  - `attribution_analytics`：归因/营销分析工具（AppsFlyer、Adjust）