---
name: cloud-service-check
description: "Detect cloud service topology (pure_edge / centralized / decentralized) in a React Native library codebase"
metadata:
  category: "rn-analysis"
---

## Goal
分析 React Native 三方库的端云拓扑类型，输出三分类标签：纯端（pure_edge）、端云协同中心化（centralized）、端云协同去中心化（decentralized）。
同时列出所有涉及的云端服务及其提供方。

## 端云拓扑定义

| 标签 | key | 核心判断标准 |
|------|-----|------------|
| 纯端 | `pure_edge` | 库自身不发起任何外部网络请求；断网后核心功能 100% 正常 |
| 端云协同中心化 | `centralized` | 库硬绑定到特定商业平台，需注册/AppKey，厂商云不可替换 |
| 端云协同去中心化 | `decentralized` | 库会发起网络请求，但目标端点由开发者配置 / 可自托管 / P2P / 开放协议 |

**重要边界**：
- 如果库**本身只提供**网络工具（不调用任何外部端点）→ `pure_edge`（如 axios、fetch 封装库）
- 如果库**自身代码**使用网络工具调用**可配置 URL / 无特定厂商**的外部端点 → `decentralized`
- 如果库调用**特定厂商**的固定端点（需注册/AppKey）→ `centralized`
- `pure_edge` vs `decentralized` 的本质边界：**库自身是否发起外部调用**，而非是否依赖特定厂商
- 优先级：`centralized` > `decentralized` > `pure_edge`

---

## 云端服务提供方字典

命中以下关键词时，按字典填写 `provider`（中文）和 `provider_en`（英文）：

| 关键词 | service 名称 | provider | provider_en |
|--------|-------------|----------|-------------|
| `@react-native-firebase/` | Firebase | Google | Google |
| `react-native-google-signin` | Google 登录 | Google | Google |
| `react-native-admob` / `@react-native-admob` | AdMob | Google | Google |
| `jpush-react-native` / `jiguang` | 极光推送 | 极光 | Aurora Push |
| `@getui/react-native` | 个推 | 个推 | Getui |
| `react-native-umeng` / `umeng` | 友盟+ | 友盟 | Umeng |
| `@aliyun/` / `aliyun-oss-react-native` | 阿里云 | 阿里云 | Alibaba Cloud |
| `react-native-qiniu` | 七牛云 | 七牛 | Qiniu Cloud |
| `@tencent/` / `react-native-tencent-im` | 腾讯云 | 腾讯云 | Tencent Cloud |
| `react-native-wechat` / `@react-native-wechat/` | 微信 SDK | 腾讯 | Tencent |
| `react-native-amap` / `amap` | 高德地图 | 高德（阿里） | Amap/Alibaba |
| `react-native-baidu-map` | 百度地图 | 百度 | Baidu |
| `@rongcloud/react-native-im` | 融云 | 融云 | RongCloud |
| `@netease/` / `nim-react-native` | 网易云信 | 网易 | NetEase Yunxin |
| `@react-native-hms/` | 华为 HMS | 华为 | Huawei |
| `react-native-agora` | 声网 | 声网 | Agora |
| `react-native-zego` | 即构科技 | 即构 | ZEGO |
| `@react-native-community/netinfo` | 网络状态 | Meta | Meta |
| `react-native-alipay` | 支付宝 | 蚂蚁集团 | Ant Group |
| `@stripe/stripe-react-native` | Stripe | Stripe | Stripe |
| `react-native-razorpay` | Razorpay | Razorpay | Razorpay |
| `react-native-adjust` | Adjust | Adjust | Adjust |
| `react-native-appsflyer` | AppsFlyer | AppsFlyer | AppsFlyer |
| `@sensorsdata/react-native` | 神策数据 | 神策 | Sensors Data |
| `@braze/react-native-sdk` | Braze | Braze | Braze |
| `aws-amplify` / `@aws-amplify/` | AWS Amplify | Amazon | Amazon AWS |
| `react-native-mapbox-gl` | Mapbox | Mapbox | Mapbox |
| `react-native-twilio` | Twilio | Twilio | Twilio |
| `@sentry/react-native` | Sentry | Sentry | Sentry |
| `react-native-onesignal` | OneSignal | OneSignal | OneSignal |

---

## Steps

### Step 1a — 中心化厂商信号检测

