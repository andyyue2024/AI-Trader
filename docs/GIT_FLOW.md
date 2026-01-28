# AI-Trader Git Flow 工作流指南

## 分支策略

### 主要分支
- **main**: 生产环境代码，只接受 release 和 hotfix 合并
- **develop**: 开发主分支，所有功能开发的集成分支

### 辅助分支
- **feature/xxx**: 新功能开发
- **bugfix/xxx**: Bug 修复
- **release/x.x.x**: 版本发布准备
- **hotfix/x.x.x**: 紧急生产修复

## 工作流程

### 1. 开发新功能

```bash
# 从 develop 创建 feature 分支
git checkout develop
git pull origin develop
git checkout -b feature/hft-options-support

# 开发完成后
git add .
git commit -m "feat: add options trading support"

# 推送并创建 PR
git push origin feature/hft-options-support
# 在 GitHub 创建 PR 合并到 develop
```

### 2. 修复 Bug

```bash
# 从 develop 创建 bugfix 分支
git checkout develop
git checkout -b bugfix/fix-slippage-calculation

# 修复完成后
git commit -m "fix: correct slippage calculation formula"
git push origin bugfix/fix-slippage-calculation
```

### 3. 发布版本

```bash
# 从 develop 创建 release 分支
git checkout develop
git checkout -b release/1.0.0

# 更新版本号、修复最后的问题
git commit -m "chore: bump version to 1.0.0"

# 合并到 main 和 develop
git checkout main
git merge release/1.0.0 --no-ff
git tag -a v1.0.0 -m "Release version 1.0.0"

git checkout develop
git merge release/1.0.0 --no-ff

# 删除 release 分支
git branch -d release/1.0.0
git push origin main develop --tags
```

### 4. 紧急修复

```bash
# 从 main 创建 hotfix 分支
git checkout main
git checkout -b hotfix/1.0.1

# 修复完成后
git commit -m "fix: critical circuit breaker issue"

# 合并到 main 和 develop
git checkout main
git merge hotfix/1.0.1 --no-ff
git tag -a v1.0.1 -m "Hotfix 1.0.1"

git checkout develop
git merge hotfix/1.0.1 --no-ff

# 删除 hotfix 分支
git branch -d hotfix/1.0.1
git push origin main develop --tags
```

## 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具相关

示例：
```
feat(options): add bull call spread strategy
fix(risk): correct max drawdown calculation
docs(readme): update installation instructions
test(executor): add unit tests for short selling
```

## CI/CD 集成

### GitHub Actions 工作流

触发条件：
- **develop**: 每次 push 运行测试
- **release/***: 运行测试 + 构建 Docker 镜像
- **main**: 运行测试 + 构建 + 部署到生产

### 必须通过的检查

1. 单元测试通过
2. 测试覆盖率 ≥ 80%
3. 代码风格检查
4. 安全漏洞扫描

## 版本号规则

遵循 [Semantic Versioning](https://semver.org/)：

- **主版本号**: 不兼容的 API 变更
- **次版本号**: 向后兼容的功能新增
- **修订号**: 向后兼容的问题修正

示例：v1.2.3
- 1: 主版本
- 2: 次版本
- 3: 修订号
