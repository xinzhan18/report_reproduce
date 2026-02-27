# scripts/ - 运维脚本层

**一旦此文件夹有变化,请更新本文件**

## 三行架构说明

1. **职责**: 提供系统初始化、数据迁移、运维管理等一次性脚本
2. **依赖**: core/database (数据库), config/auth_config (认证配置), tools (各类工具)
3. **输出**: 系统部署脚本、数据初始化脚本、维护工具脚本

## 文件清单

### setup_oauth.py
- **角色**: OAuth设置脚本 (OAuth Setup)
- **功能**: 配置OAuth2.0认证流程,获取并保存访问令牌

### test_auth.py
- **角色**: 认证测试脚本 (Auth Testing)
- **功能**: 测试API认证是否正常,验证token有效性

### initialize_agent_memories.py
- **角色**: Agent记忆初始化 (Agent Memory Initialization)
- **功能**: 初始化Agent记忆系统的数据库结构和初始数据

### initialize_domains.py
- **角色**: 领域初始化 (Domain Initialization)
- **功能**: 初始化论文领域分类的类别定义和规则

### classify_existing_papers.py
- **角色**: 论文分类脚本 (Paper Classification)
- **功能**: 对已存储的论文进行批量领域分类

### migrate_database_v2.py
- **角色**: 数据库迁移脚本 (Database Migration)
- **功能**: 执行数据库schema升级,从v1迁移到v2版本

## 更新历史

- 2026-02-27: 创建此文档,记录当前架构
