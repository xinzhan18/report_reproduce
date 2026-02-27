# Documentation Index

## 核心文档

### 使用指南

1. **[AGENT_MEMORY_SYSTEM.md](AGENT_MEMORY_SYSTEM.md)** ⭐ **重要**
   - Agent记忆系统完整使用指南
   - Markdown-based persona和memory管理
   - 如何初始化、查看和编辑agent记忆

2. **[OAUTH_AUTHENTICATION.md](OAUTH_AUTHENTICATION.md)** ⭐ **重要**
   - OAuth 2.0认证完整指南
   - 支持Anthropic和OpenAI
   - API Key vs OAuth配置方法

### 迁移和实施总结

3. **[MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md)**
   - Agent记忆系统迁移技术总结
   - 从SQLite到Markdown的完整迁移过程
   - 对比新旧系统优劣

4. **[OAUTH_SUPPORT_SUMMARY.md](OAUTH_SUPPORT_SUMMARY.md)**
   - OAuth支持实施总结
   - 快速入门指南
   - 常见问题解答

5. **[ENHANCEMENTS_SUMMARY.md](ENHANCEMENTS_SUMMARY.md)**
   - 系统增强功能总结
   - 新增特性列表

6. **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)**
   - 核心功能实现总结

### 升级和历史

7. **[UPGRADE_GUIDE.md](UPGRADE_GUIDE.md)**
   - 系统升级指南
   - 版本迁移说明

8. **[AGENT_INTELLIGENCE_INTEGRATION.md](AGENT_INTELLIGENCE_INTEGRATION.md)** *(历史文档)*
   - 旧的agent intelligence系统文档
   - 已被新的markdown memory系统取代
   - 保留作为参考

---

## 文档组织

```
docs/
├── README.md                            # 本文件 - 文档索引
├── AGENT_MEMORY_SYSTEM.md              # Agent记忆系统（主要使用指南）
├── OAUTH_AUTHENTICATION.md             # OAuth认证（主要使用指南）
├── MIGRATION_SUMMARY.md                # 迁移总结
├── OAUTH_SUPPORT_SUMMARY.md            # OAuth支持总结
├── ENHANCEMENTS_SUMMARY.md             # 增强功能总结
├── IMPLEMENTATION_SUMMARY.md           # 实现总结
├── UPGRADE_GUIDE.md                    # 升级指南
└── AGENT_INTELLIGENCE_INTEGRATION.md   # 历史文档
```

---

## 快速导航

### 我想...

**使用Agent记忆系统**
→ 阅读 [AGENT_MEMORY_SYSTEM.md](AGENT_MEMORY_SYSTEM.md)

**配置OAuth认证**
→ 阅读 [OAUTH_AUTHENTICATION.md](OAUTH_AUTHENTICATION.md)

**了解系统架构和新特性**
→ 阅读 [MIGRATION_SUMMARY.md](MIGRATION_SUMMARY.md)

**快速开始OAuth**
→ 阅读 [OAUTH_SUPPORT_SUMMARY.md](OAUTH_SUPPORT_SUMMARY.md)

**系统升级**
→ 阅读 [UPGRADE_GUIDE.md](UPGRADE_GUIDE.md)

---

## 其他文档位置

- **项目根目录**:
  - `README.md` - 项目主文档
  - `CLAUDE.md` - Claude Code工作指南

- **代码注释**:
  - 所有Python文件包含详细的docstrings
  - 关键功能有行内注释

---

**最后更新**: 2026-02-27
