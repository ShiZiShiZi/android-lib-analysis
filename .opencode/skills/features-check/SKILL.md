---
name: features-check
description: "Identify predefined feature categories and tags of a React Native library"
---

## Goal
分析 React Native 三方库提供的核心功能，从预定义的两级标签体系中选取匹配项，
输出 categories（1-3 个一级分类）和 tags（对应的二级标签）以及一句话中文摘要。
**两级标签均只能从下方预定义列表中选取，禁止自造新 key。**

---

## 预定义标签体系

### 一级分类（categories 字段的合法值）

| key | 中文 | 代表关键词 |
|-----|------|----------|
| payment | 支付 | alipay, stripe, wechat_pay, iap, BillingClient |
| map_location | 地图与定位 | geolocation, google_maps, amap, LatLng, geocoding |
| push_notification | 推送通知 | firebase_messaging, jpush, getui, FCM, APNs |
| im_chat | 即时通讯 | rongcloud, tencent_im, agora_chat, ChatClient |
| audio_video_call | 音视频通话 | agora, zego, trtc, webrtc, RtcEngine |
| storage | 数据存储 | sqlite, realm, async_storage, mmkv |
| file_media | 文件与媒体 | image_picker, file_picker, video_player, camera |
| networking | 网络请求 | axios, fetch, graphql, grpc |
| auth_security | 认证与安全 | firebase_auth, google_sign_in, oauth2, biometrics |
| analytics | 数据分析与埋点 | firebase_analytics, umeng, appsflyer, logEvent |
| ads | 广告 | admob, AdWidget, BannerAd, facebook_ads |
| social_share | 社会化分享 | react-native-share, wechat_share, Share, qr_code |
| ui_component | UI 组件 | Animated, chart, calendar, FlatList |
| device_sensor | 设备与传感器 | sensors, battery, connectivity, device_info |
| bluetooth_hardware | 蓝牙与硬件 | react-native-ble, BluetoothDevice, nfc, usb |
| ar_xr | AR/XR | arkit, arcore, ARSession, model_viewer |
| ai_ml | AI 与机器学习 | tflite, mlkit, openai, inference |
| platform_utility | 平台工具 | permission, clipboard, linking, vibration |

### 二级标签（tags 字段的合法值，按一级分类列出）

**payment**: alipay, wechat_pay, stripe, apple_pay, google_pay, paypal, razorpay, unionpay, paytm, in_app_purchase, subscription, one_time_purchase

**map_location**: google_maps, amap, baidu_map, mapbox, real_time_gps, background_location, geofencing, geocoding, poi_search, route_planning, offline_map, indoor_map

**push_notification**: fcm, apns, jpush, getui, huawei_push, xiaomi_push, oppo_push, vivo_push, local_notification, rich_notification, topic_subscription, scheduled_notification

**im_chat**: rongcloud, tencent_im, netease_im, agora_chat, sendbird, text_message, image_message, voice_message, group_chat, message_history, message_recall, read_receipt

**audio_video_call**: agora, zego, trtc, webrtc, jitsi, video_call, voice_call, live_streaming, screen_sharing, multi_party_call, recording, beauty_filter

**storage**: sqlite, key_value_store, nosql, encrypted_storage, reactive_query, migration, cloud_sync, offline_first, full_text_search, backup_restore

**file_media**: image_picker, video_picker, file_picker, camera_capture, video_recording, image_compression, image_cropping, video_playback, audio_playback, pdf_viewer, file_management, media_cache

**networking**: rest_api, graphql, websocket, grpc, http_client, interceptor, request_caching, retry, ssl_pinning, multipart_upload, download_manager

**auth_security**: firebase_auth, google_sign_in, apple_sign_in, wechat_auth, oauth2, biometric, pin_lock, secure_storage, jwt, phone_auth, two_factor_auth

**analytics**: firebase_analytics, umeng, appsflyer, adjust, sensors_data, mixpanel, crash_reporting, apm, event_tracking, user_profiling, ab_testing, funnel_analysis

