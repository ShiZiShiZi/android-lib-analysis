---
name: dependency-analysis
description: "Analyze React Native library dependency structure including npm, Android native, iOS native dependencies, architecture type, new-arch support, and platform support"
---

## Goal
对 React Native 三方库进行完整依赖结构分析，按依赖类型分类输出，并识别插件架构类型、新旧架构兼容性、支持平台。

**严格按以下 5 步顺序执行，所有命令必须在给定仓库路径下运行。**

---

## 最终输出结构（7 个顶层字段）

1. `plugin_metadata`       — Step 1 产出
2. `npm_deps`              — Step 2 产出（npm 包依赖，无需 source_availability）
3. `android_jar_aar_deps`  — Step 3 产出（build.gradle Maven + 本地 JAR/AAR）
4. `ios_pod_deps`          — Step 4 产出（.podspec CocoaPod 依赖）
5. `c_library_deps`        — Step 5 产出（Android NDK / iOS 链接的 C 库）
6. `so_deps`               — Step 5 产出（仓库内预编译 .so / .a 二进制文件）
7. `platform_api_deps`     — Step 5 产出（平台专有系统 API，如 OpenGL ES / UIKit）

---

## source_availability 判定规则（Step 3 / 4 / 5 共用）

对 `android_jar_aar_deps`、`ios_pod_deps`、`c_library_deps`、`so_deps` 中每个条目填写：
- `source_availability`：按下表判定
- `description`：一句话中文说明该库是什么（如"支付宝官方 Android SDK"、"OpenSSL 安全通信库"）

| 值 | 判断规则 |
|----|---------|
| `SOURCE_IN_REPO` | `source_type` 为 `LOCAL_FILE` / `LOCAL_PATH`，路径在仓库内；本地 .aar/.jar/.so/.a 可在仓库中找到 |
| `OPEN_SOURCE_COMMUNITY` | 知名开源库，可在公开平台找到源码。包括：`androidx.*`、OkHttp、Retrofit、Glide、Kotlin 标准库、Alamofire、SDWebImage；NDK 系统库（`libc`、`libm`、`libz`、`libssl`、`log`、`android`）；iOS 基础系统库 |
| `COMMERCIAL_PUBLIC` | 公开商业或生态厂商 SDK，有官方文档但源码不完全开放。包括：`com.google.android.gms.*`、`com.google.firebase.*`、`com.huawei.*`、支付宝、微信、极光推送等 |
| `PRIVATE_INTERNAL` | 私有 Maven 仓库 URL、私有 git Pod source、无法在公开平台查到的内部包名 |
| `UNKNOWN_BLACKBOX` | 本地 .aar / .jar / .so / .a 且无法匹配任何已知库，来源不明 |

> `androidx.*` → `OPEN_SOURCE_COMMUNITY`（不是 COMMERCIAL_PUBLIC）
> `com.google.android.gms:play-services-*` 和 `com.google.firebase:*` → `COMMERCIAL_PUBLIC`

---

## Step 1 — 库元数据、架构类型、新旧架构、支持平台

### 1a — 读取基础文件

```bash
cat package.json
ls -la
ls -la android/ 2>/dev/null || echo "NO_ANDROID_DIR"
ls -la ios/     2>/dev/null || echo "NO_IOS_DIR"
ls -la src/     2>/dev/null | head -20
cat react-native.config.js 2>/dev/null || echo "NO_RN_CONFIG"
```

### 1b — 架构类型信号检测

```bash
# codegenConfig（新架构核心标志）
python3 -c "
import json, sys
d = json.load(open('package.json', errors='replace'))
cc = d.get('codegenConfig', {})
print('codegenConfig:', json.dumps(cc) if cc else 'NONE')
" 2>/dev/null

# Expo Modules
grep -E '"expo-modules-core"' package.json 2>/dev/null | head -3

# Fabric component（react-native.config.js 声明 component）
grep -n "component\b" react-native.config.js 2>/dev/null | head -5
```

### 1c — 新旧架构兼容性信号检测

