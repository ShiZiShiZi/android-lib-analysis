---
name: dependency-analysis
description: "Analyze Android library dependency structure including Gradle deps, Maven deps, local JAR/AAR, NDK C/C++ libs"
---

## Goal
对 Android 三方库进行完整依赖结构分析，按依赖类型分类输出，并识别库类型、SDK 版本要求、平台 API 依赖。

**严格按以下 5 步顺序执行，所有命令必须在给定仓库路径下运行。**

---

## 最终输出结构（6 个顶层字段）

1. `library_metadata`       — Step 1 产出
2. `gradle_deps`            — Step 2 产出（Maven 远程依赖）
3. `local_jar_aar_deps`     — Step 3 产出（本地 JAR/AAR 文件）
4. `c_library_deps`         — Step 4 产出（NDK C/C++ 库）
5. `so_deps`                — Step 4 产出（预编译 .so 文件）
6. `platform_api_deps`      — Step 5 产出（Android 平台专有 API）

---

## source_availability 判定规则（Step 2 / 3 / 4 共用）

对 `gradle_deps`、`local_jar_aar_deps`、`c_library_deps`、`so_deps` 中每个条目填写：
- `source_availability`：按下表判定
- `description`：一句话中文说明该库是什么（如"支付宝官方 Android SDK"、"OkHttp 网络请求库"）

| 值 | 判断规则 |
|----|---------|
| `SOURCE_IN_REPO` | `source_type` 为 `LOCAL_FILE`，路径在仓库内；本地 .aar/.jar/.so 可在仓库中找到 |
| `OPEN_SOURCE_COMMUNITY` | 知名开源库，可在公开平台找到源码。包括：`androidx.*`、`com.google.android.material`、OkHttp、Retrofit、Glide、Kotlin 标准库、Gson、Moshi、Room、WorkManager；NDK 系统库（`libc`、`libm`、`libz`、`libssl`、`log`、`android`） |
| `COMMERCIAL_PUBLIC` | 公开商业或生态厂商 SDK，有官方文档但源码不完全开放。包括：`com.google.android.gms.*`、`com.google.firebase.*`、`com.huawei.*`、支付宝、微信、极光推送、友盟等 |
| `PRIVATE_INTERNAL` | 私有 Maven 仓库 URL、无法在公开平台查到的内部包名 |
| `UNKNOWN_BLACKBOX` | 本地 .aar / .jar / .so 且无法匹配任何已知库，来源不明 |

> `androidx.*` → `OPEN_SOURCE_COMMUNITY`（不是 COMMERCIAL_PUBLIC）
> `com.google.android.gms:play-services-*` 和 `com.google.firebase:*` → `COMMERCIAL_PUBLIC`

---

## Step 1 — 库元数据、类型、SDK 版本

### 1a — 读取基础文件

```bash
ls -la
find . -name "build.gradle" -o -name "build.gradle.kts" 2>/dev/null | grep -v ".gradle/" | head -10
find . -name "*.aar" -o -name "*.jar" 2>/dev/null | grep -v ".gradle/" | head -20
find . -name "AndroidManifest.xml" 2>/dev/null | head -5
cat build.gradle 2>/dev/null || cat build.gradle.kts 2>/dev/null || echo "NO_ROOT_BUILD"
cat gradle.properties 2>/dev/null | head -30
```

### 1b — 判断 library_type

| library_type | 条件 |
|--------------|------|
| `aar_library` | 存在 `.aar` 文件，或有 `android { ... }` 块且发布配置为 AAR |
| `jar_library` | 存在 `.jar` 文件，且无 `android { ... }` 块，纯 Java/Kotlin 库 |
| `source_library` | 有 build.gradle 但无预编译 .aar/.jar，需要编译后才能使用 |
| `mixed` | 同时存在 .aar/.jar 和源码目录 |

### 1c — SDK 版本信息

```bash
grep -rn "minSdk\|minSdkVersion\|targetSdk\|targetSdkVersion\|compileSdk\|compileSdkVersion" \
  --include="*.gradle" --include="*.kts" --include="*.xml" . 2>/dev/null | head -20
cat AndroidManifest.xml 2>/dev/null | grep -E "uses-sdk|minSdk|targetSdk" | head -5
```

### 1d — has_java_kotlin 与 has_ndk_cpp

```bash
# Java/Kotlin
find . -name "*.java" -o -name "*.kt" 2>/dev/null | grep -v ".gradle/" | grep -v "build/" | head -10

# NDK/C++
find . -name "*.c" -o -name "*.cpp" -o -name "*.h" -o -name "CMakeLists.txt" -o -name "Android.mk" 2>/dev/null | grep -v ".gradle/" | grep -v "build/" | head -10
```

**判定规则**：
- `has_java_kotlin`：存在 .java 或 .kt 文件（排除 .gradle/、build/）则为 `true`
- `has_ndk_cpp`：存在 .c / .cpp / .h / CMakeLists.txt / Android.mk 文件则为 `true`

### 1e — repository_url

从以下来源提取（优先级递减）：
1. gradle.properties 中的 `POM_URL` 或类似字段
2. README.md 中的 GitHub 链接
3. 无则 `null`

---

## Step 2 — Gradle Maven 依赖

```bash
# 读取所有 build.gradle 文件
find . \( -name "build.gradle" -o -name "build.gradle.kts" \) ! -path "*/.gradle/*" ! -path "*/build/*" 2>/dev/null | head -10

# 主 build.gradle
cat build.gradle 2>/dev/null || cat build.gradle.kts 2>/dev/null || echo "NO_BUILD_GRADLE"

# gradle.properties（解析变量值）
cat gradle.properties 2>/dev/null | grep -v "^#" | head -30

# settings.gradle（了解多模块结构）
cat settings.gradle 2>/dev/null || cat settings.gradle.kts 2>/dev/null | head -20
```