**ads**: admob, facebook_ads, unity_ads, applovin, pangle, banner_ad, interstitial_ad, rewarded_ad, native_ad, splash_ad

**social_share**: wechat_share, weibo_share, qq_share, system_share, deep_link, dynamic_link, qr_code, barcode_scan, referral_invite

**ui_component**: chart, calendar, table, carousel, bottom_sheet, dialog, animation, theme, image_display, skeleton_loading, swipe_action, pull_to_refresh, infinite_scroll, rich_text_editor

**device_sensor**: accelerometer, gyroscope, step_counter, barometer, proximity_sensor, light_sensor, battery_info, connectivity_status, device_info, health_kit, gps_raw

**bluetooth_hardware**: ble_central, ble_peripheral, classic_bluetooth, nfc, usb_serial, bluetooth_printer, device_scan, mesh_network, wifi_direct

**ar_xr**: arkit, arcore, face_tracking, plane_detection, 3d_model_viewer, image_tracking, object_placement, world_tracking

**ai_ml**: image_recognition, face_detection, ocr, object_detection, text_classification, on_device_inference, cloud_ai, tflite, mlkit, llm_integration, pose_detection, translation

**platform_utility**: permission, clipboard, vibration, screen_brightness, screen_orientation, linking, app_lifecycle, keyboard_utils, package_info, app_update_check, contact_access, calendar_access, haptic_feedback, status_bar

---

## 预定义标签体系二（鸿蒙生态组件分类）

**两级均只能从下方预定义列表中选取，禁止自造，输出纯中文名。**

| 一级分类 | 二级标签 |
|---------|---------|
| AI | AI大模型, AI技术应用, 机器学习算法 |
| UI | ArkUI主题框架, 状态组件, Tab标签栏组件, 按钮组件, 标题栏组件, 表单组件, 表格组件, 布局组件, 弹窗组件, 导航索引组件, 动画, 工时填报组件, 骨架屏组件, 滑动组件, 刷新组件, 聊天对话组件, 列表组件, 轮播组件, 媒体组件, 日历组件, 扫码组件, 筛选组件, 审批流组件, 搜索页面模版, 图表绘制, 文本组件, 悬浮球组件, 指示器组件, UI组件框架, 卡片, Sticker组件, 组件生命周期管理, ArkUI图标集 |
| web开发技术 | CSS标准连字符转换, CSS色彩管理, CSS属性列表库, CSS属性设置, CSS信息资源库, CSS转换工具, web通信路由, web组件, web组件设置, 动画库, 跨平台应用运行容器, 网页解析, web数据库, 底层平台能力接口 |
| 安全 | 安全加解密, 身份验证, 完整性校验 |
| 编译构建 | 编译工具, 构建工具 |
| 测试框架 | 单元测试 |
| 存储与数据库 | 存储, 数据库 |
| 工具库 | 编程辅助工具, 程序语言工具, 地理数据处理, 第三方SDK, 电子邮件, 调试调优, 二维码处理, 华为移动服务功能库, 机器人仿真库, 即时通讯, 计时器, 计算器, 开源书籍应用, 命令行工具, 拼音转换, 日志记录和管理, 色彩管理工具, 数据处理与分析, 数学库, 通用唯一标识符, 温度转换, 文本处理工具, 应用组件模型, 正则表达式, 商品管理应用, 开源DFU应用, 应用缓存清除 |
| 跨平台开发框架 | 混合渲染框架, 自渲染框架 |
| 开发框架 | 权限请求框架, 任务调度框架, 事件驱动框架, 依赖注入框架, 游戏开发框架, 运行时hook框架 |
| 媒体 | 视频, 音频, 图像 |
| 全球化 | 电话号码解析, 日期和时间, 字符编码国际标准, 语言检测 |
| 图形 | 矢量图形处理, 图形渲染, 位图绘制, 字体渲染, 摇杆绘制 |
| 网络通信 | 短距通信, 网络I/O库, 网络路由管理, 网络通信框架, 通信协议, 应用页面路由 |
| 文档处理 | Office文档处理, PDF文档处理, XML文档处理, MD文档处理 |
| 文件操作 | 文件差异对比, 文件传输, 文件大小计算, 文件管理, 文件解析及转换, 文件类型检测, 文件路径处理, 文件上传下载 |
| 性能监控与分析 | 网络状态监控, 应用异常状态监控 |
| 序列化 | json, XML, yaml, 二进制 |
| 压缩 | 通用数据压缩, 图像压缩, 文本数据压缩 |

