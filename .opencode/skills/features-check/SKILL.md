---
name: features-check
description: "Identify predefined feature categories and tags of an Android library"
---

## Goal
分析 Android 三方库提供的核心功能，从预定义的两级标签体系中选取匹配项，
输出 categories（1-3 个一级分类）和 tags（对应的二级标签）以及一句话中文摘要。
**两级标签均只能从下方预定义列表中选取，禁止自造新 key。**

---

## 预定义标签体系

### 一级分类（categories 字段的合法值）

| key | 中文 | 代表关键词 |
|-----|------|----------|
| payment | 支付 | alipay, stripe, wechat_pay, iap, BillingClient, PaymentRequest |
| map_location | 地图与定位 | geolocation, google_maps, amap, LatLng, geocoding, LocationManager |
| push_notification | 推送通知 | firebase_messaging, jpush, getui, FCM, NotificationManager |
| im_chat | 即时通讯 | rongcloud, tencent_im, agora_chat, ChatClient, Message |
| audio_video_call | 音视频通话 | agora, zego, trtc, webrtc, RtcEngine, MediaPlayer |
| storage | 数据存储 | sqlite, realm, room, mmkv, SharedPreferences, Database |
| file_media | 文件与媒体 | image_picker, file_picker, video_player, camera, MediaStore |
| networking | 网络请求 | okhttp, retrofit, volley, http, grpc, WebSocket |
| auth_security | 认证与安全 | firebase_auth, google_sign_in, oauth2, biometrics, KeyStore |
| analytics | 数据分析与埋点 | firebase_analytics, umeng, appsflyer, logEvent, Track |
| ads | 广告 | admob, AdWidget, BannerAd, facebook_ads, AdLoader |
| social_share | 社会化分享 | share, wechat_share, Intent.ACTION_SEND, qr_code |
| ui_component | UI 组件 | RecyclerView, View, animation, chart, calendar, dialog |
| device_sensor | 设备与传感器 | sensors, battery, connectivity, device_info, SensorManager |
| bluetooth_hardware | 蓝牙与硬件 | ble, BluetoothDevice, nfc, usb, BluetoothAdapter |
| ar_xr | AR/XR | arkit, arcore, ARSession, model_viewer, SceneView |
| ai_ml | AI 与机器学习 | tflite, mlkit, openai, inference, MLModel |
| platform_utility | 平台工具 | permission, clipboard, vibration, notification, PackageManager |

### 二级标签（tags 字段的合法值，按一级分类列出）

**payment**: alipay, wechat_pay, stripe, apple_pay, google_pay, paypal, razorpay, unionpay, paytm, in_app_purchase, subscription, one_time_purchase

**map_location**: google_maps, amap, baidu_map, mapbox, real_time_gps, background_location, geofencing, geocoding, poi_search, route_planning, offline_map, indoor_map

**push_notification**: fcm, jpush, getui, huawei_push, xiaomi_push, oppo_push, vivo_push, local_notification, rich_notification, topic_subscription, scheduled_notification

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
| UI | ArkUI主题框架, 状态组件, Tab标签栏组件, 按钮组件, 标题栏组件, 表单组件, 表格组件, 布局组件, 弹窗组件, 导航索引组件, 动画, 骨架屏组件, 滑动组件, 刷新组件, 聊天对话组件, 列表组件, 轮播组件, 媒体组件, 日历组件, 扫码组件, 篮选组件, 搜索页面模版, 图表绘制, 文本组件, 悬浮球组件, 指示器组件, UI组件框架, 卡片 |
| web开发技术 | web通信路由, web组件, 动画库, 跨平台应用运行容器, 网页解析, web数据库 |
| 安全 | 安全加解密, 身份验证, 完整性校验 |
| 编译构建 | 编译工具, 构建工具 |
| 测试框架 | 单元测试 |
| 存储与数据库 | 存储, 数据库 |
| 工具库 | 编程辅助工具, 程序语言工具, 地理数据处理, 第三方SDK, 电子邮件, 调试调优, 二维码处理, 华为移动服务功能库, 即时通讯, 计时器, 计算器, 日志记录和管理, 色彩管理工具, 数据处理与分析, 数学库, 通用唯一标识符, 文本处理工具, 应用组件模型, 正则表达式 |
| 跨平台开发框架 | 混合渲染框架, 自渲染框架 |
| 开发框架 | 权限请求框架, 任务调度框架, 事件驱动框架, 依赖注入框架, 游戏开发框架 |
| 媒体 | 视频, 音频, 图像 |
| 全球化 | 电话号码解析, 日期和时间, 字符编码国际标准, 语言检测 |
| 图形 | 矢量图形处理, 图形渲染, 位图绘制, 字体渲染 |
| 网络通信 | 短距通信, 网络I/O库, 网络路由管理, 网络通信框架, 通信协议 |
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
| 人工智能类 | 图像识别, 文字识别, 语音识别, 语音合成, 图像增强, 自然语言处理, 数字人 |
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
| 生活与学习 | 购物, 居家日常, 运动与健康, 旅游, 理财, 教育与学习, 社交与沟通 |
| 效率与性能 | 通用工具, 性能, 无障碍 |
| 多媒体与娱乐 | 动画与音视频处理, 图片与照片, 游戏与娱乐 |
| 办公与协同 | 流式文档处理, 版式文档处理, 电子签章, 报表制作与绘图, 会议与协作 |
| 外设交互 | 打印与扫描, 影像采集器, 扫码枪, POS机, 读卡器 |
| 开发与设计 | 开发工具, 组件库, 外观与主题 |
| 人工智能 | AI |
| 安全与隐私 | 安全控件, 安全防御, 隐私保护, 内容过滤 |