```bash
# === Android 新架构信号 ===
# TurboModule / JSI
grep -rn "TurboReactPackage\|TurboModuleManagerDelegate\|ReactPackageTurboModuleManagerDelegate\
\|com\.facebook\.react\.turbomodule\|JSIModule\|NativeModule.*Spec\b" \
  android/src/ --include="*.java" --include="*.kt" 2>/dev/null | head -10

# Fabric component（Android）
grep -rn "ViewManagerDelegate\|ViewManagerInterface\|ReactShadowNode\|FabricViewManager\
\|com\.facebook\.react\.uimanager\.annotations" \
  android/src/ --include="*.java" --include="*.kt" 2>/dev/null | head -10

# CMakeLists 新架构信号
grep -rn "react_codegen\|ReactCommon\|jsi\b\|turbomodule\|REACT_NATIVE_NEW_ARCHITECTURE" \
  android/ --include="CMakeLists.txt" --include="Android.mk" 2>/dev/null | head -10

# === Android 旧架构信号 ===
grep -rn "ReactContextBaseJavaModule\|ReactPackage\b\|ViewGroupManager\b\|SimpleViewManager\b\
\|@ReactMethod\b\|@ReactProp\b" \
  android/src/ --include="*.java" --include="*.kt" 2>/dev/null | head -10

# === iOS 新架构信号 ===
grep -rn "RCTTurboModule\|RCTInitializing\|RCTViewComponentView\|RCTFabricComponentsPlugins\
\|RCTNativeModule\|REACT_NATIVE_NEW_ARCHITECTURE\|RCT_EXPORT_MODULE_NO_LOAD" \
  ios/ --include="*.h" --include="*.m" --include="*.mm" --include="*.swift" 2>/dev/null | head -10

# .mm 文件（ObjC++ 是新架构 C++ 互操作的标志）
find ios/ -name "*.mm" ! -path "*/Pods/*" ! -path "*/example/*" 2>/dev/null | head -5

# === iOS 旧架构信号 ===
grep -rn "RCTBridgeModule\|RCTEventEmitter\|RCTViewManager\b\|RCT_EXPORT_MODULE\b\
\|RCT_EXPORT_METHOD\b\|RCT_REMAP_METHOD\b" \
  ios/ --include="*.h" --include="*.m" --include="*.mm" 2>/dev/null | head -10
```

### 1d — 支持平台扩展检测

```bash
# Windows
ls windows/ 2>/dev/null && echo "HAS_WINDOWS_DIR"
grep -i "react-native-windows\|\"windows\"\|'windows'" package.json 2>/dev/null | head -3

# macOS
ls macos/ 2>/dev/null && echo "HAS_MACOS_DIR"
grep -i "react-native-macos\|\"macos\"\|'macos'" package.json 2>/dev/null | head -3

# tvOS（通常复用 ios/ 目录，需从 podspec 或 package.json keywords 判断）
grep -iE "tvos|appletvos" ios/*.podspec package.json 2>/dev/null | head -5

# Web（react-native-web 兼容）
grep -iE '"browser"|"web"|react-native-web' package.json 2>/dev/null | head -3

# visionOS
ls visionos/ 2>/dev/null && echo "HAS_VISIONOS_DIR"
grep -iE "visionos|xros" ios/*.podspec package.json 2>/dev/null | head -3
```

---

### architecture 判定逻辑（按顺序，第一个匹配即停止）

| 优先级 | 条件 | 结论 |
|--------|------|------|
| 1 | `codegenConfig` 存在，且 `type` 为 `"components"` 或含 `components` key | `fabric_component` |
| 2 | `codegenConfig` 存在，且 `type` 为 `"modules"` 或含 `modules` key | `turbo_module` |
| 3 | `codegenConfig` 存在但 type 不明确，或检测到 CMakeLists react_codegen/jsi 信号 | `turbo_module` |
| 4 | `dependencies`/`peerDependencies` 含 `expo-modules-core` | `expo_module` |
| 5 | `react-native.config.js` 存在且声明了 `component` | `fabric_component` |
| 6 | 有 android/ 或 ios/ 目录且含原生代码（.java/.kt/.m/.mm/.swift） | `monolithic` |
| 7 | 其余（纯 JS/TS 库） | `js_only` |

---

### new_arch_support 判定逻辑

基于 1c 步骤检测结果综合判断：

| 值 | 条件 |
|----|------|
| `full` | 只有新架构信号（TurboModule/Fabric/codegenConfig），无旧架构信号（无 RCTBridgeModule/ReactContextBaseJavaModule） |
| `partial` | 同时存在新架构信号和旧架构信号（双支持/兼容模式） |
| `none` | 只有旧架构信号，无新架构信号 |
| `unknown` | 无原生代码（js_only/expo），或信号不足以判断 |

---

### platform_support 判定逻辑

| 平台 | 判定条件 |
|------|---------|
| `android` | 存在 `android/` 目录 |
| `ios` | 存在 `ios/` 目录或 `.podspec` 文件 |
| `windows` | 存在 `windows/` 目录，或 package.json 含 `react-native-windows` |
| `macos` | 存在 `macos/` 目录，或 package.json 含 `react-native-macos` |
| `tvos` | podspec 含 `tvos` platform 声明，或 package.json keywords 含 `tvos` |
| `web` | package.json 含 `"browser"` 字段，或 keywords 含 `react-native-web` |
| `visionos` | 存在 `visionos/` 目录，或 podspec 含 `visionos` 声明 |