读取 `package.json` 的 dependencies，并在代码中搜索特定厂商关键词：

```bash
# AppKey / 初始化信号
grep -r "AppKey\|appKey\|app_key\|AppSecret\|apiKey\|api_key\|SecretKey\|secretKey\|initializeApp\|appId\|APP_ID" \
  --include="*.js" --include="*.ts" --include="*.tsx" \
  --exclude-dir=node_modules --exclude-dir=example --exclude-dir=dist -l .
grep -r "AppKey\|appKey\|app_key\|AppSecret\|apiKey\|api_key\|SecretKey\|secretKey\|appId" \
  --include="*.json" --exclude-dir=node_modules --exclude-dir=example -l .

# 推送 / IM / 音视频 厂商
grep -r "@react-native-firebase\|jpush\|jiguang\|getui\|umeng\|onesignal\|braze\
\|aliyun.*push\|@react-native-hms.*push\|xiaomi.*push\|oppo.*push\|vivo.*push\
\|rongcloud\|tencent.*im\|@netease/.*im\|nim-\
\|react-native-agora\|react-native-zego\|trtc" \
  --include="*.json" --include="*.js" --include="*.ts" --include="*.tsx" \
  --exclude-dir=node_modules --exclude-dir=example -l -i .

# 分析 / 监控 / 归因
grep -r "@react-native-firebase/analytics\|umeng\|adjust\|appsflyer\|sensors_data\
\|mixpanel\|braze\|@react-native-firebase/crashlytics\|@sentry/react-native\|datadog" \
  --include="*.json" --include="*.js" --include="*.ts" --include="*.tsx" \
  --exclude-dir=node_modules --exclude-dir=example -l -i .

# 地图服务（均需注册 API Key）
grep -r "react-native-maps\|react-native-amap\|react-native-baidu-map\|@react-native-google-maps\|mapbox\|here_sdk" \
  --include="*.json" --include="*.js" --include="*.ts" --include="*.tsx" \
  --exclude-dir=node_modules --exclude-dir=example -l -i .

# 云存储 / 云平台（supabase 可自托管，归 decentralized，不列此处）
grep -r "aliyun-oss\|@qiniu/\|tencent-cos\|aws-amplify\
\|@react-native-firebase/storage\|@react-native-firebase/database\|@react-native-firebase/firestore" \
  --include="*.json" --include="*.js" --include="*.ts" --include="*.tsx" \
  --exclude-dir=node_modules --exclude-dir=example -l -i .

# 支付
grep -r "react-native-alipay\|wechat.*pay\|@stripe/\|razorpay\|paytm\|braintree" \
  --include="*.json" --include="*.js" --include="*.ts" --include="*.tsx" \
  --exclude-dir=node_modules --exclude-dir=example -l -i .

# AI 云服务
grep -r "openai\|anthropic\|@google/generative-ai\|iflytek\|baidu.*aip\
\|tongyi\|dashscope\|zhipu\|minimax\|deepseek\|moonshot" \
  --include="*.json" --include="*.js" --include="*.ts" --include="*.tsx" \
  --exclude-dir=node_modules --exclude-dir=example -l -i .
```

**若命中** → 记录 centralized 信号，对照提供方字典填写 services，**继续执行 Step 1b/1c/Step 2**（不跳过，确保收集完整证据）。

---

### Step 1b — 端点配置信号检测

检测库源码中是否存在可配置的 URL / 服务器地址参数：

```bash
grep -r "baseUrl\|base_url\|serverUrl\|server_url\|endpoint\|feedUrl\|feed_url\
\|appcastUrl\|updateUrl\|hostUrl\|apiUrl\|wsUrl\|mqttHost\|brokerUrl\|serverAddress" \
  --include="*.js" --include="*.ts" --include="*.tsx" --include="*.json" \
  --exclude-dir=node_modules --exclude-dir=example -l -i .
```

**若命中** → 记录为"可配置端点信号"，继续 Step 1c。

---

### Step 1c — 外部直连信号检测

检测库代码中是否存在硬编码的外部 URL（排除注释和测试文件）：

```bash
grep -rn "https\?://\|ws\?://" --include="*.js" --include="*.ts" --include="*.tsx" \
  --exclude-dir=node_modules --exclude-dir=example --exclude-dir=dist \
  | grep -v "^\s*//" \
  | grep -v "_test\|__tests__\|\.test\.\|\.spec\." \
  | head -20
```