---

## Steps

### Step 1 — 读取元信息
```bash
cat build.gradle 2>/dev/null || cat build.gradle.kts 2>/dev/null || echo "NO_BUILD_GRADLE"
head -150 README.md 2>/dev/null || head -150 readme.md 2>/dev/null
cat gradle.properties 2>/dev/null | head -30
```
从 `dependencies` 和 `README` 快速锁定候选一级分类。

### Step 2 — 读取公开 API
```bash
find . -name "*.java" -o -name "*.kt" 2>/dev/null | grep -v "build/" | grep -v ".gradle/" | grep -v "test/" | head -20
cat src/main/java/**/*.java 2>/dev/null | head -200 || cat **/*.java 2>/dev/null | head -200
grep -rn "public\s+class\|public\s+interface\|public\s+fun" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/" | head -60
```

### Step 3 — 按候选分类 grep 关键词（在仓库根目录执行，相对路径）
```bash
EXCL="--exclude-dir=build --exclude-dir=.gradle --exclude-dir=test --exclude-dir=example --exclude-dir=sample"

# payment
grep -r "alipay\|wechat.*pay\|stripe\|BillingClient\|PaymentRequest\|paywall\|unionpay\|google.*pay\|apple.*pay\|InAppPurchase" --include="*.java" --include="*.kt" --include="*.gradle" --include="*.kts" --include="*.xml" -l -i $EXCL .

# map_location
grep -r "google.*maps\|amap\|baidu.*map\|mapbox\|geolocation\|geocoding\|LatLng\|Marker\|LocationManager\|FusedLocationProvider" --include="*.java" --include="*.kt" --include="*.gradle" --include="*.xml" -l -i $EXCL .

# push_notification
grep -r "firebase.*messaging\|jpush\|getui\|FirebaseMessaging\|NotificationManager\|FCM\|huawei.*push\|xiaomi.*push" --include="*.java" --include="*.kt" --include="*.gradle" --include="*.xml" -l -i $EXCL .

# im_chat
grep -r "rongcloud\|tencent.*im\|netease.*im\|agora.*chat\|sendbird\|ChatClient\|MessageKit\|IMService" --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL .

# audio_video_call
grep -r "agora\|zego\|trtc\|webrtc\|jitsi\|RtcEngine\|MediaPlayer\|liveStream\|VideoCall" --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL .

# storage
grep -r "sqlite\|room\|realm\|SharedPreferences\|mmkv\|objectbox\|Database\|Dao\b\|Entity\b" --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL .

# file_media
grep -r "image.*picker\|document.*picker\|video.*player\|camera\|ffmpeg\|MediaStore\|ExoPlayer\|ImageLoader" --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL .

# networking
grep -r "okhttp\|retrofit\|volley\|grpc\|WebSocket\|HttpURLConnection\|HttpClient\|Interceptor" --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL .

# auth_security
grep -r "firebase.*auth\|google.*sign.*in\|oauth2\|biometric\|KeyStore\|Fingerprint\|authenticate\|signIn\b" --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL .

# analytics
grep -r "firebase.*analytics\|umeng\|appsflyer\|adjust\|sensors_data\|mixpanel\|logEvent\|trackEvent\|Crashlytics\|sentry" --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL .

# ads
grep -r "admob\|BannerAd\|InterstitialAd\|applovin\|unity.*ads\|pangle\|loadAd\|AdRequest\|AdView" --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL .

# ui_component
grep -r "RecyclerView\|View\|animation\|chart\|calendar\|dialog\|BottomSheet\|ViewPager\|skeleton" --include="*.java" --include="*.kt" -l -i $EXCL .

# device_sensor
grep -r "SensorManager\|Accelerometer\|Gyroscope\|Barometer\|BatteryManager\|ConnectivityManager\|DeviceConfig" --include="*.java" --include="*.kt" -l -i $EXCL .

# bluetooth_hardware
grep -r "BluetoothAdapter\|BluetoothDevice\|BLE\|nfc\|usb\|NfcAdapter\|NfcManager" --include="*.java" --include="*.kt" -l -i $EXCL .

# ai_ml
grep -r "tflite\|mlkit\|onnx\|openai\|anthropic\|langchain\|llm\|TensorFlow\|MLModel" --include="*.java" --include="*.kt" --include="*.gradle" -l -i $EXCL .

# platform_utility
grep -r "Permission\|ClipboardManager\|Vibrator\|PackageManager\|Intent\|Notification\|Settings" --include="*.java" --include="*.kt" -l -i $EXCL .
```