---

### has_native_code 与 repository_url

**has_native_code**：android/ 下有 .java/.kt 或 ios/ 下有 .swift/.m/.mm 则为 true。

**repository_url**：取 package.json `repository.url` 或 `repository`（仅限 github.com / gitlab.com / bitbucket.org / gitee.com / codeberg.org / gitcode.com）；均无则 `null`。

**environment**：从 `peerDependencies` 提取 react 和 react-native 约束，各含 `raw`、`min`、`min_op`。

---

## Step 2 — npm 包依赖

```bash
cat package.json
# transitive_count：package-lock.json 用 packages 总数减去直接依赖数；yarn.lock 用行数粗估
cat package-lock.json 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    pkgs = d.get('packages', {})
    direct = len(d.get('dependencies', {})) + len(d.get('devDependencies', {}))
    print('lock_packages:', len(pkgs), 'direct:', direct, 'transitive:', max(0, len(pkgs) - direct - 1))
except: print('PARSE_ERROR')
" 2>/dev/null || \
python3 -c "
from pathlib import Path
yl = Path('yarn.lock')
if yl.exists():
    blocks = [l for l in yl.read_text(errors='replace').splitlines() if l and not l.startswith(' ') and not l.startswith('#')]
    print('yarn_lock_entries:', len(blocks))
else:
    print('NO_LOCK_FILE')
" 2>/dev/null
```

从 `package.json` 提取：
- `dependencies`：运行时依赖，每条含 `name`、`version_constraint`、`evidence`
- `devDependencies`：开发依赖，每条含 `name`、`version_constraint`、`evidence`
- `peerDependencies`：对宿主的依赖要求，每条含 `name`、`version_constraint`、`evidence`
- `optionalDependencies`：可选依赖（部分库用于平台选择性原生模块），每条含 `name`、`version_constraint`、`evidence`；无则空数组
- `transitive_count`：package-lock.json 中 packages 总数减去 direct+dev 数量（无 lock 则 -1）

---

## Step 3 — Android JAR/AAR 依赖

```bash
# 读取所有 build.gradle 文件
find android/ \( -name "build.gradle" -o -name "build.gradle.kts" \) 2>/dev/null | head -5
cat android/build.gradle 2>/dev/null || cat android/app/build.gradle 2>/dev/null || echo "NO_ANDROID_BUILD"

# 读取 gradle.properties（解析变量值）
cat android/gradle.properties 2>/dev/null | grep -v "^#" | head -30

# 读取 settings.gradle（了解子模块）
cat android/settings.gradle 2>/dev/null | head -20

# Maven 仓库声明（用于 PRIVATE_INTERNAL 判定）
grep -rn "maven\s*{.*url\|maven(url\|repositories\s*{" \
  android/ --include="*.gradle" --include="*.kts" 2>/dev/null | head -20

# 本地 JAR/AAR 文件
find android/ \( -name "*.aar" -o -name "*.jar" \) 2>/dev/null | grep -v "node_modules" | head -20
```

从 `build.gradle` 提取所有 `implementation`/`api`/`compileOnly`/`runtimeOnly` 依赖条目，每条字段：
- `name`：
  - REMOTE 类型：`group:artifact`（如 `com.google.android.gms:play-services-base`）
  - LOCAL_FILE 类型：库名（不含版本号和后缀，如 `afservicesdk`）
- `version`：版本号（若为变量如 `$sdkVersion`，从 `gradle.properties` 查找实际值并以 `变量名=实际值` 格式标注）
- `filename`：**仅 LOCAL_FILE 类型填写**，完整文件名含后缀；REMOTE 类型此字段为 `null`
- `dep_type`：`implementation | api | compileOnly | runtimeOnly | testImplementation | debugImplementation | releaseImplementation`
- `source_type`：`REMOTE`（Maven 坐标）/ `LOCAL_FILE`（fileTree / 本地 .aar/.jar）
- `source_availability`：按共用规则判定；maven 仓库为非公开 URL 则 `PRIVATE_INTERNAL`
- `description`：一句话中文说明
- `evidence`：`android/build.gradle:<行号>`

同时记录：
- `has_java_kotlin`：android/ 下存在 .java 或 .kt 文件则为 `true`
- `has_ndk_cpp`：android/ 下存在 .c / .cpp / CMakeLists.txt / Android.mk 则为 `true`