---

## 预定义标签体系三（SDK 标签关联关系字典）

**两级均只能从下方预定义列表中选取，输出纯中文名（不含编号前缀）。**

| 一级分类 | 二级标签 |
|---------|---------|
| 第三方登录类 | 手机号登录, 三方账号登录 |
| 认证类 | 生物特征认证, 身份认证, 短信验证 |
| 支付类 | 聚合支付, 三方支付, 乘车码 |
| 社交类 | 即时通讯, 分享 |
| 媒体类 | 音视频通话, 直播, 点播, 短视频, 媒体编辑 |
| 人工智能类 | 图像识别, 文字识别, 语音识别, 语音合成, 图像增强, 手语合成, 自然语言处理, 数字人 |
| 框架类 | 跨平台框架, 业务框架, UI框架, 架构框架 |
| 平台服务类 | 影音娱乐服务, 电商服务, 生活服务, 商务办公, 金融服务, 行业监管 |
| 存储类 | 本地存储, 云存储 |
| 地图类 | 地图, 定位, 导航 |
| 设备通信类 | 金融安全设备, 运动健康设备, 车机设备, 办公家居设备 |
| 网络类 | DNS域名解析, 网络优化, 网络中台服务, 网络加密 |
| 安全风控类 | 应用安全, 业务安全, 数据安全, 设备安全, 安全控件 |
| 统计类 | 数据分析, 运营测试 |
| 性能监控类 | 测试工具, 性能分析 |
| 推送类 | 推送 |
| 游戏类 | 游戏性能优化, 云游戏服务, 游戏基础功能 |
| XR类 | XR |
| 客服类 | 客服 |
| 广告类 | 广告投放, 广告监测 |
| 系统工具类 | 系统工具 |
| 生产工具类 | 设计工具 |
| 生活与学习 | 购物, 居家日常, 运动与健康, 旅游, 理财, 教育与学习, 社交与沟通, 新闻与天气 |
| 效率与性能 | 通用工具, 性能, 无障碍 |
| 多媒体与娱乐 | 动画与音视频处理, 图片与照片, 游戏与娱乐 |
| 办公与协同 | 流式文档处理, 版式文档处理, 电子签章, 报表制作与绘图, 会议与协作, 业务系统专用插件 |
| 外设交互 | 打印与扫描, 影像采集器, 扫码枪, POS机, 评价器, 读卡器, Ukey |
| 开发与设计 | 开发工具, 组件库, 外观与主题 |
| 人工智能 | AI |
| 安全与隐私 | 安全控件, 安全防御, 隐私保护, 内容过滤 |
| Ukey | （无子标签） |

---

## Steps

### Step 1 — 读取元信息
```bash
cat package.json
head -150 README.md 2>/dev/null || head -150 readme.md 2>/dev/null
```
从 `description` 和 `dependencies` 快速锁定候选一级分类。

### Step 2 — 读取公开 API（src/ 入口文件）
```bash
find src/ \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" \) 2>/dev/null | head -10
cat index.js 2>/dev/null || cat index.ts 2>/dev/null || cat src/index.ts 2>/dev/null
grep -rn "export\|export default\|export const" --include="*.ts" --include="*.tsx" --include="*.js" src/ 2>/dev/null | head -60
```

