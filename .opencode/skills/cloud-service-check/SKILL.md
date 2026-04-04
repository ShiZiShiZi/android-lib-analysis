---
name: cloud-service-check
description: "Detect cloud service topology (pure_edge / centralized / decentralized) in an Android library codebase"
metadata:
  category: "android-analysis"
---

## Goal
分析 Android 三方库的端云拓扑类型，输出三分类标签：纯端（pure_edge）、端云协同中心化（centralized）、端云协同去中心化（decentralized）。
同时列出所有涉及的云端服务及其提供方。

## 端云拓扑定义

| 标签 | key | 核心判断标准 |
|------|-----|------------|
| 纯端 | `pure_edge` | 库自身不发起任何外部网络请求；断网后核心功能 100% 正常 |
| 端云协同中心化 | `centralized` | 库硬绑定到特定商业平台，需注册/AppKey，厂商云不可替换 |
| 端云协同去中心化 | `decentralized` | 库会发起网络请求，但目标端点由开发者配置 / 可自托管 / P2P / 开放协议 |

**重要边界**：
- 如果库**本身只提供**网络工具（不调用任何外部端点）→ `pure_edge`（如 OkHttp 封装库）
- 如果库**自身代码**使用网络工具调用**可配置 URL / 无特定厂商**的外部端点 → `decentralized`
- 如果库调用**特定厂商**的固定端点（需注册/AppKey）→ `centralized`
- `pure_edge` vs `decentralized` 的本质边界：**库自身是否发起外部调用**
- 优先级：`centralized` > `decentralized` > `pure_edge`

---

## 云端服务提供方字典

命中以下关键词时，按字典填写 `provider`（中文）和 `provider_en`（英文）：

| 关键词 | service 名称 | provider | provider_en |
|--------|-------------|----------|-------------|
| `com.google.firebase` | Firebase | Google | Google |
| `com.google.android.gms` | Google Play Services | Google | Google |
| `play-services-*` | Google Play Services | Google | Google |
| `jpush` / `jiguang` | 极光推送 | 极光 | Aurora Push |
| `getui` / `com.igexin` | 个推 | 个推 | Getui |
| `umeng` / `com.umeng` | 友盟+ | 友盟 | Umeng |
| `com.aliyun` / `aliyun-oss` | 阿里云 | 阿里云 | Alibaba Cloud |
| `com.qiniu` | 七牛云 | 七牛 | Qiniu Cloud |
| `com.tencent` / `tencent-im` | 腾讯云 | 腾讯云 | Tencent Cloud |
| `com.tencent.mm` / `wechat` | 微信 SDK | 腾讯 | Tencent |
| `com.amap` / `com.autonavi` | 高德地图 | 高德（阿里） | Amap/Alibaba |
| `com.baidu.*map` | 百度地图 | 百度 | Baidu |
| `com.huawei.*hms` | 华为 HMS | 华为 | Huawei |
| `com.agora` | 声网 | 声网 | Agora |
| `com.zego` | 即构科技 | 即构 | ZEGO |
| `com.alipay` / `alipaysdk` | 支付宝 | 蚂蚁集团 | Ant Group |
| `com.stripe` | Stripe | Stripe | Stripe |
| `com.razorpay` | Razorpay | Razorpay | Razorpay |
| `com.adjust` | Adjust | Adjust | Adjust |
| `com.appsflyer` | AppsFlyer | AppsFlyer | AppsFlyer |
| `com.sensorsdata` | 神策数据 | 神策 | Sensors Data |
| `com.braze` | Braze | Braze | Braze |
| `com.amazonaws` / `aws-*` | AWS | Amazon | Amazon AWS |
| `com.mapbox` | Mapbox | Mapbox | Mapbox |
| `com.twilio` | Twilio | Twilio | Twilio |
| `com.sentry` | Sentry | Sentry | Sentry |
| `com.onesignal` | OneSignal | OneSignal | OneSignal |

---

## Steps

### Step 1a — 中心化厂商信号检测

读取 `build.gradle` 的 dependencies，并在代码中搜索特定厂商关键词：