---

## Step 4 — iOS Pod 依赖

```bash
find ios/ -name "*.podspec" 2>/dev/null | head -3
cat ios/*.podspec 2>/dev/null || echo "NO_PODSPEC"
```

从 `.podspec` 提取所有依赖，包括：
- 顶层 `s.dependency` 条目
- **所有 subspec 下的 `ss.dependency` 条目**（`s.subspec` 块内）

每条字段：
- `name`：Pod 名称
- `version`：版本约束（如 `~> 15.7.9`）
- `dep_type`：`dependency` / `test_spec_dependency`
- `subspec`：所属 subspec 名称（顶层依赖填 `null`）
- `source_type`：`REMOTE`（标准 CocoaPods）/ `LOCAL_PATH`（`:path =>`）/ `GIT_SOURCE`（`:git =>`）
- `source_availability`：按共用规则判定；私有 git source / 非公开 spec repo 则 `PRIVATE_INTERNAL`
- `description`：一句话中文说明
- `evidence`：`ios/<name>.podspec:<行号>`

同时记录：
- `has_native_code`：ios/ 下存在 .h / .m / .swift / .mm 文件则为 `true`

---

## Step 5 — C 库 / SO / 平台 API 分析

```bash
# Android NDK
find android/ \( -name "CMakeLists.txt" -o -name "Android.mk" \) 2>/dev/null | head -5
cat android/CMakeLists.txt android/src/main/cpp/CMakeLists.txt 2>/dev/null | head -120
find android/ -name "*.so" 2>/dev/null | grep -v "node_modules" | head -20

# iOS 原生
find ios/ -name "*.podspec" 2>/dev/null | xargs grep -h "frameworks\|libraries\|vendored" 2>/dev/null
find ios/ \( -name "*.a" -o -name "*.framework" \) 2>/dev/null | grep -v "Pods/" | head -20
find ios/ \( -name "*.h" -o -name "*.m" -o -name "*.mm" \) 2>/dev/null | grep -v "Pods/" | head -10
```

将结果分类到以下三个输出字段：

### c_library_deps — C 库依赖

收集所有以 C 接口形式链接的库（不含平台专有 API）：
- **Android NDK 来源**：CMakeLists.txt `target_link_libraries` 中属于通用系统库的条目（`log`、`android`、`z`、`m`、`c`、`dl`、`pthread`、`atomic`、`stdc++`）
- **iOS 来源**：`s.libraries` 中指定的 C 库（如 `z`、`sqlite3`、`c++`）

每条字段：`name`、`platform`（`android` / `ios` / `cross_platform`）、`source_availability`、`description`、`evidence`

### so_deps — 预编译二进制

仓库内所有预编译的 .so / .a 文件（不含通过 Maven/CocoaPods 远程拉取的）：
- Android：`android/` 下的 .so 文件（jniLibs/ 或 libs/ 目录）
- iOS：`ios/` 下的 .a 文件和本地 .framework（排除 Pods/）

每条字段：`path`、`platform`（`android` / `ios` / `cross_platform`）、`source_availability`、`description`、`evidence`

### platform_api_deps — 平台专有系统 API

平台独有、在其他平台需要寻找替代方案的系统 API：

**Android 来源**（CMakeLists.txt `target_link_libraries` 中的平台 API）：

| 库名 | API 含义 |
|------|---------|
| `GLESv1_CM`、`GLESv2`、`GLESv3` | OpenGL ES 图形 API |
| `EGL` | EGL 图形上下文 |
| `vulkan` | Vulkan 图形/计算 API |
| `mediandk` | Android Media NDK（视频编解码） |
| `OpenSLES` | OpenSL ES 音频 API |
| `camera2ndk` | Camera2 NDK |
| `jnigraphics` | Bitmap 像素访问 API |
| `nativewindow` | ANativeWindow 图形窗口 |

**iOS 来源**（`.podspec` 的 `s.frameworks` / `s.weak_frameworks`）：

| Framework | API 含义 |
|-----------|---------|
| `UIKit` | iOS UI 框架 |
| `CoreMotion` | 运动传感器 |
| `AVFoundation` | 音视频 |
| `CoreBluetooth` | 蓝牙 |
| `ARKit` | 增强现实 |
| `CoreML` | 机器学习 |
| `Metal` | GPU 编程 |
| `CoreLocation` | 位置服务 |
| `MapKit` | 地图 |
| `StoreKit` | App 内购 |
| `AuthenticationServices` | Sign in with Apple |
| `LocalAuthentication` | 生物认证 |
| `WebKit` | Web 渲染 |
| `CallKit` | 通话 UI |
| `PushKit` | VoIP 推送 |
| `UserNotifications` | 通知 |
| `SafariServices` | Safari 集成 |
| `HealthKit` | 健康数据 |
| `HomeKit` | 智能家居 |
| `EventKit` | 日历/提醒 |
| `Contacts` / `ContactsUI` | 通讯录 |
| `PhotosUI` / `Photos` | 相册访问 |
| 其他非 Foundation/CoreFoundation 的 Framework | 平台专有 API |