从 `build.gradle` 提取所有 `implementation`/`api`/`compileOnly`/`runtimeOnly` 依赖条目，每条字段：
- `name`：`group:artifact`（如 `com.squareup.okhttp3:okhttp`）
- `version`：版本号（若为变量如 `$okhttpVersion`，从 `gradle.properties` 查找实际值并以 `变量名=实际值` 格式标注）
- `dep_type`：`implementation | api | compileOnly | runtimeOnly | testImplementation | debugImplementation | releaseImplementation`
- `source_type`：`REMOTE`（Maven 坐标）
- `source_availability`：按共用规则判定
- `description`：一句话中文说明
- `evidence`：`build.gradle:<行号>`

---

## Step 3 — 本地 JAR/AAR 文件

```bash
find . \( -name "*.aar" -o -name "*.jar" \) ! -path "*/.gradle/*" ! -path "*/build/*" ! -path "*/node_modules/*" 2>/dev/null | head -30
```

每条字段：
- `name`：库名（不含版本号和后缀，如 `alipaysdk`）
- `filename`：完整文件名含后缀
- `source_type`：`LOCAL_FILE`
- `source_availability`：`SOURCE_IN_REPO` 或 `UNKNOWN_BLACKBOX`
- `description`：一句话中文说明
- `evidence`：文件路径列表

---

## Step 4 — C/C++ 库与 SO 文件

### 4a — CMake / Android.mk

```bash
find . -name "CMakeLists.txt" -o -name "Android.mk" -o -name "Application.mk" 2>/dev/null | grep -v ".gradle/" | head -10
cat CMakeLists.txt 2>/dev/null | head -150
cat Android.mk 2>/dev/null | head -50
```

从 CMakeLists.txt 的 `target_link_libraries` 中提取 C 库依赖：
- NDK 系统库（`log`、`android`、`z`、`m`、`c`、`dl`、`pthread`、`atomic`、`stdc++`）→ `OPEN_SOURCE_COMMUNITY`
- 其他库名 → 查证来源后判定

### 4b — SO 文件

```bash
find . -name "*.so" ! -path "*/.gradle/*" ! -path "*/build/*" 2>/dev/null | head -30
```

每条字段：
- `path`：完整文件路径
- `platform`：`android`
- `source_availability`：`UNKNOWN_BLACKBOX`（预编译二进制通常来源不明）
- `description`：一句话中文说明
- `evidence`：文件路径列表

---

## Step 5 — 平台专有系统 API

Android 系统独有、在其他平台需要寻找替代方案的系统 API：

**来源**：CMakeLists.txt `target_link_libraries` + AndroidManifest.xml `uses-feature` + 源码 import

```bash
grep -rn "target_link_libraries" --include="CMakeLists.txt" . 2>/dev/null | head -10
grep -rn "uses-feature" --include="*.xml" . 2>/dev/null | head -10
grep -rn "import android\.hardware\|import android\.media\|import android\.opengl\|import android\.camera\|import android\.location\|import android\.bluetooth\|import android\.nfc" \
  --include="*.java" --include="*.kt" . 2>/dev/null | head -20
```

| 库名/API | 含义 |
|---------|------|
| `GLESv1_CM`、`GLESv2`、`GLESv3` | OpenGL ES 图形 API |
| `EGL` | EGL 图形上下文 |
| `vulkan` | Vulkan 图形/计算 API |
| `mediandk` | Android Media NDK（视频编解码） |
| `OpenSLES` | OpenSL ES 音频 API |
| `camera2ndk` | Camera2 NDK |
| `jnigraphics` | Bitmap 像素访问 API |
| `nativewindow` | ANativeWindow 图形窗口 |
| `android.hardware.camera2` | Camera2 API |
| `android.location` | 定位服务 |
| `android.bluetooth` | 蓝牙 |
| `android.nfc` | NFC |

每条字段：`name`、`platform`（`android`）、`description`、`evidence`

---

## Output

```json
{
  "library_metadata": {
    "library_type": "source_library",
    "has_java_kotlin": true,
    "has_ndk_cpp": false,
    "min_sdk_version": "21",
    "target_sdk_version": "34",
    "repository_url": "https://github.com/square/okhttp"
  },
  "gradle_deps": {
    "dependencies": [
      {
        "name": "com.squareup.okio:okio",
        "version": "3.6.0",
        "dep_type": "implementation",
        "source_type": "REMOTE",
        "source_availability": "OPEN_SOURCE_COMMUNITY",
        "description": "OkIO 高效 I/O 库",
        "evidence": "build.gradle:45"
      }
    ],
    "test_dependencies": [
      {
        "name": "org.junit.jupiter:junit-jupiter",
        "version": "5.10.0",
        "dep_type": "testImplementation",
        "source_availability": "OPEN_SOURCE_COMMUNITY",
        "description": "JUnit 5 测试框架",
        "evidence": "build.gradle:80"
      }
    ]
  },
  "local_jar_aar_deps": {
    "deps": []
  },
  "c_library_deps": [
    {
      "name": "log",
      "platform": "android",
      "source_availability": "OPEN_SOURCE_COMMUNITY",
      "description": "Android NDK 日志系统库",
      "evidence": ["CMakeLists.txt:15 (target_link_libraries ... log)"]
    }
  ],
  "so_deps": [],
  "platform_api_deps": [
    {
      "name": "OpenGL ES (GLESv2)",
      "platform": "android",
      "description": "Android 图形渲染 API",
      "evidence": ["CMakeLists.txt:18 (target_link_libraries ... GLESv2)"]
    }
  ]
}