```bash
EXCL="--exclude-dir=build --exclude-dir=.gradle --exclude-dir=test --exclude-dir=example --exclude-dir=sample"

# AppKey / 初始化信号
grep -r "AppKey\|appKey\|app_key\|AppSecret\|apiKey\|api_key\|SecretKey\|secretKey\|initializeApp\|appId\|APP_ID" \
  --include="*.java" --include="*.kt" --include="*.gradle" --include="*.kts" -l $EXCL . 2>/dev/null

# 推送 / IM / 音视频 厂商
grep -r "com\.google\.firebase\|jpush\|jiguang\|getui\|umeng\|onesignal\|braze\
\|com\.huawei.*push\|com\.xiaomi.*push\|com\.oppo.*push\|com\.vivo.*push\
\|rongcloud\|tencent.*im\|com\.netease.*im\
\|com\.agora\|com\.zego\|trtc" \
  --include="*.gradle" --include="*.kts" --include="*.java" --include="*.kt" -l -i $EXCL . 2>/dev/null

# 分析 / 监控 / 归因
grep -r "com\.google\.firebase.*analytics\|umeng\|adjust\|appsflyer\|sensors_data\
\|mixpanel\|braze\|sentry\|datadog" \
  --include="*.gradle" --include="*.kts" --include="*.java" --include="*.kt" -l -i $EXCL . 2>/dev/null

# 地图服务（均需注册 API Key）
grep -r "com\.google.*maps\|com\.amap\|com\.baidu.*map\|com\.mapbox\|here_sdk" \
  --include="*.gradle" --include="*.kts" --include="*.java" --include="*.kt" -l -i $EXCL . 2>/dev/null

# 云存储 / 云平台
grep -r "com\.aliyun.*oss\|com\.qiniu\|com\.tencent.*cos\|com\.amazonaws\
\|com\.google\.firebase.*storage\|com\.google\.firebase.*database" \
  --include="*.gradle" --include="*.kts" -l -i $EXCL . 2>/dev/null

# 支付
grep -r "com\.alipay\|com\.wechat\|com\.stripe\|com\.razorpay\|com\.braintree" \
  --include="*.gradle" --include="*.kts" --include="*.java" --include="*.kt" -l -i $EXCL . 2>/dev/null

# AI 云服务
grep -r "openai\|anthropic\|com\.google.*generative\|com\.baidu.*aip\
\|tongyi\|dashscope\|zhipu\|minimax\|deepseek\|moonshot" \
  --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL . 2>/dev/null
```

**若命中** → 记录 centralized 信号，对照提供方字典填写 services，**继续执行 Step 1b/1c/Step 2**。

---

### Step 1b — 端点配置信号检测

检测库源码中是否存在可配置的 URL / 服务器地址参数：

```bash
grep -r "baseUrl\|base_url\|serverUrl\|server_url\|endpoint\|feedUrl\|feed_url\
\|appcastUrl\|updateUrl\|hostUrl\|apiUrl\|wsUrl\|mqttHost\|brokerUrl\|serverAddress" \
  --include="*.java" --include="*.kt" --include="*.gradle" --include="*.kts" \
  -l -i $EXCL . 2>/dev/null
```

**若命中** → 记录为"可配置端点信号"。

---

### Step 1c — 外部直连信号检测

检测库代码中是否存在硬编码的外部 URL：

```bash
grep -rn "https\?://\|ws\?://" --include="*.java" --include="*.kt" \
  $EXCL . 2>/dev/null | head -20
```

**若命中非厂商固定域名的外部 URL** → 记录为"外部直连信号"。

---

### Step 2 — 去中心化信号检测

```bash
# WebRTC / P2P
grep -r "webrtc\|peerjs\|nearby-connection\|bluetooth.*socket\|wifi-direct\|p2p" \
  --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL . 2>/dev/null

# MQTT / WebSocket 等可自托管协议
grep -r "mqtt\|amqp\|stomp\|websocket.*client\|socket.*host\|oidc\|oauth2.*endpoint" \
  --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL . 2>/dev/null

# 开放地图（无需 AppKey）
grep -r "openstreetmap\|osm\|tile\.openstreetmap\|nominatim" \
  --include="*.java" --include="*.kt" -l -i $EXCL . 2>/dev/null

# 区块链工具库
grep -r "web3j\|ethers\|walletconnect\|bitcoinj" \
  --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL . 2>/dev/null
```

---

### Step 3 — 最终判定

按以下优先级决定 topology：

1. **Step 1a 命中厂商信号** → `centralized`
2. **Step 2 命中去中心化信号** → `decentralized`（若同时命中 Step 1a，仍为 `centralized`）
3. **Step 1b 或 Step 1c 有可配置端点信号，且无厂商绑定** → `decentralized`
4. **无任何网络调用迹象** → `pure_edge`
5. **仅有 OkHttp/Retrofit 等工具包但库自身未调用任何外部端点** → `pure_edge`

---

## Output

```json
{
  "topology": "pure_edge | centralized | decentralized",
  "label": "纯端 | 端云协同中心化 | 端云协同去中心化",
  "services": [
    {
      "name": "友盟推送",
      "provider": "友盟",
      "provider_en": "Umeng"
    },
    {
      "name": "Firebase Analytics",
      "provider": "Google",
      "provider_en": "Google"
    }
  ],
  "evidence": ["build.gradle:12 (com.umeng.analytics:umeng-analytics:9.6.0)", "build.gradle:18 (com.google.firebase:firebase-analytics)"]
}