> `Foundation`、`CoreFoundation` 属于基础系统库，归入 `c_library_deps`，不放此处。

每条字段：`name`、`platform`（`android` / `ios`）、`description`、`evidence`

---

## Output

```json
{
  "plugin_metadata": {
    "architecture": "monolithic | js_only | turbo_module | fabric_component | expo_module",
    "new_arch_support": "full | partial | none | unknown",
    "new_arch_evidence": [
      "android/src/main/java/Foo.kt:12 (TurboReactPackage)",
      "ios/Foo.mm:5 (RCTTurboModule)"
    ],
    "platform_support": ["android", "ios"],
    "has_native_code": true,
    "repository_url": "https://github.com/example/react-native-alipay",
    "environment": {
      "react": {"raw": ">=18.0.0", "min": "18.0.0", "min_op": ">="},
      "react_native": {"raw": ">=0.71.0", "min": "0.71.0", "min_op": ">="}
    }
  },
  "npm_deps": {
    "dependencies": [
      {"name": "react-native-inappbrowser-reborn", "version_constraint": "^3.6.3", "evidence": "package.json:15"}
    ],
    "devDependencies": [
      {"name": "typescript", "version_constraint": "^5.0.0", "evidence": "package.json:25"}
    ],
    "peerDependencies": [
      {"name": "react", "version_constraint": ">=18.0.0", "evidence": "package.json:30"},
      {"name": "react-native", "version_constraint": ">=0.71.0", "evidence": "package.json:31"}
    ],
    "optionalDependencies": [],
    "transitive_count": 45
  },
  "android_jar_aar_deps": {
    "has_java_kotlin": true,
    "has_ndk_cpp": false,
    "deps": [
      {
        "name": "com.alipay.sdk:alipaysdk-android",
        "version": "15.8.14",
        "filename": null,
        "dep_type": "implementation",
        "source_type": "REMOTE",
        "source_availability": "COMMERCIAL_PUBLIC",
        "description": "支付宝官方 Android SDK",
        "evidence": "android/build.gradle:28"
      }
    ]
  },
  "ios_pod_deps": {
    "has_native_code": true,
    "deps": [
      {
        "name": "AlipaySDK-iOS",
        "version": "~> 15.7.9",
        "dep_type": "dependency",
        "subspec": null,
        "source_type": "REMOTE",
        "source_availability": "COMMERCIAL_PUBLIC",
        "description": "支付宝官方 iOS SDK",
        "evidence": "ios/RNAlipay.podspec:18"
      }
    ]
  },
  "c_library_deps": [
    {
      "name": "log",
      "platform": "android",
      "source_availability": "OPEN_SOURCE_COMMUNITY",
      "description": "Android NDK 日志系统库",
      "evidence": ["android/CMakeLists.txt:12 (target_link_libraries ... log)"]
    }
  ],
  "so_deps": [
    {
      "path": "android/src/main/jniLibs/arm64-v8a/libfoo.so",
      "platform": "android",
      "source_availability": "UNKNOWN_BLACKBOX",
      "description": "来源不明的预编译 ARM64 动态库",
      "evidence": ["android/src/main/jniLibs/arm64-v8a/libfoo.so"]
    }
  ],
  "platform_api_deps": [
    {
      "name": "OpenGL ES (GLESv2)",
      "platform": "android",
      "description": "Android 图形渲染 API",
      "evidence": ["android/CMakeLists.txt:15 (target_link_libraries ... GLESv2)"]
    },
    {
      "name": "CoreMotion",
      "platform": "ios",
      "description": "iOS 运动传感器框架",
      "evidence": ["ios/RNAlipay.podspec:20 (s.frameworks 'CoreMotion')"]
    }
  ]
}
```

**`new_arch_support` 填写规范：**
- `new_arch_evidence`：列出支撑判断的具体文件和代码行，新旧架构信号各取最具代表性的 1-3 条
- `new_arch_support = unknown` 时，`new_arch_evidence` 填 `["js_only 库，无原生代码"]` 或 `["原生代码信号不足"]`