### Step 3 — 按候选分类 grep 关键词（在仓库根目录执行，相对路径）
```bash
EXCL="--exclude-dir=node_modules --exclude-dir=example --exclude-dir=dist --exclude-dir=.gradle"

# payment
grep -r "stripe\|alipay\|wechat.*pay\|razorpay\|IAP\|RevenueCat\|BillingClient\|paywall\|unionpay\|google.*pay\|apple.*pay" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" -l -i $EXCL .

# map_location
grep -r "google.*maps\|amap\|baidu.*map\|mapbox\|geolocation\|geocoding\|LatLng\|Marker\|Polyline\|geofenc" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" -l -i $EXCL .

# push_notification
grep -r "@react-native-firebase/messaging\|jpush\|getui\|RemoteMessage\|local.*notification\|FCM\|APNs\|NotificationService\|huawei.*push\|xiaomi.*push" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" -l -i $EXCL .

# im_chat
grep -r "rongcloud\|tencent.*im\|netease.*im\|agora.*chat\|sendbird\|ChatClient\|MessageKit\|IMService" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" -l -i $EXCL .

# audio_video_call
grep -r "react-native-agora\|zego\|trtc\|react-native-webrtc\|jitsi\|RtcEngine\|ZegoExpressEngine\|liveStream" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" -l -i $EXCL .

# storage
grep -r "react-native-quick-sqlite\|realm\|@react-native-async-storage\|mmkv\|objectbox\|openDatabase\|Box\b\|Dao\b" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" -l -i $EXCL .

# file_media
grep -r "react-native-image-picker\|react-native-document-picker\|react-native-video\|react-native-vision-camera\|react-native-camera\|ffmpeg\|ImagePicker" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" -l -i $EXCL .

# networking
grep -r "axios\|fetch\|graphql\|grpc\|XMLHttpRequest\|WebSocket\|interceptor" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" -l -i $EXCL .

# auth_security
grep -r "@react-native-firebase/auth\|@react-native-google-signin\|oauth2\|react-native-biometrics\|react-native-keychain\|biometric\|signIn\b\|authenticate" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" -l -i $EXCL .

# analytics
grep -r "@react-native-firebase/analytics\|umeng\|appsflyer\|adjust\|sensors_data\|mixpanel\|logEvent\|trackEvent\|Crashlytics\|@sentry/react-native" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" -l -i $EXCL .

# ads
grep -r "react-native-admob\|@react-native-admob\|BannerAd\|InterstitialAd\|admob\|applovin\|unity.*ads\|pangle\|loadAd" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" -l -i $EXCL .

# ui_component
grep -r "Animated\|chart\|calendar\|carousel\|BottomSheet\|skeleton\|SwipeAction" --include="*.ts" --include="*.tsx" --include="*.js" -l -i $EXCL .

# device_sensor
grep -r "react-native-sensors\|react-native-battery\|@react-native-community/netinfo\|react-native-device-info\|Accelerometer\|Gyroscope\|Barometer" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" -l -i $EXCL .

# bluetooth_hardware
grep -r "react-native-ble-plx\|react-native-ble-manager\|BluetoothDevice\|nfc-manager\|usb\|bluetooth.*print" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" -l -i $EXCL .

# ai_ml
grep -r "tflite\|@react-native-ml-kit\|onnx\|openai\|anthropic\|langchain\|llm" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" -l -i $EXCL .

# platform_utility
grep -r "react-native-permissions\|Clipboard\|react-native-vibration\|Linking\|screen.*brightness\|StatusBar\|react-native-device-info" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" -l -i $EXCL .
```

### Step 4 — Android 权限与危险机制扫描

#### 4a — 扫描 AndroidManifest.xml 声明权限
```bash
grep -r "uses-permission" android/ --include="*.xml" -h | grep -oE 'android:name="[^"]+"' | sort -u
```

