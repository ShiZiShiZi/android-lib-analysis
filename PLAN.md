# React Native Library Analyzer - GitHub 源码分析

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
│ rn-analyzer Agent   │ → 八维度分析
└─────────────────────┘
```

## 支持的 URL 格式

- `https://github.com/owner/repo`
- `https://github.com/owner/repo/tree/main`
- `https://github.com/expo/expo/tree/main/packages/expo-camera`

## 八维度分析

1. License（许可证）
2. Mobile Platform（厂商平台）
3. Cloud Services（云服务拓扑）
4. Payment（付费功能）
5. Features（功能分类）
6. Ecosystem（生态敏感型）
7. Dependency（依赖结构）
8. Code Stats（代码统计）

## 使用方式

```bash
# 启动服务
python3 -m uvicorn web.app:app --host 0.0.0.0 --port 8000

# 访问
open http://localhost:8000
```