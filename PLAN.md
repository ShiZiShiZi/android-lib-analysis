# Android Library Analyzer - GitHub 源码分析

## 系统架构

```
用户输入 GitHub URL (支持 monorepo 子路径)
       │
       ▼
┌─────────────────────┐
│ GitHub URL 解析     │ → owner/repo/branch/sub_path
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ git clone --depth 1 │ → 浅克隆到 repos/
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 定位包路径          │ → monorepo: repo/sub_path
└──────────┬──────────┘           单仓库: repo/
           │
           ▼
┌─────────────────────┐
│ android-analyzer    │ → 八维度分析
└─────────────────────┘
```

## 支持的 URL 格式

- `https://github.com/owner/repo`
- `https://github.com/owner/repo/tree/main`
- `https://github.com/square/okhttp/tree/master/okhttp-bom`

## 八维度分析

1. License（许可证）
2. Mobile Platform（厂商平台）
3. Cloud Services（云服务拓扑）
4. Payment（付费功能）
5. Features（功能分类）
6. Ecosystem（生态敏感型）
7. Dependency（依赖结构）
8. Code Stats（代码统计）

## 分析内容

### 依赖结构分析
- Gradle Maven 依赖（build.gradle dependencies）
- 本地 JAR/AAR 文件
- NDK C/C++ 库
- 预编译 .so 文件
- 平台专有 API（OpenGL ES、Camera2、Media NDK 等）

### 代码统计
- Java 代码规模
- Kotlin 代码规模
- C/C++ 代码规模
- 公开 API 面积（公开类和方法数）

### 厂商平台识别
- HMS（华为）
- GMS（Google）
- XIAOMI_OPEN（小米）
- OPPO_OPEN（OPPO）
- VIVO_OPEN（vivo）
- HONOR_OPEN（荣耀）
- MEIZU_OPEN（魅族）
- AGGREGATOR_PLATFORM（聚合平台）

## 使用方式

```bash
# 分析单个 Android 库
python main.py https://github.com/square/okhttp

# 分析 monorepo 子路径
python main.py https://github.com/square/okhttp/tree/master/okhttp-bom

# 指定输出文件
python main.py https://github.com/square/retrofit --output retrofit.json

# 保留克隆的仓库目录
python main.py https://github.com/square/okhttp --keep

# 详细日志
python main.py https://github.com/square/okhttp --verbose
```