**若命中非厂商固定域名的外部 URL** → 记录为"外部直连信号"，继续 Step 2。

---

### Step 2 — 去中心化信号检测

**检查去中心化信号**（满足任意一项 → 记录 decentralized 信号）：

```bash
# WebRTC / P2P
grep -r "react-native-webrtc\|peerjs\|simple-peer\|nearby-connection\|bluetooth\|wifi-direct\|p2p" \
  --include="*.json" --include="*.js" --include="*.ts" --include="*.tsx" \
  --exclude-dir=node_modules --exclude-dir=example -l -i .

# 自动更新框架（URL 可配置）
grep -r "codepush\|code-push\|osparkle\|appcast\|appcastUrl" \
  --include="*.js" --include="*.ts" --include="*.tsx" --include="*.json" \
  --exclude-dir=node_modules --exclude-dir=example -l -i .

# 自托管 / 可配置服务协议
grep -r "mqtt\|amqp\|stomp\|websocket.*url\|socket.*host\|oidc\|oauth2.*endpoint" \
  --include="*.js" --include="*.ts" --include="*.tsx" --include="*.json" \
  --exclude-dir=node_modules --exclude-dir=example -l -i .

# 开放地图（无需 AppKey）
grep -r "openstreetmap\|osm\|tile\.openstreetmap\|nominatim" \
  --include="*.js" --include="*.ts" --include="*.tsx" --include="*.json" \
  --exclude-dir=node_modules --exclude-dir=example -l -i .

# 区块链工具库（可连接任意 RPC 节点）
grep -r "ethers\|web3\|walletconnect\|viem" \
  --include="*.json" --include="*.js" --include="*.ts" --include="*.tsx" \
  --exclude-dir=node_modules --exclude-dir=example -l -i .

# 自托管 BaaS（supabase 可自托管，归此处）
grep -r "appwrite\|supabase" \
  --include="*.js" --include="*.ts" --include="*.tsx" --include="*.json" \
  --exclude-dir=node_modules --exclude-dir=example -l -i .
```

去中心化判定条件（满足任意一项）：
- WebRTC SDK（`react-native-webrtc`、`peerjs`）
- 蓝牙 / 附近发现
- Wi-Fi Direct / P2P 直连
- CodePush 且端点可配置
- MQTT / AMQP / STOMP 等可自托管协议客户端
- 通用 WebSocket/SSE 客户端（目标 URL 可配置）
- 开放协议 OAuth2/OIDC（不绑定特定厂商）
- 开放地图 tile（OpenStreetMap 等无需注册）
- 区块链 / Web3 工具库（`ethers`、`viem`、`walletconnect`）
- 自托管 BaaS（`appwrite`）
- Step 1b/1c 存在可配置端点信号且无特定厂商绑定

---

### Step 3 — 最终判定

按以下优先级决定 topology：

1. **Step 1a 命中厂商信号** → `centralized`
2. **Step 2 命中去中心化信号** → `decentralized`（若同时命中 Step 1a，仍为 `centralized`）
3. **Step 1b 或 Step 1c 有可配置端点 / 外部 URL 信号，且无厂商绑定** → `decentralized`
4. **无任何网络调用迹象** → `pure_edge`
5. **仅有 axios/fetch 等工具包但库自身未调用任何外部端点** → `pure_edge`

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
  "evidence": ["具体文件和代码行", "..."]
}
```

**`evidence` 填写规范**：
- 必须是 grep 命中的**文件路径和代码行**，例如 `package.json:12 (@react-native-firebase/analytics: ^18.0.0)`、`android/build.gradle:8 (com.huawei.agconnect)`
- **禁止**填写功能描述或库用途说明（那是 features-check 的职责）
- `topology=pure_edge` 时无 grep 命中，evidence 填写各步扫描结论：
  ```
  ["Step 1a: 无厂商信号命中", "Step 1b: 无可配置端点信号", "Step 1c: 无外部 URL", "Step 2: 无去中心化信号"]
  ```

> `services` 为空数组时 topology 应为 `pure_edge` 或 `decentralized`。
> decentralized 类服务（WebRTC、MQTT、OpenStreetMap 等）不计入 services，仅在 evidence 中记录。