### Step 4 — Android 权限与危险机制扫描

#### 4a — 扫描 AndroidManifest.xml 声明权限
```bash
find . -name "AndroidManifest.xml" 2>/dev/null | head -5
grep -r "uses-permission" --include="*.xml" . -h 2>/dev/null | grep -oE 'android:name="[^"]+"' | sort -u
```

#### 4b — 扫描 PROHIBITED 危险代码模式（Java/Kotlin 源码）
```bash
grep -r "DexClassLoader\|PathClassLoader\|BaseDexClassLoader\|InMemoryDexClassLoader" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/"
grep -r "de\.robv\.android\.xposed\|XposedBridge\|XposedHelpers\|IXposedHookLoadPackage" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/"
grep -r "Runtime\.exec.*[\"']su[\"']\|ProcessBuilder.*[\"']su[\"']\|checkRootMethod\|isRooted" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/"
```

#### 4c — 扫描 CONTROLLED_ACL 高危权限使用（Manifest + 源码）
```bash
grep -r "SYSTEM_ALERT_WINDOW\|TYPE_APPLICATION_OVERLAY\|TYPE_SYSTEM_ALERT" --include="*.xml" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/"
grep -r "AccessibilityService\|BIND_ACCESSIBILITY_SERVICE\|onAccessibilityEvent\|performGlobalAction" --include="*.xml" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/"
grep -r "BIND_DEVICE_ADMIN\|DevicePolicyManager\|DeviceAdminReceiver" --include="*.xml" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/"
grep -r "REQUEST_INSTALL_PACKAGES\|PackageInstaller\|ACTION_INSTALL_PACKAGE" --include="*.xml" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/"
grep -r "MANAGE_EXTERNAL_STORAGE\|ACTION_MANAGE_ALL_FILES\|AllFilesAccess" --include="*.xml" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/"
grep -r "WRITE_SETTINGS\|Settings\.System\|Settings\.Global" --include="*.xml" --include="*.java" --include="*.kt" . 2>/dev/null | grep -v "build/"
grep -r "REQUEST_IGNORE_BATTERY_OPTIMIZATIONS\|RECEIVE_BOOT_COMPLETED\|FOREGROUND_SERVICE" --include="*.xml" . -h 2>/dev/null | sort -u
```

#### 4d — 三级分类规则

| 级别 | 判定条件 | 典型信号 |
|------|---------|---------|
| `PROHIBITED` | 鸿蒙底层架构明确禁止，无平替 API | `DexClassLoader`/`PathClassLoader`（动态字节码加载）、Xposed/Frida hook（`XposedBridge`）、root 提权（`Runtime.exec("su")`） |
| `CONTROLLED_ACL` | 鸿蒙有对应能力但属高危受控，须 ACL 审批 | `BIND_ACCESSIBILITY_SERVICE`、`SYSTEM_ALERT_WINDOW`、`BIND_DEVICE_ADMIN`、`REQUEST_INSTALL_PACKAGES`、`WRITE_SETTINGS`、`MANAGE_EXTERNAL_STORAGE`、保活组合（三个权限同时出现） |
| `NORMAL_PASS` | 常规开放权限 | `INTERNET`、`CAMERA`、`RECORD_AUDIO`、`ACCESS_FINE_LOCATION`、`READ_EXTERNAL_STORAGE`、`BLUETOOTH_*`、`NFC`、`VIBRATE`、`WAKE_LOCK` |

### Step 5 — 读取命中最多的核心文件
命中文件数 ≥ 2 的分类，读取其核心 .java/.kt 文件前 200 行确认细节：
```bash
cat src/main/java/com/example/Main.java | head -200
```

---

## Output

```json
{
  "feature_list": [
    "支持支付宝 App 支付（调起支付宝客户端）",
    "支持支付宝 OAuth 授权登录",
    "支持获取支付宝用户 ID 和基本信息",
    "提供支付结果异步回调接口",
    "提供检测设备是否已安装支付宝的工具方法"
  ],
  "summary": "封装支付宝 Android SDK，提供支付和 OAuth 登录能力，适用于需接入支付宝的电商类应用。",
  "evidence": [
    "src/main/java/com/alipay/sdk/pay/PayTask.java:32 public void pay(...)",
    "build.gradle:58 com.alipay.sdk:alipaysdk-android:15.8.14"
  ],
  "android_permissions": {
    "PROHIBITED": [],
    "CONTROLLED_ACL": [
      {"permission": "android.permission.SYSTEM_ALERT_WINDOW", "note": "全局悬浮窗，鸿蒙需 ACL 审批"}
    ],
    "NORMAL_PASS": [
      "android.permission.INTERNET",
      "android.permission.ACCESS_NETWORK_STATE"
    ]
  },
  "taxonomy1": {
    "categories": ["payment", "auth_security"],
    "tags": ["alipay", "in_app_purchase", "oauth2"]
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