#### 4b — 扫描 PROHIBITED 危险代码模式（Java/Kotlin 源码）
```bash
# 动态字节码加载 / 热修复
grep -r "DexClassLoader\|PathClassLoader\|BaseDexClassLoader\|InMemoryDexClassLoader" android/ --include="*.java" --include="*.kt" -l

# Xposed / hook 框架
grep -r "de\.robv\.android\.xposed\|XposedBridge\|XposedHelpers\|IXposedHookLoadPackage" android/ --include="*.java" --include="*.kt" -l

# root 提权
grep -r "Runtime\.exec.*[\"']su[\"']\|ProcessBuilder.*[\"']su[\"']\|checkRootMethod\|isRooted" android/ --include="*.java" --include="*.kt" -l
```

#### 4c — 扫描 CONTROLLED_ACL 高危权限使用（Manifest + 源码）
```bash
# SYSTEM_ALERT_WINDOW 全局悬浮窗
grep -r "SYSTEM_ALERT_WINDOW\|TYPE_APPLICATION_OVERLAY\|TYPE_SYSTEM_ALERT\|TYPE_SYSTEM_OVERLAY" android/ --include="*.xml" --include="*.java" --include="*.kt" -l

# AccessibilityService 无障碍/模拟点击
grep -r "AccessibilityService\|BIND_ACCESSIBILITY_SERVICE\|onAccessibilityEvent\|performGlobalAction" android/ --include="*.xml" --include="*.java" --include="*.kt" -l

# 设备管理器
grep -r "BIND_DEVICE_ADMIN\|DevicePolicyManager\|DeviceAdminReceiver" android/ --include="*.xml" --include="*.java" --include="*.kt" -l

# 安装未知来源 APK
grep -r "REQUEST_INSTALL_PACKAGES\|PackageInstaller\|ACTION_INSTALL_PACKAGE" android/ --include="*.xml" --include="*.java" --include="*.kt" -l

# 修改系统设置
grep -r "WRITE_SETTINGS\|Settings\.System\.putInt\|Settings\.Global" android/ --include="*.xml" --include="*.java" --include="*.kt" -l

# 全盘文件访问
grep -r "MANAGE_EXTERNAL_STORAGE\|ACTION_MANAGE_ALL_FILES" android/ --include="*.xml" --include="*.java" --include="*.kt" -l

# 极端后台保活组合（三个权限同时出现才判定）
grep -r "REQUEST_IGNORE_BATTERY_OPTIMIZATIONS\|RECEIVE_BOOT_COMPLETED\|FOREGROUND_SERVICE" android/ --include="*.xml" -h | sort -u
```

#### 4d — 三级分类规则

| 级别 | 判定条件 | 典型信号 |
|------|---------|---------|
| `PROHIBITED` | 鸿蒙底层架构明确禁止，无平替 API | `DexClassLoader`/`PathClassLoader`（动态字节码加载/热修复）、Xposed/Frida hook 框架（`XposedBridge`/`de.robv.android.xposed`）、root 提权（`Runtime.exec("su")`） |
| `CONTROLLED_ACL` | 鸿蒙有对应能力但属高危受控，须向华为提交 ACL 白名单申请 | `BIND_ACCESSIBILITY_SERVICE`（无障碍/模拟点击）、`SYSTEM_ALERT_WINDOW`（全局悬浮窗）、`BIND_DEVICE_ADMIN`（设备管理器）、`REQUEST_INSTALL_PACKAGES`（装 APK）、`WRITE_SETTINGS`（改系统设置）、`MANAGE_EXTERNAL_STORAGE`（全盘访问）、同时含 `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`+`RECEIVE_BOOT_COMPLETED`+`FOREGROUND_SERVICE` 的极端保活组合 |
| `NORMAL_PASS` | 常规开放权限，普通用户授权即可使用 | `INTERNET`、`CAMERA`、`RECORD_AUDIO`、`ACCESS_FINE_LOCATION`、`READ_EXTERNAL_STORAGE`、`BLUETOOTH_*`、`NFC`、`VIBRATE`、`WAKE_LOCK`、`FOREGROUND_SERVICE`（单独）等所有其余权限 |

> **判定优先级**：若一个权限/模式同时符合多级，取最高级。后台保活三权限须**同时**出现才升级为 `CONTROLLED_ACL`，单独出现属 `NORMAL_PASS`。

### Step 5 — 读取命中最多的 1-2 个核心文件
命中文件数 ≥ 2 的分类，读取其核心 .ts/.tsx/.js 文件前 200 行确认细节：
```bash
cat src/<core_file>.ts | head -200
```

### Step 6 — 独立输出三套标签（互不影响）

**共享字段**（描述库客观能力，与分类体系无关）：
1. `feature_list`：自然语言功能清单，**5-15 条**，每条以「支持」或「提供」开头，中文，
   描述库具体实现的能力（从 README 和核心 API 提取，不要泛泛而谈）
2. `summary`：一句话中文，格式「提供 XX 能力，支持 YY，适用于 ZZ 场景」
3. `evidence`：具体文件和代码行

**体系一**（英文 key 体系，原有逻辑不变）：
- **不参考体系二/三的结果**，独立从体系一预定义列表中选取
- `categories`：命中文件 ≥ 2 或 README 明确描述 → 纳入，最多 3 个，降序排列
- `tags`：仅从命中 categories 对应的预定义列表中选，4-10 个，选有代码证据的
- 若确实无匹配，tags 中可出现 `other`（应极少出现）

**体系二**（鸿蒙生态组件分类，纯中文名）：
- **不参考体系一/三的结果**，独立从体系二预定义列表中选取
- `categories`：1-3 个一级分类中文名
- `tags`：对应一级分类下的二级标签中文名，4-10 个

**体系三**（SDK 标签关联关系字典，纯中文名）：
- **不参考体系一/二的结果**，独立从体系三预定义列表中选取
- `categories`：1-3 个一级分类中文名（不含编号前缀）
- `tags`：对应一级分类下的二级标签中文名（不含编号前缀），4-10 个

## Output

```json
{
  "feature_list": [
    "支持支付宝 App 支付（调起支付宝客户端）",
    "支持支付宝 OAuth 授权登录",
    "支持获取支付宝用户 ID 和基本信息",
    "支持 Android 和 iOS 双平台原生 SDK 封装",
    "支持支付结果异步回调",
    "提供检测设备是否已安装支付宝的工具方法"
  ],
  "summary": "封装支付宝原生 SDK，提供支付和 OAuth 登录能力，适用于需接入支付宝的电商类应用。",
  "evidence": [
    "src/index.ts:32 export function pay(...)",
    "android/build.gradle:58 com.alipay.sdk:alipaysdk-android:15.8.14"
  ],
  "android_permissions": {
    "PROHIBITED": [
      {"signal": "DexClassLoader", "file": "android/src/main/java/com/example/Plugin.java", "note": "动态字节码加载/热修复"}
    ],
    "CONTROLLED_ACL": [
      {"permission": "android.permission.SYSTEM_ALERT_WINDOW", "note": "全局悬浮窗，鸿蒙需 ACL 审批"},
      {"permission": "android.permission.BIND_ACCESSIBILITY_SERVICE", "note": "无障碍服务，鸿蒙需 ACL 审批"}
    ],
    "NORMAL_PASS": [
      "android.permission.INTERNET",
      "android.permission.CAMERA",
      "android.permission.ACCESS_FINE_LOCATION"
    ]
  },
  "taxonomy1": {
    "categories": ["payment", "auth_security"],
    "tags": ["alipay", "in_app_purchase", "wechat_auth", "oauth2"]
  },
  "taxonomy2": {
    "categories": ["工具库", "安全"],
    "tags": ["第三方SDK", "身份验证", "安全加解密"]
  },
  "taxonomy3": {
    "categories": ["支付类", "第三方登录类"],
    "tags": ["三方支付", "三方账号登录"]
  }
}
```

> `android_permissions` 三个 key 均可为空数组（`[]`）。`PROHIBITED` 和 `CONTROLLED_ACL` 中的每项保留 `file`（发现位置）和 `note`（风险说明）；`NORMAL_PASS` 只列权限名字符串即可。