# AI 代码审查新项目接入教程

文档版本：v2.3  
编写日期：2026-07-09  
适用场景：任意 Git 项目从 0 接入本地 Git Hook 和 Merge Request AI 代码审查

这份文档默认你正在给一个新项目接入 AI 代码审查。它不假设项目里已经有 `.githooks/pre-commit`、`.githooks/post-commit`、`scripts/ai_review.py`、`ci/ai-review.sh`。

核心结论：

- Git 不会自动帮你做 AI 审查。
- GitLab / Codeup 也不会自动调用 AI。
- 你必须先把脚本放进项目，再让 Git Hook 或 CI 去执行这些脚本。
- 本地提交前靠 `.githooks/pre-commit`。
- 本地提交后靠 `.githooks/post-commit`。
- Merge Request 靠 CI job 执行 `ci/ai-review.sh`。
- 真正调用 DeepSeek / OpenAI 兼容接口的是 `scripts/ai_review.py`。

建议阅读路线：

- 第一次接入：按第 2 节、第 4 节、第 5 节、第 13 节、附录 B 操作。
- 只想理解原理：看第 1 节、第 3 节、第 7 节、第 8 节。
- 要接 Merge Request：重点看第 6 节、第 10 节、第 12 节。
- 要排错：先看第 11 节的排错表，再看具体问题。
- 要复制脚本：直接看附录 A，但复制后仍要回到第 4 节检查配置。

读完这份文档后，你应该能回答五个问题：

1. 本地提交和 Merge Request 为什么不是同一条触发链路。
2. `.githooks/pre-commit`、`.githooks/post-commit`、`ci/ai-review.sh`、`scripts/ai_review.py` 分别负责什么。
3. 哪些场景会阻断提交或流水线，哪些场景只生成报告。
4. AI 默认只能看到哪些 diff，看不到哪些上下文。
5. 新项目接入失败时，应该先检查 hook、环境变量、网络还是 CI。

## 目录

- [1. 新项目接入后长什么样](#1-新项目接入后长什么样)
- [2. 从 0 接入的最小步骤](#2-从-0-接入的最小步骤)
- [3. 四个脚本分别做什么](#3-四个脚本分别做什么)
- [4. 新项目必须检查哪些地方](#4-新项目必须检查哪些地方)
- [5. 本地 Git Hook 怎么启用](#5-本地-git-hook-怎么启用)
- [6. Merge Request 怎么接入](#6-merge-request-怎么接入)
- [7. 基础概念](#7-基础概念)
- [8. AI 审查范围](#8-ai-审查范围)
- [9. AI 重点看什么](#9-ai-重点看什么)
- [10. 环境变量](#10-环境变量)
- [11. 常见问题](#11-常见问题)
- [12. 安全要求](#12-安全要求)
- [13. 验收命令](#13-验收命令)
- [14. 后续增强](#14-后续增强)
- [附录 A：四个脚本的当前实际版本](#附录-a四个脚本的当前实际版本)
- [附录 B：从空 Git 项目完整演练](#附录-b从空-git-项目完整演练)

## 1. 新项目接入后长什么样

假设你的项目叫 `your-project`。接入完成后，项目里至少会多出这些文件：

```text
your-project/
  .githooks/
    pre-commit
    post-commit
  scripts/
    ai_review.py
  ci/
    ai-review.sh
```

这四个文件可以理解成“一个公共审查器 + 三个入口脚本”：

| 文件 | 角色 | 给谁用 |
|---|---|---|
| `scripts/ai_review.py` | 公共审查器，负责调用 AI 并生成 Markdown 报告 | 本地 hook 和 CI 都会调用它 |
| `.githooks/pre-commit` | 本地提交前入口 | 开发者执行 `git commit` 时自动触发 |
| `.githooks/post-commit` | 本地提交后入口 | commit 成功后自动触发 |
| `ci/ai-review.sh` | MR/CI 入口 | GitLab CI / Codeup Flow 执行 |

先用这张表判断应该看哪条链路：

| 场景 | 谁触发 | 执行入口 | 审查范围 | 是否适合阻断 | 报告位置 |
|---|---|---|---|---|---|
| 本地提交前发现明显问题 | 开发者执行 `git commit` | `.githooks/pre-commit` | 已经 `git add` 的暂存区 diff | 适合，发现 `BLOCKER` 可阻止 commit | `build/ai-review/pre-commit-review.md` |
| 本地提交后留痕 | commit 已经创建成功 | `.githooks/post-commit` | 最新 commit 的 diff | 不适合，只生成报告 | `build/ai-review/last-commit-review.md` |
| Merge Request 审查 | GitLab CI / Codeup Flow | `ci/ai-review.sh` | 目标分支到源分支的 MR diff | 第一阶段不阻断，稳定后可阻断 | `build/ai-review.md` |

这张表先记住一个原则：**本地 hook 只管开发者电脑上的提交，Merge Request 必须靠 CI。**

下面三张图分别说明三种触发场景。

第一张图是“提交前审查”。它发生在 `git commit` 真正创建提交之前，审查的是你已经 `git add` 到暂存区的代码。如果 AI 报告里出现 `BLOCKER`，本次 commit 会被拦住。

```text
本地 git commit（开发者执行提交命令）
      |
      v
.githooks/pre-commit（Git 自动执行提交前脚本）
      |
      v
build/ai-review/pre-commit.diff （生成暂存区 diff（只包含 git add 的改动））
      |
      v
scripts/ai_review.py（读取 diff，调用 AI）
      |
      v
AI Provider（DeepSeek / OpenAI 兼容接口，判断风险）
      |
      v
build/ai-review/pre-commit-review.md （生成提交前报告（Markdown 审查结果））
      |
      v
有 BLOCKER 时阻止 commit（脚本返回非 0，提交失败）
```

图里的关键点：

- `pre-commit` 不会审查所有本地文件，只审查暂存区 diff。
- `scripts/ai_review.py` 是真正调用 AI 的地方。
- `pre-commit-review.md` 是你排查问题时最先看的报告。
- 如果没有 `BLOCKER`，commit 会继续创建；如果有 `BLOCKER`，commit 会失败。

第二张图是“提交后留痕”。它发生在 commit 已经成功创建之后，审查的是刚刚生成的最新 commit。这个阶段不能阻止提交，也不会自动回滚提交，只是生成一份报告方便事后查看。

```text
本地 commit 成功后（提交已经创建）
      |
      v
.githooks/post-commit（Git 自动执行提交后脚本）
      |
      v
build/ai-review/last-commit.diff （生成最新 commit diff（审查 HEAD 这次提交））
      |
      v
scripts/ai_review.py（读取 diff，调用 AI）
      |
      v
build/ai-review/last-commit-review.md （生成提交后报告（只留痕，不阻断））
```

图里的关键点：

- `post-commit` 用 `git show HEAD` 生成最新提交的 diff。
- 它适合做留痕和提醒，不适合作为强制门禁。
- 即使 AI 调用失败，也不应该影响已经创建成功的 commit。
- 报告默认写到 `build/ai-review/last-commit-review.md`。

第三张图是“Merge Request 审查”。MR 不会执行开发者电脑上的 `.githooks`，所以必须让 GitLab CI 或 Codeup Flow 执行 `ci/ai-review.sh`。CI 会生成目标分支到源分支的 diff，再调用同一个 `scripts/ai_review.py`。

```text
Merge Request（源分支准备合并到目标分支）
      |
      v
GitLab CI / Codeup Flow（平台触发流水线）
      |
      v
ci/ai-review.sh（CI 入口脚本）
      |
      v
build/ai-review.diff （生成目标分支...源分支 diff（只看 MR 改动））
      |
      v
scripts/ai_review.py（读取 diff，调用 AI）
      |
      v
build/ai-review.md （生成 MR 审查报告（artifact 或 CI 日志查看））
```

图里的关键点：

- MR 审查靠 CI，不靠本地 Git Hook。
- `ci/ai-review.sh` 负责生成 MR diff。
- `scripts/ai_review.py` 仍然是公共 AI 审查器。
- 第一阶段建议只生成 `build/ai-review.md` 报告；团队确认误报率可接受后，再让 `BLOCKER` 阻断 MR。

## 2. 从 0 接入的最小步骤

### 2.1 进入你的新项目

下面所有命令都在你的新项目根目录执行：

```bash
cd /path/to/your-project
```

### 2.2 准备目录

```bash
mkdir -p .githooks scripts ci build/ai-review
```

### 2.3 放入脚本文件

先准备一份脚本模板。下面用 `/path/to/ai-review-template` 表示模板仓库或模板目录。

如果你已经有模板目录，可以复制这四个文件：

```bash
cp /path/to/ai-review-template/.githooks/pre-commit .githooks/pre-commit
cp /path/to/ai-review-template/.githooks/post-commit .githooks/post-commit
cp /path/to/ai-review-template/scripts/ai_review.py scripts/ai_review.py
cp /path/to/ai-review-template/ci/ai-review.sh ci/ai-review.sh
```

如果你的模板不在同一台机器上，就从模板仓库复制这四个文件的内容，放到新项目相同路径下。重点不是复制命令本身，而是新项目里必须出现同名文件。

### 2.4 设置可执行权限

```bash
chmod +x .githooks/pre-commit .githooks/post-commit ci/ai-review.sh scripts/ai_review.py
```

### 2.5 按新项目检查配置

复制模板后，不要直接当成最终版本。多数项目不需要改 `scripts/ai_review.py` 的默认 prompt，但至少要检查这些配置：

| 需要改的地方 | 在哪个文件里 | 为什么 |
|---|---|---|
| 审查哪些文件后缀 | `.githooks/pre-commit`、`.githooks/post-commit`、`ci/ai-review.sh` | 不同技术栈、monorepo 子目录和配置文件命名可能不同 |
| 排除哪些目录 | `.githooks/pre-commit`、`.githooks/post-commit`、`ci/ai-review.sh` | 构建产物、依赖目录、二进制文件不应该发给 AI |
| 项目背景和审查重点 | 环境变量，必要时才改 `scripts/ai_review.py` | 默认 prompt 已经通用，项目差异优先通过环境变量传入 |
| CI 默认目标分支 | `ci/ai-review.sh` 或 `.gitlab-ci.yml` | 有的项目主分支叫 `master`，有的叫 `main` |

### 2.6 启用本地 Hook

```bash
git config core.hooksPath .githooks
```

检查：

```bash
git config --get core.hooksPath
```

预期输出：

```text
.githooks
```

注意：这个配置是每个开发者本机自己的 Git 配置。脚本可以进仓库，但 `git config core.hooksPath .githooks` 需要每个人在自己的 clone 里执行一次。

### 2.7 配置 AI 环境变量

在执行 `git commit` 的同一个终端里配置：

```bash
export AI_BASE_URL="https://api.deepseek.com"
export AI_API_KEY="你的 key"
export AI_MODEL="deepseek-v4-pro"
```

这些变量只在当前 shell 生效。重新打开终端后需要重新设置，或者写到你自己的 shell 配置文件里。

### 2.8 提交一次代码测试

```bash
git add 你要提交的文件
git commit -m "test: verify ai review hook"
```

如果提交成功，检查报告：

```bash
cat build/ai-review/pre-commit-review.md
cat build/ai-review/last-commit-review.md
```

如果提交失败，并看到：

```text
Commit blocked by AI pre-commit review.
```

打开提交前报告：

```bash
cat build/ai-review/pre-commit-review.md
```

## 3. 四个脚本分别做什么

### 3.1 `.githooks/pre-commit`

运行时机：`git commit` 创建提交之前。

它做三件事：

1. 用 `git diff --cached` 生成暂存区 diff。
2. 调用 `scripts/ai_review.py`。
3. 如果 AI 报告里有 `BLOCKER`，返回非 0，阻止本次 commit。

它只审查已经 `git add` 的内容。工作区里没暂存的修改不会进入本次审查。

### 3.2 `.githooks/post-commit`

运行时机：commit 已经创建成功之后。

它做三件事：

1. 用 `git show HEAD` 生成最新 commit diff。
2. 调用 `scripts/ai_review.py`。
3. 生成 `build/ai-review/last-commit-review.md`。

它不能阻止已经完成的 commit，也不会自动回滚提交。

### 3.3 `ci/ai-review.sh`

运行时机：CI / Merge Request 流水线里。

它做三件事：

1. 计算目标分支和源分支之间的 diff。
2. 把 diff 写到 `build/ai-review.diff`。
3. 调用 `scripts/ai_review.py`，生成 `build/ai-review.md`。

MR 场景推荐审查：

```text
目标分支...源分支
```

这样更接近 MR 页面里展示的变更范围。

### 3.4 `scripts/ai_review.py`

运行时机：被 Git Hook 或 CI 脚本调用。

它做四件事：

1. 读取 diff。
2. 组装 prompt。
3. 调用 DeepSeek / OpenAI 兼容接口。
4. 输出 Markdown 审查报告。

它不应该写死某个业务项目的规则。新项目接入时，默认不用改 `build_messages`；如果模型需要更多业务背景，优先通过环境变量传入项目名称、技术栈和高风险模块。

## 4. 新项目必须检查哪些地方

### 4.1 改文件类型范围

当前脚本默认覆盖常见后端、前端、配置和文档文本文件，通常包含：

```text
*.java
*.kt
*.py
*.go
*.rs
*.c
*.cpp
*.cs
*.php
*.rb
*.swift
*.xml
*.sql
*.yml
*.yaml
*.properties
*.md
*.json
*.sh
Dockerfile
*.ts
*.tsx
*.js
*.jsx
*.vue
*.css
*.html
pom.xml
package.json
go.mod
Cargo.toml
pyproject.toml
frontend/package.json
```

如果新项目还有其他重要文件后缀、锁文件、子项目清单或代码生成配置，要把它们加入审查范围。

示例：

| 技术栈 | 可以增加 |
|---|---|
| Go | `*.go`、`go.mod`、`go.sum` |
| Python | `*.py`、`pyproject.toml`、`requirements.txt` |
| Node.js | `*.ts`、`*.tsx`、`package.json`、`pnpm-lock.yaml` |
| React Native | `*.ts`、`*.tsx`、`app.json`、`metro.config.js` |
| Rust | `*.rs`、`Cargo.toml`、`Cargo.lock` |

### 4.2 改排除目录

当前脚本默认排除常见依赖目录、构建产物、IDE 配置、本地密钥配置和二进制文件，例如：

```text
node_modules/**
.venv/**
vendor/**
target/**
build/**
dist/**
coverage/**
.idea/**
.vscode/**
.env
.env.*
*.pem
*.xlsx
*.xls
*.png
*.jpg
*.jpeg
*.pdf
```

新项目要按实际情况调整。

常见应该排除：

- 依赖目录，例如 `node_modules/**`、`.venv/**`、`vendor/**`。
- 构建产物，例如 `dist/**`、`build/**`、`target/**`、`coverage/**`。
- IDE 配置，例如 `.idea/**`、`.vscode/**`。
- 二进制或业务资料，例如图片、PDF、Excel、压缩包。
- 可能包含密钥的本地配置，例如 `.env`、`.env.*`、生产配置文件。

### 4.3 配置 AI 审查上下文

默认 `scripts/ai_review.py` 里的 prompt 已经是通用的新项目审查提示词。它会要求 AI 只审查 diff、优先发现生产事故、安全问题、编译失败、权限绕过和核心流程不可用等风险。

新项目第一次接入时，不建议先改脚本。更推荐通过环境变量传入项目背景：

```bash
export AI_REVIEW_PROJECT_NAME="your-project"
export AI_REVIEW_PROJECT_CONTEXT="后端 Go + PostgreSQL，前端 React，核心业务是订单、支付、库存。"
export AI_REVIEW_REVIEW_FOCUS="支付金额错误、库存扣减错误、权限绕过、SQL 注入、密钥泄露、编译失败。"
```

如果背景比较长，可以写到文件里：

```bash
export AI_REVIEW_PROJECT_CONTEXT_FILE="docs/ai-review-context.md"
```

`docs/ai-review-context.md` 可以写成这样：

```text
项目名称：order-service
主要技术栈：Go、PostgreSQL、React
核心业务流程：下单、支付、库存扣减、退款
最高风险模块：金额计算、库存并发、权限校验、SQL 拼接
不希望 AI 关注的内容：纯格式化、命名偏好、无风险的注释调整
希望 AI 优先发现的问题：编译失败、权限绕过、金额错误、库存扣减错误、密钥泄露
```

只有当团队确认通用 prompt 不适合时，才直接改 `scripts/ai_review.py` 里的 `build_messages`。

直接改脚本时，不要删掉这些约束：

```text
- 只审查 diff 中出现的变更。
- 不输出泛泛建议。
- 每个问题必须给出级别、文件、位置、风险说明和修改建议。
- 如果无法确认是问题，标记为 INFO 或不输出。
- 输出中文 Markdown。
```

不推荐把某个业务项目的固定描述直接写死到通用模板里。否则这四个文件复制到下一个项目时，AI 会带着上一个项目的背景审查代码。


### 4.4 改 CI 目标分支

如果主分支叫 `main`，CI 里建议用：

```yaml
TARGET_BRANCH: "origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME"
```

如果没有 MR 变量，可以临时默认：

```bash
TARGET_BRANCH="${TARGET_BRANCH:-origin/main}"
```

不要假设所有项目主分支都叫 `master`。

## 5. 本地 Git Hook 怎么启用

Git 默认会执行 `.git/hooks/` 下的本地脚本，但 `.git/hooks/` 不会进入代码仓库。

为了让 hook 脚本能被团队统一维护，本教程使用：

```bash
git config core.hooksPath .githooks
```

它的含义是：告诉 Git 以后从项目里的 `.githooks/` 目录找 hook。

### 5.1 启用

```bash
cd /path/to/your-project
git config core.hooksPath .githooks
```

### 5.2 检查

```bash
git config --get core.hooksPath
```

预期：

```text
.githooks
```

### 5.3 测试 pre-commit

先暂存一些文件：

```bash
git add path/to/file
```

手动运行：

```bash
.githooks/pre-commit
```

预期：

- 没有可审查 diff 时返回 0。
- 有 diff 时生成 `build/ai-review/pre-commit.diff`。
- AI 配置正确时生成 `build/ai-review/pre-commit-review.md`。
- AI 报告有 `BLOCKER` 时返回非 0。

### 5.4 测试 post-commit

```bash
.githooks/post-commit
cat build/ai-review/last-commit-review.md
```

## 6. Merge Request 怎么接入

本地 `.githooks` 不会在 GitLab / Codeup 的 MR 页面自动执行。MR 审查必须靠 CI。

### 6.1 推荐落地阶段

| 阶段 | 推荐做法 | 原因 |
|---|---|---|
| 第一阶段 | CI 只生成 AI 报告，不阻断 MR | 先观察误报率 |
| 第二阶段 | 有 `BLOCKER` 时让 CI 失败 | 形成质量门禁 |
| 第三阶段 | 把报告自动评论到 MR | reviewer 不用翻 artifact |

### 6.2 GitLab CI 示例

在新项目根目录新增 `.gitlab-ci.yml`：

```yaml
stages:
  - test

ai_review:
  stage: test
  image: python:3.11
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
  variables:
    TARGET_BRANCH: "origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME"
    SOURCE_REF: "HEAD"
    AI_REVIEW_OUTPUT: "build/ai-review.md"
    AI_REVIEW_FAIL_ON_BLOCKER: "false"
  before_script:
    - git --version
    - python3 --version
    - git fetch origin "$CI_MERGE_REQUEST_TARGET_BRANCH_NAME"
  script:
    - bash ci/ai-review.sh
  artifacts:
    when: always
    paths:
      - build/ai-review.diff
      - build/ai-review.md
      - build/ai-review.console.md
```

第一阶段建议：

```text
AI_REVIEW_FAIL_ON_BLOCKER=false
```

等团队确认误报率可以接受，再改成：

```text
AI_REVIEW_FAIL_ON_BLOCKER=true
```

### 6.3 CI/CD Variables

在 GitLab / Codeup 的 CI 变量里配置：

```text
AI_BASE_URL
AI_API_KEY
AI_MODEL
```

不要把 API Key 写进 `.gitlab-ci.yml`。

### 6.4 CI Runner 需要什么

Runner 至少需要：

```text
bash
git
python3
网络能访问 AI_BASE_URL
```

如果是 Docker Runner，用 `python:3.11` 镜像通常已经有 Python，但仍要确认镜像里有 `git`。如果没有，可以换镜像或在 `before_script` 里安装。

## 7. 基础概念

### 7.1 Git Hook 是什么

Git Hook 是 Git 在某些动作前后自动执行的脚本。

常见例子：

- `pre-commit`：提交创建前执行。
- `post-commit`：提交创建后执行。
- `pre-push`：推送到远端前执行。

本教程默认只接入：

- `.githooks/pre-commit`
- `.githooks/post-commit`

### 7.2 常见 Git Hook 节点

| Hook 节点 | 运行时机 | 常见用途 | 本教程是否默认接入 |
|---|---|---|---|
| `pre-commit` | `git commit` 创建提交之前 | 格式检查、测试、lint、AI 审查；返回非 0 会阻止提交 | 是 |
| `prepare-commit-msg` | Git 生成提交信息模板之后、打开编辑器之前 | 自动填充提交信息，例如补 issue ID、分支名 | 否 |
| `commit-msg` | 用户填写提交信息之后、提交真正创建之前 | 校验 commit message 格式，例如 Conventional Commits | 否 |
| `post-commit` | commit 创建成功之后 | 生成提交报告、通知、记录日志；不能阻止已经完成的提交 | 是 |
| `pre-rebase` | 执行 `git rebase` 之前 | 防止错误 rebase 受保护分支 | 否 |
| `post-checkout` | 执行 `git checkout` 或切换分支之后 | 自动安装依赖、提示环境变化 | 否 |
| `post-merge` | 执行 `git merge` 成功之后 | merge 后自动安装依赖、刷新生成文件 | 否 |
| `pre-push` | 执行 `git push` 之前 | push 前跑测试、AI 审查、阻止明显有问题的代码推到远端 | 否，可扩展 |
| `pre-receive` | 远端仓库接收 push 之前，在服务端运行 | 服务端统一阻断不合规提交、密钥泄露、分支保护 | 不在本地配置，通常由 GitLab/Codeup 管理 |
| `update` | 远端仓库更新某个 ref 之前，在服务端运行 | 针对单个分支或 tag 做权限和规则校验 | 不在本地配置 |
| `post-receive` | 远端仓库接收 push 成功之后，在服务端运行 | 触发部署、通知、流水线 | 不在本地配置，平台通常已有机制 |

### 7.3 Merge Request 是什么

Merge Request，简称 MR，是把一个功能分支合并到目标分支前的审查流程。

典型流程：

```text
开发者 push feature 分支
  -> 创建或更新 Merge Request
  -> GitLab / Codeup 触发 CI Pipeline
  -> CI Job 拉取仓库代码并执行脚本
  -> 生成 AI Review 报告
```

### 7.4 CI Job 是什么

CI Job 是 GitLab Runner / Codeup Flow 执行的一段命令。

Runner 可以是：

- Docker Runner：使用指定镜像，例如 `python:3.11`。
- Shell Runner：直接在一台服务器上执行命令。

只要 CI 环境有 `bash`、`git`、`python3`，并且能访问 AI 接口，就可以执行：

```bash
bash ci/ai-review.sh
```

## 8. AI 审查范围

AI 默认不扫描整个仓库，而是审查 diff。

不同场景下 diff 来源不同：

| 场景 | diff 来源 |
|---|---|
| 本地 `pre-commit` | `git diff --cached`，也就是暂存区 |
| 本地 `post-commit` | `git show HEAD`，也就是最新提交 |
| MR CI | `git diff 目标分支...源分支` |

它主要能看到：

- 本次修改的行。
- 修改附近的上下文。
- 文件路径和 diff 片段。

它默认看不到：

- 没有进入 diff 的旧代码。
- 没有被脚本包含的文件类型。
- 被排除目录里的文件。
- 数据库真实数据。
- 运行时日志，除非你额外提供。

所以 AI Review 适合发现“本次改动直接引入的问题”，不适合作为唯一质量保障。

更准确的分工如下：

| 手段 | 主要发现什么 | 不能替代什么 |
|---|---|---|
| AI Review | diff 中明显的逻辑错误、安全风险、权限绕过、必现异常、配置泄露 | 编译器、自动化测试、完整业务验收 |
| 编译 / Build | 语法错误、类型错误、依赖缺失、打包失败 | 业务逻辑正确性 |
| 单元测试 / 集成测试 | 已知业务规则、接口契约、回归问题 | 没有写进测试用例的未知风险 |
| 静态扫描 | 明确规则类问题，例如密钥、依赖漏洞、危险 API | 复杂业务语义判断 |
| 人工 Review | 架构合理性、长期维护性、产品语义、跨模块影响 | 高频重复检查和机械风险扫描 |

所以推荐组合是：**AI Review 负责提前提醒，测试和 CI 负责硬验证，人工 Review 负责最终判断。**

## 9. AI 重点看什么

默认 prompt 已经覆盖通用高风险问题。新项目如果想让 AI 更贴合业务，不要优先改脚本，先通过 `AI_REVIEW_PROJECT_CONTEXT` 或 `AI_REVIEW_REVIEW_FOCUS` 补充审查重点。

可以把下面这些内容写进 `AI_REVIEW_REVIEW_FOCUS` 或 `docs/ai-review-context.md`。

后端重点：

1. 编译失败、必现异常、空指针、除以 0。
2. 登录、鉴权、权限边界是否被绕过。
3. 数据写入、事务、幂等、并发是否有明显问题。
4. SQL 注入、分页错误、排序错误、索引风险。
5. API Key、Token、服务器路径、生产配置是否泄露。
6. 核心业务金额、库存、状态流转、审批流是否被改坏。

前端重点：

1. 路由守卫和权限入口是否绕过。
2. 表单保存、弹窗确认、批量选择是否有状态错误。
3. API 错误是否有明确提示。
4. 移动端和桌面端入口是否行为一致。
5. 是否误提交调试代码、测试地址、mock 数据。

不建议让 AI 重点关注：

- 纯格式化风格。
- 无实际风险的命名偏好。
- 和本次 diff 无关的大范围重构建议。

## 10. 环境变量

| 变量 | 必填 | 示例 | 说明 |
|---|---:|---|---|
| `AI_BASE_URL` | 是 | `https://api.deepseek.com` | OpenAI 兼容接口地址 |
| `AI_API_KEY` | 是 | `sk-xxx` | 模型 API Key |
| `AI_MODEL` | 是 | `deepseek-v4-pro` | 模型名称 |
| `AI_REVIEW_OUTPUT` | 否 | `build/ai-review.md` | 报告输出路径 |
| `AI_REVIEW_MAX_CHARS` | 否 | `120000` | 发送给模型的最大 diff 字符数 |
| `AI_REVIEW_TIMEOUT` | 否 | `120` | 模型请求超时时间，单位秒 |
| `AI_REVIEW_RETRY_WITHOUT_PROXY` | 否 | `true` | 代理失败时自动直连重试 |
| `AI_REVIEW_DISABLE_PROXY` | 否 | `false` | 完全跳过当前代理 |
| `AI_REVIEW_CA_FILE` | 否 | `/path/to/ca.pem` | 自定义 CA 证书文件 |
| `AI_REVIEW_FAIL_ON_BLOCKER` | 否 | `false` | 有 BLOCKER 时退出非 0 |
| `AI_REVIEW_FAIL_ON_ERROR` | 否 | `false` | AI 配置缺失或请求失败时退出非 0 |
| `AI_REVIEW_LANGUAGE` | 否 | `zh-CN` | 输出语言 |
| `AI_REVIEW_PROJECT_NAME` | 否 | `order-service` | 项目名称，默认空；不设置时不会把项目名写进提示词 |
| `AI_REVIEW_PROJECT_CONTEXT` | 否 | `后端 Go + PostgreSQL...` | 直接传入项目背景 |
| `AI_REVIEW_PROJECT_CONTEXT_FILE` | 否 | `docs/ai-review-context.md` | 从文件读取项目背景，适合长说明 |
| `AI_REVIEW_REVIEW_FOCUS` | 否 | `支付金额、权限、SQL 注入` | 当前项目希望 AI 优先关注的风险点 |

DeepSeek 示例：

```bash
export AI_BASE_URL="https://api.deepseek.com"
export AI_API_KEY="${DEEPSEEK_API_KEY}"
export AI_MODEL="deepseek-v4-pro"
```

OpenAI 示例：

```bash
export AI_BASE_URL="https://api.openai.com/v1"
export AI_API_KEY="${OPENAI_API_KEY}"
export AI_MODEL="按账号可用模型配置"
```

## 11. 常见问题

先用这张表定位问题：

| 现象 | 最常见原因 | 先执行什么命令 | 解决方向 |
|---|---|---|---|
| `git commit` 时完全没看到 AI 审查 | 没启用 `core.hooksPath`，或 hook 文件没有执行权限 | `git config --get core.hooksPath`；`ls -l .githooks/pre-commit` | 设置 `git config core.hooksPath .githooks`，并执行 `chmod +x .githooks/pre-commit .githooks/post-commit` |
| commit 成功了，但没有报告文件 | 没有暂存区 diff、文件类型没命中、报告目录没生成 | `git status --short`；`ls -l build/ai-review` | 先 `git add`，再确认脚本里的文件类型范围包含本次修改文件 |
| pre-commit 阻止提交 | AI 报告存在 `BLOCKER`，或 AI 配置/请求失败且配置为失败阻断 | `cat build/ai-review/pre-commit-review.md` | 如果是代码问题就修复；如果是 AI 配置问题就补环境变量或网络配置 |
| 报告提示缺少 `AI_BASE_URL`、`AI_API_KEY`、`AI_MODEL` | 当前终端没有配置模型环境变量 | `echo "$AI_BASE_URL"`；`test -n "$AI_API_KEY" && echo ok` | 在同一个终端 export 变量，或放到本机 shell 配置 / CI Variables |
| 出现 `Connection reset by peer` | 本机代理或公司网络拦截模型请求 | `AI_REVIEW_DISABLE_PROXY=true .githooks/post-commit` | 关闭代理重试，或配置公司允许的代理 / CA |
| MR 里没有 AI Review | MR 不会执行本地 hook，CI 没配置或没触发 | 查看 Pipeline 是否有 `ai_review` job | 增加 `.gitlab-ci.yml` 或 Codeup Flow 任务，执行 `bash ci/ai-review.sh` |
| CI 提示没有 Python | Runner 镜像或机器没有 `python3` | `python3 --version` | Docker Runner 使用 `python:3.11`，Shell Runner 安装 Python |
| CI 有报告但 MR 没评论 | 当前方案只生成 artifact，没有调用平台评论 API | 查看 `build/ai-review.md` artifact | 后续增加 GitLab / Codeup API，把报告写成 MR 评论 |

### 11.1 我执行了 `git config core.hooksPath .githooks`，为什么没有 AI 审查

`git config core.hooksPath .githooks` 只是告诉 Git 去 `.githooks` 目录找脚本。

你还需要确认：

```bash
ls -l .githooks/pre-commit .githooks/post-commit
```

如果文件不存在，说明新项目还没有放入 hook 脚本。

如果文件存在但没有执行权限：

```bash
chmod +x .githooks/pre-commit .githooks/post-commit
```

### 11.2 我 commit 了，但没看到 AI 报告

检查 hook 路径：

```bash
git config --get core.hooksPath
```

必须输出：

```text
.githooks
```

检查环境变量：

```bash
echo "$AI_BASE_URL"
echo "$AI_MODEL"
test -n "$AI_API_KEY" && echo ok
```

检查报告目录：

```bash
ls -l build/ai-review
```

### 11.3 pre-commit 阻止了提交，怎么办

打开报告：

```bash
cat build/ai-review/pre-commit-review.md
```

如果是代码问题，修代码后重新：

```bash
git add 你修改的文件
git commit -m "你的提交说明"
```

如果是缺少 AI 配置，设置：

```bash
export AI_BASE_URL="https://api.deepseek.com"
export AI_API_KEY="你的 key"
export AI_MODEL="deepseek-v4-pro"
```

### 11.4 Connection reset by peer

本地代理访问模型网关失败时常见。

脚本默认会自动直连重试。如果还失败，可以显式关闭代理：

```bash
AI_REVIEW_DISABLE_PROXY=true .githooks/post-commit
```

### 11.5 GitLab CI 里没有 Python

如果是 Docker Runner，用 Python 镜像：

```yaml
image: python:3.11
```

如果是 Shell Runner，需要在 runner 机器安装 Python。

同时确认有 `git`：

```yaml
script:
  - git --version
  - python3 --version
```

### 11.6 AI 会不会检查未修改代码

默认不会完整扫描全仓。

它主要看到：

- 你修改的行。
- 修改附近的上下文。
- MR 或 commit 的 diff。

所以它能发现很多直接由本次改动引入的问题，但不保证发现所有跨模块连锁影响。

跨模块可靠性仍然要靠：

- 后端测试。
- 前端 build / lint。
- 静态扫描。
- 人工 Review。

## 12. 安全要求

必须遵守：

- `AI_API_KEY` 只能放本机环境变量或 CI/CD Variables。
- 禁止把 API Key 写进仓库。
- 禁止在日志里打印完整环境变量。
- 不上传构建产物、依赖目录、Excel、图片、PDF、生产配置和密钥文件。
- 外部模型调用要符合公司代码和数据出境要求。
- 如果项目包含敏感业务代码，先确认公司是否允许发送 diff 到外部模型。

## 13. 验收命令

### 13.1 脚本语法检查

```bash
python3 -m py_compile scripts/ai_review.py
bash -n ci/ai-review.sh
bash -n .githooks/pre-commit
bash -n .githooks/post-commit
```

### 13.2 本地 hook 配置检查

```bash
git config --get core.hooksPath
ls -l .githooks/pre-commit .githooks/post-commit
```

### 13.3 手动运行 pre-commit

```bash
.githooks/pre-commit
```

预期：

- 有暂存区 diff 时，生成 `build/ai-review/pre-commit-review.md`。
- 有 `BLOCKER` 时返回非 0。
- 无暂存区 diff 时直接返回 0。

### 13.4 手动运行 post-commit

```bash
.githooks/post-commit
cat build/ai-review/last-commit-review.md
```

### 13.5 CI 验收

在 MR Pipeline 里确认：

```text
build/ai-review.diff
build/ai-review.md
build/ai-review.console.md
```

至少有 `build/ai-review.md` 能作为 artifact 下载。

## 14. 后续增强

1. 新增 `.githooks/pre-push`，在 push 前再审查一次。
2. 将 AI 报告自动评论到 GitLab / Codeup MR。
3. 按文件分片审查，避免大 diff 被截断。
4. 给 AI 额外提供相关文件上下文，例如 Controller 改动时附带 Service、Mapper、测试。
5. 把项目架构文档、安全文档作为固定审查上下文。
6. 按技术栈或目录选择不同模型，核心业务用强模型，样式改动用低成本模型。

## 附录 A：四个脚本的当前实际版本

这一节不是伪代码，也不是简化模板，而是当前仓库实际使用的四个脚本完整内容。

新项目接入时可以直接复制这四个文件。复制后通常只需要改第 4 节提到的项目配置，例如文件类型范围、排除目录、AI 环境变量、目标分支和项目背景。

维护规则：以后只要修改 `.githooks/pre-commit`、`.githooks/post-commit`、`ci/ai-review.sh` 或 `scripts/ai_review.py`，就要同步更新本附录，否则读者按文档复制时会拿到旧版本。

### A.1 `.githooks/pre-commit`

用途：提交前审查暂存区 diff，有 `BLOCKER` 或 AI 调用失败时阻止提交。

````bash
#!/usr/bin/env bash
set -euo pipefail

# pre-commit 会在 commit 真正创建之前执行。
# 这里用于审查“暂存区”的代码，也就是即将进入本次提交的内容。
mkdir -p build/ai-review

DIFF_FILE="build/ai-review/pre-commit.diff"
REPORT_FILE="build/ai-review/pre-commit-review.md"

# 生成暂存区 diff。
# 注意这里使用 --cached，只审查已经 git add 的内容；工作区未暂存的修改不会进入本次审查。
# 只审查源码、配置、文档等文本文件，避免把构建产物和二进制文件发给 AI。
git diff \
  --cached \
  --stat \
  --patch \
  --find-renames \
  --find-copies \
  --unified=80 \
  -- \
  '*.java' \
  '*.kt' \
  '*.kts' \
  '*.scala' \
  '*.groovy' \
  '*.py' \
  '*.go' \
  '*.rs' \
  '*.c' \
  '*.h' \
  '*.cpp' \
  '*.hpp' \
  '*.cs' \
  '*.php' \
  '*.rb' \
  '*.swift' \
  '*.xml' \
  '*.sql' \
  '*.yml' \
  '*.yaml' \
  '*.toml' \
  '*.ini' \
  '*.properties' \
  '*.md' \
  '*.json' \
  '*.ts' \
  '*.tsx' \
  '*.js' \
  '*.jsx' \
  '*.vue' \
  '*.svelte' \
  '*.css' \
  '*.scss' \
  '*.less' \
  '*.html' \
  '*.sh' \
  '*.bash' \
  '*.zsh' \
  '*.ps1' \
  'pom.xml' \
  '**/pom.xml' \
  'build.gradle' \
  '**/build.gradle' \
  'settings.gradle' \
  '**/settings.gradle' \
  'package.json' \
  '**/package.json' \
  'go.mod' \
  '**/go.mod' \
  'go.sum' \
  '**/go.sum' \
  'Cargo.toml' \
  '**/Cargo.toml' \
  'Cargo.lock' \
  '**/Cargo.lock' \
  'pyproject.toml' \
  '**/pyproject.toml' \
  'requirements*.txt' \
  '**/requirements*.txt' \
  'Dockerfile' \
  '**/Dockerfile' \
  'docker-compose*.yml' \
  '**/docker-compose*.yml' \
  ':(exclude)target/**' \
  ':(exclude)build/**' \
  ':(exclude)dist/**' \
  ':(exclude)out/**' \
  ':(exclude)coverage/**' \
  ':(exclude)node_modules/**' \
  ':(exclude)**/node_modules/**' \
  ':(exclude).venv/**' \
  ':(exclude)venv/**' \
  ':(exclude)vendor/**' \
  ':(exclude).next/**' \
  ':(exclude).nuxt/**' \
  ':(exclude).gradle/**' \
  ':(exclude).idea/**' \
  ':(exclude).vscode/**' \
  ':(exclude).env' \
  ':(exclude).env.*' \
  ':(exclude)**/.env' \
  ':(exclude)**/.env.*' \
  ':(exclude)**/*.pem' \
  ':(exclude)**/*.key' \
  ':(exclude)**/*.p12' \
  ':(exclude)**/*.pfx' \
  ':(exclude)**/*.png' \
  ':(exclude)**/*.jpg' \
  ':(exclude)**/*.jpeg' \
  ':(exclude)**/*.gif' \
  ':(exclude)**/*.svg' \
  ':(exclude)**/*.pdf' \
  ':(exclude)**/*.xlsx' \
  ':(exclude)**/*.xls' \
  ':(exclude)**/*.docx' \
  ':(exclude)**/*.pptx' \
  ':(exclude)**/*.zip' \
  ':(exclude)**/*.jar' \
  ':(exclude)**/*.war' \
  ':(exclude)**/*.class' \
  > "${DIFF_FILE}"

# 如果暂存区没有需要审查的文件，直接放行本次提交。
if [ ! -s "${DIFF_FILE}" ]; then
  exit 0
fi

# 临时关闭 set -e，目的是拿到 ai_review.py 的退出码。
# 如果 AI 发现 BLOCKER、AI 配置缺失或请求失败，脚本会返回非 0。
set +e
AI_REVIEW_OUTPUT="${REPORT_FILE}" \
AI_REVIEW_FAIL_ON_BLOCKER=true \
AI_REVIEW_FAIL_ON_ERROR=true \
python3 scripts/ai_review.py "${DIFF_FILE}"
status=$?
set -e

echo "AI pre-commit review report: ${REPORT_FILE}"

# 非 0 表示这次提交不能继续。
# 具体原因看 build/ai-review/pre-commit-review.md。
if [ "${status}" -ne 0 ]; then
  echo "Commit blocked by AI pre-commit review." >&2
  exit "${status}"
fi
````

### A.2 `.githooks/post-commit`

用途：提交完成后审查刚生成的 commit，默认只生成报告，不阻断提交。

````bash
#!/usr/bin/env bash
set -euo pipefail

# post-commit 会在 commit 已经创建成功后执行。
# 这个阶段已经不能阻止本次提交，所以这里只生成 AI 审查报告，供开发者事后查看。
mkdir -p build/ai-review

# 把“刚刚提交的 commit”转换成一个 diff 文件。
# scripts/ai_review.py 只接收 diff 文本，不直接读取 Git 历史。
DIFF_FILE="build/ai-review/last-commit.diff"

# 只把适合文本审查的源码、配置和文档发给 AI。
# 二进制文件、构建产物、IDE 配置会在 pathspec 里 exclude 掉，避免浪费 token。
git show \
  --format=medium \
  --stat \
  --patch \
  --find-renames \
  --find-copies \
  --unified=80 \
  HEAD \
  -- \
  '*.java' \
  '*.kt' \
  '*.kts' \
  '*.scala' \
  '*.groovy' \
  '*.py' \
  '*.go' \
  '*.rs' \
  '*.c' \
  '*.h' \
  '*.cpp' \
  '*.hpp' \
  '*.cs' \
  '*.php' \
  '*.rb' \
  '*.swift' \
  '*.xml' \
  '*.sql' \
  '*.yml' \
  '*.yaml' \
  '*.toml' \
  '*.ini' \
  '*.properties' \
  '*.md' \
  '*.json' \
  '*.ts' \
  '*.tsx' \
  '*.js' \
  '*.jsx' \
  '*.vue' \
  '*.svelte' \
  '*.css' \
  '*.scss' \
  '*.less' \
  '*.html' \
  '*.sh' \
  '*.bash' \
  '*.zsh' \
  '*.ps1' \
  'pom.xml' \
  '**/pom.xml' \
  'build.gradle' \
  '**/build.gradle' \
  'settings.gradle' \
  '**/settings.gradle' \
  'package.json' \
  '**/package.json' \
  'go.mod' \
  '**/go.mod' \
  'go.sum' \
  '**/go.sum' \
  'Cargo.toml' \
  '**/Cargo.toml' \
  'Cargo.lock' \
  '**/Cargo.lock' \
  'pyproject.toml' \
  '**/pyproject.toml' \
  'requirements*.txt' \
  '**/requirements*.txt' \
  'Dockerfile' \
  '**/Dockerfile' \
  'docker-compose*.yml' \
  '**/docker-compose*.yml' \
  ':(exclude)target/**' \
  ':(exclude)build/**' \
  ':(exclude)dist/**' \
  ':(exclude)out/**' \
  ':(exclude)coverage/**' \
  ':(exclude)node_modules/**' \
  ':(exclude)**/node_modules/**' \
  ':(exclude).venv/**' \
  ':(exclude)venv/**' \
  ':(exclude)vendor/**' \
  ':(exclude).next/**' \
  ':(exclude).nuxt/**' \
  ':(exclude).gradle/**' \
  ':(exclude).idea/**' \
  ':(exclude).vscode/**' \
  ':(exclude).env' \
  ':(exclude).env.*' \
  ':(exclude)**/.env' \
  ':(exclude)**/.env.*' \
  ':(exclude)**/*.pem' \
  ':(exclude)**/*.key' \
  ':(exclude)**/*.p12' \
  ':(exclude)**/*.pfx' \
  ':(exclude)**/*.png' \
  ':(exclude)**/*.jpg' \
  ':(exclude)**/*.jpeg' \
  ':(exclude)**/*.gif' \
  ':(exclude)**/*.svg' \
  ':(exclude)**/*.pdf' \
  ':(exclude)**/*.xlsx' \
  ':(exclude)**/*.xls' \
  ':(exclude)**/*.docx' \
  ':(exclude)**/*.pptx' \
  ':(exclude)**/*.zip' \
  ':(exclude)**/*.jar' \
  ':(exclude)**/*.war' \
  ':(exclude)**/*.class' \
  > "${DIFF_FILE}"

# 如果这次 commit 没有命中上面的文件类型，就不用调用 AI。
if [ ! -s "${DIFF_FILE}" ]; then
  exit 0
fi

# post-commit 只做提醒，不阻塞。
# AI_REVIEW_FAIL_ON_BLOCKER=false 表示即使 AI 报 BLOCKER，也只写报告。
# 末尾的 `|| true` 保证网络失败、Key 缺失等问题不会影响已经完成的 commit。
AI_REVIEW_OUTPUT="build/ai-review/last-commit-review.md" \
AI_REVIEW_FAIL_ON_BLOCKER=false \
python3 scripts/ai_review.py "${DIFF_FILE}" || true

echo "AI review report: build/ai-review/last-commit-review.md"
````

### A.3 `ci/ai-review.sh`

用途：给 CI / MR Pipeline 使用，生成目标分支到源分支的 diff，再调用公共 AI 审查器。

````bash
#!/usr/bin/env bash
set -euo pipefail

# 这个脚本给 CI / Merge Request 使用，不依赖开发者本机的 Git Hook。
# CI 只需要执行 `bash ci/ai-review.sh`，它会生成 MR diff 并调用 scripts/ai_review.py。
mkdir -p build

# 目标分支和源分支可以由 CI 变量传入。
# GitLab MR 常见写法：
#   TARGET_BRANCH=origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME
#   SOURCE_REF=HEAD
TARGET_BRANCH="${TARGET_BRANCH:-origin/main}"
SOURCE_REF="${SOURCE_REF:-HEAD}"
DIFF_FILE="${AI_REVIEW_DIFF_FILE:-build/ai-review.diff}"

# CI 拉到的仓库可能没有最新目标分支引用，所以先尝试 fetch。
# 这里受 set -e 控制：如果 fetch 失败，说明 CI 的远端权限或网络需要先修好。
if git remote get-url origin >/dev/null 2>&1; then
  git fetch origin --prune
fi

# 优先审查“目标分支...源分支”的 MR diff。
# 三点语法会从两个分支共同祖先开始比较，更贴近 MR 页面展示的改动。
if git rev-parse --verify "${TARGET_BRANCH}^{commit}" >/dev/null 2>&1; then
  DIFF_RANGE="${TARGET_BRANCH}...${SOURCE_REF}"
elif git rev-parse --verify "HEAD~1^{commit}" >/dev/null 2>&1; then
  # 如果目标分支不存在，退化为审查最近一个 commit，方便普通分支流水线也能运行。
  echo "TARGET_BRANCH ${TARGET_BRANCH} not found, fallback to HEAD~1...HEAD" >&2
  DIFF_RANGE="HEAD~1...HEAD"
else
  # 仓库只有一个提交时没有 HEAD~1，就退化为工作区 diff。
  echo "No target branch or previous commit found; using working tree diff." >&2
  DIFF_RANGE=""
fi

# Bash 数组用于安全地处理“有 diff range”和“无 diff range”两种情况。
if [ -n "${DIFF_RANGE}" ]; then
  DIFF_ARGS=("${DIFF_RANGE}")
else
  DIFF_ARGS=()
fi

# 只审查文本类文件；构建产物、IDE 文件和常见二进制文件排除。
git diff \
  --unified=80 \
  --find-renames \
  --find-copies \
  "${DIFF_ARGS[@]}" \
  -- \
  '*.java' \
  '*.kt' \
  '*.kts' \
  '*.scala' \
  '*.groovy' \
  '*.py' \
  '*.go' \
  '*.rs' \
  '*.c' \
  '*.h' \
  '*.cpp' \
  '*.hpp' \
  '*.cs' \
  '*.php' \
  '*.rb' \
  '*.swift' \
  '*.xml' \
  '*.sql' \
  '*.yml' \
  '*.yaml' \
  '*.toml' \
  '*.ini' \
  '*.properties' \
  '*.md' \
  '*.json' \
  '*.ts' \
  '*.tsx' \
  '*.js' \
  '*.jsx' \
  '*.vue' \
  '*.svelte' \
  '*.css' \
  '*.scss' \
  '*.less' \
  '*.html' \
  '*.sh' \
  '*.bash' \
  '*.zsh' \
  '*.ps1' \
  'pom.xml' \
  '**/pom.xml' \
  'build.gradle' \
  '**/build.gradle' \
  'settings.gradle' \
  '**/settings.gradle' \
  'package.json' \
  '**/package.json' \
  'go.mod' \
  '**/go.mod' \
  'go.sum' \
  '**/go.sum' \
  'Cargo.toml' \
  '**/Cargo.toml' \
  'Cargo.lock' \
  '**/Cargo.lock' \
  'pyproject.toml' \
  '**/pyproject.toml' \
  'requirements*.txt' \
  '**/requirements*.txt' \
  'Dockerfile' \
  '**/Dockerfile' \
  'docker-compose*.yml' \
  '**/docker-compose*.yml' \
  ':(exclude)target/**' \
  ':(exclude)build/**' \
  ':(exclude)dist/**' \
  ':(exclude)out/**' \
  ':(exclude)coverage/**' \
  ':(exclude)node_modules/**' \
  ':(exclude)**/node_modules/**' \
  ':(exclude).venv/**' \
  ':(exclude)venv/**' \
  ':(exclude)vendor/**' \
  ':(exclude).next/**' \
  ':(exclude).nuxt/**' \
  ':(exclude).gradle/**' \
  ':(exclude).idea/**' \
  ':(exclude).vscode/**' \
  ':(exclude).env' \
  ':(exclude).env.*' \
  ':(exclude)**/.env' \
  ':(exclude)**/.env.*' \
  ':(exclude)**/*.pem' \
  ':(exclude)**/*.key' \
  ':(exclude)**/*.p12' \
  ':(exclude)**/*.pfx' \
  ':(exclude)**/*.xlsx' \
  ':(exclude)**/*.xls' \
  ':(exclude)**/*.png' \
  ':(exclude)**/*.jpg' \
  ':(exclude)**/*.jpeg' \
  ':(exclude)**/*.gif' \
  ':(exclude)**/*.svg' \
  ':(exclude)**/*.pdf' \
  ':(exclude)**/*.docx' \
  ':(exclude)**/*.pptx' \
  ':(exclude)**/*.zip' \
  ':(exclude)**/*.jar' \
  ':(exclude)**/*.war' \
  ':(exclude)**/*.class' \
  > "${DIFF_FILE}"

# 没有命中文件时也生成一份报告，避免 CI 页面看起来像“什么都没执行”。
if [ ! -s "${DIFF_FILE}" ]; then
  {
    echo "# AI Code Review"
    echo
    echo "本次变更没有命中需要 AI 审查的文件。"
  } | tee build/ai-review.md
  exit 0
fi

# ai_review.py 会把完整报告写到 AI_REVIEW_OUTPUT 指定的位置。
# tee 额外保存一份控制台输出，方便在 CI 日志里直接查看。
python3 scripts/ai_review.py "${DIFF_FILE}" | tee build/ai-review.console.md
````

### A.4 `scripts/ai_review.py`

用途：公共 AI 审查器。它读取 diff，调用 OpenAI 兼容接口，输出 Markdown 报告，并根据配置决定是否用退出码阻断流程。

````python
#!/usr/bin/env python3
"""调用 DeepSeek / OpenAI 兼容接口审查 git diff。

脚本只做四件事：
1. 读取 Git Hook 或 CI 生成的 diff。
2. 组装审查提示词并调用 AI 模型。
3. 把模型返回的 Markdown 报告写入文件。
4. 按配置决定是否因为 BLOCKER 或 AI 调用失败返回非 0。

注意：这里没有本地正则规则去判断源码 bug。
`has_blocker` 只解析 AI 返回报告里的 BLOCKER 段，用于决定是否阻塞提交或 CI。
"""

import http.client
import json
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.error
import urllib.request


DEFAULT_MAX_CHARS = 120000
DEFAULT_TIMEOUT_SECONDS = 120


class AiHttpError(Exception):
    """把 http.client 的非 2xx 响应包装成统一异常，方便上层生成失败报告。"""

    def __init__(self, status, body):
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}\n{body}")


def truthy(value):
    """把环境变量里的 true/false 字符串转成布尔值。"""

    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def env(name, default=None, required=False):
    """读取环境变量；required=True 时缺失就直接退出。"""

    value = os.getenv(name, default)
    if required and not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def read_diff():
    """读取待审查 diff。

    用法：
    - `python3 scripts/ai_review.py path/to.diff`：从文件读取。
    - `git diff | python3 scripts/ai_review.py -`：从标准输入读取。
    """

    if len(sys.argv) > 1 and sys.argv[1] != "-":
        with open(sys.argv[1], "r", encoding="utf-8", errors="replace") as file:
            return file.read()
    return sys.stdin.read()


def truncate_diff(diff, max_chars):
    """限制发送给模型的 diff 长度。

    大 MR 可能超过模型上下文或导致费用过高，所以保留头尾，中间用提示文字替代。
    头部通常包含文件列表和前半段修改，尾部通常包含后半段修改，二者都比只截前面更有参考价值。
    """

    if len(diff) <= max_chars:
        return diff, False

    head_size = max_chars // 2
    tail_size = max_chars - head_size
    truncated = (
        diff[:head_size]
        + "\n\n[AI_REVIEW_NOTICE] diff too large, middle content truncated.\n\n"
        + diff[-tail_size:]
    )
    return truncated, True


def read_optional_file(path):
    """读取可选上下文文件；文件不存在或路径为空时返回空字符串。"""

    if not path:
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as file:
            return file.read().strip()
    except OSError as error:
        return f"[无法读取上下文文件 {path}: {error}]"


def build_messages(diff, language, truncated, project_name, project_context, review_focus):
    """组装 OpenAI Chat Completions 所需的 messages。

    system_prompt 告诉模型项目背景和审查规则；
    user_prompt 放入本次 diff，并要求模型按固定 Markdown 模板输出。
    """

    truncated_notice = (
        "注意：diff 因长度限制已截断中间部分，请只基于可见内容判断。"
        if truncated
        else "diff 未截断。"
    )

    project_notes = []
    if project_name and project_name != "current-project":
        project_notes.append(f"项目名称：{project_name}")
    if project_context.strip():
        project_notes.append("项目背景：\n" + project_context.strip())
    if review_focus.strip():
        project_notes.append("当前项目重点关注：\n" + review_focus.strip())

    project_notes_block = ""
    if project_notes:
        project_notes_block = "\n\n项目补充信息：\n" + "\n\n".join(project_notes)

    system_prompt = f"""你是资深代码审查员。
你正在审查一个新项目的 git diff。

审查规则：
1. 只审查 diff 中出现的变更，不推测未展示的代码。
2. 优先发现会导致生产事故、数据错误、安全问题、编译失败、权限绕过或核心流程不可用的问题。
3. 不输出泛泛建议，不做纯代码风格审查。
4. 每个问题必须给出级别、文件、行号或可定位片段、风险说明、修改建议。
5. 如果无法确认是问题，标记为 INFO 或不输出。
6. 输出中文 Markdown。
7. 必须逐行检查新增代码里的确定性阻塞问题，例如常量除以 0、未处理的必现异常、调试输出导致核心接口不可用。

级别定义：
- BLOCKER：必须修复，否则可能导致生产事故、数据损坏、安全漏洞、编译失败、权限泄露或核心流程不可用。
- MAJOR：建议修复，存在明确逻辑缺陷、兼容性风险、事务风险、质量风险或测试缺失。
- MINOR：一般建议，不阻断。
- INFO：上下文说明。
{project_notes_block}
"""

    user_prompt = f"""请审查以下 git diff，并严格按模板输出。

输出语言：{language}
{truncated_notice}

# 结论
- 状态：PASS / NEEDS_ATTENTION / FAIL
- 摘要：一句话说明整体风险

# BLOCKER
- 无 / 问题列表

# MAJOR
- 无 / 问题列表

# MINOR
- 无 / 问题列表

# 建议补充的测试
- 无 / 测试建议

git diff:
```diff
{diff}
```
"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def chat_completions_url(base_url):
    """兼容两类配置：

    - AI_BASE_URL=https://api.deepseek.com
    - AI_BASE_URL=https://api.deepseek.com/chat/completions
    """

    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return normalized + "/chat/completions"


def ssl_context():
    """创建 HTTPS 证书上下文。

    有些本机 Python 没有正确加载系统证书，优先使用 certifi 可以减少证书校验失败。
    如果公司代理需要自定义 CA，可以通过 AI_REVIEW_CA_FILE 指定。
    """

    ca_file = os.getenv("AI_REVIEW_CA_FILE")
    if ca_file:
        return ssl.create_default_context(cafile=ca_file)

    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except (ImportError, OSError):
        return ssl.create_default_context()


def open_request(request, timeout, use_env_proxy):
    """通过 urllib 发起请求。

    urllib 默认会读取系统或 shell 中的 HTTP(S)_PROXY 环境变量。
    use_env_proxy=False 时不走这里，而是走 read_ai_response_direct 做直连。
    """

    if not use_env_proxy:
        raise ValueError("open_request only handles environment-proxy requests")
    return urllib.request.urlopen(request, timeout=timeout, context=ssl_context())


def read_ai_response_direct(request, timeout):
    """绕过 urllib 代理配置，直接连接 AI 服务。

    这是为了解决某些本机代理导致的 `Connection reset by peer`。
    只有在代理请求失败且允许重试时才会走到这里。
    """

    parsed = urllib.parse.urlparse(request.full_url)
    path = parsed.path or "/"
    if parsed.query:
        path = path + "?" + parsed.query

    headers = dict(request.header_items())
    connection_class = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    connection_kwargs = {"timeout": timeout}
    if parsed.scheme == "https":
        connection_kwargs["context"] = ssl_context()

    connection = connection_class(parsed.netloc, **connection_kwargs)
    try:
        connection.request(request.get_method(), path, body=request.data, headers=headers)
        response = connection.getresponse()
        body = response.read().decode("utf-8", errors="replace")
    finally:
        connection.close()

    if response.status >= 400:
        raise AiHttpError(response.status, body)
    return json.loads(body)


def retryable_network_error(error):
    """判断网络错误是否值得尝试“绕过代理再请求一次”。"""

    text = str(getattr(error, "reason", error)).lower()
    return (
        "connection reset" in text
        or "connection aborted" in text
        or "remote end closed" in text
        or "timed out" in text
    )


def read_ai_response(request, timeout, use_env_proxy):
    """根据配置选择代理请求或直连请求，并返回 JSON。"""

    if not use_env_proxy:
        return read_ai_response_direct(request, timeout)

    with open_request(request, timeout=timeout, use_env_proxy=True) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


def call_ai(base_url, api_key, model, messages, timeout, disable_proxy, retry_without_proxy):
    """调用 OpenAI 兼容的 /chat/completions 接口并返回模型文本。

    失败时抛出 SystemExit，让 main() 可以根据 AI_REVIEW_FAIL_ON_ERROR 决定是否阻塞。
    """

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "stream": False,
    }
    request = urllib.request.Request(
        chat_completions_url(base_url),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "generic-ai-review/1.0",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    started_at = time.time()
    use_env_proxy = not disable_proxy
    try:
        data = read_ai_response(request, timeout=timeout, use_env_proxy=use_env_proxy)
    except AiHttpError as error:
        raise SystemExit(f"AI request failed: HTTP {error.status}\n{error.body}")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"AI request failed: HTTP {error.code}\n{body}")
    except urllib.error.URLError as error:
        if use_env_proxy and retry_without_proxy and retryable_network_error(error):
            # 常见于公司代理或本机代理异常：先提示，再绕过代理直连重试一次。
            print(f"AI request failed via proxy, retrying without proxy: {error}", file=sys.stderr)
            try:
                data = read_ai_response(request, timeout=timeout, use_env_proxy=False)
            except AiHttpError as direct_error:
                raise SystemExit(f"AI request failed without proxy: HTTP {direct_error.status}\n{direct_error.body}")
            except (urllib.error.URLError, OSError) as direct_error:
                raise SystemExit(f"AI request failed without proxy: {direct_error}")
            except json.JSONDecodeError as direct_error:
                raise SystemExit(f"AI response without proxy is not valid JSON: {direct_error}")
        else:
            raise SystemExit(f"AI request failed: {error}")
    except OSError as error:
        if use_env_proxy and retry_without_proxy and retryable_network_error(error):
            # 某些连接重置会表现为 OSError，不一定被 urllib 包成 URLError。
            print(f"AI request failed via proxy, retrying without proxy: {error}", file=sys.stderr)
            try:
                data = read_ai_response(request, timeout=timeout, use_env_proxy=False)
            except AiHttpError as direct_error:
                raise SystemExit(f"AI request failed without proxy: HTTP {direct_error.status}\n{direct_error.body}")
            except (urllib.error.URLError, OSError) as direct_error:
                raise SystemExit(f"AI request failed without proxy: {direct_error}")
            except json.JSONDecodeError as direct_error:
                raise SystemExit(f"AI response without proxy is not valid JSON: {direct_error}")
        else:
            raise SystemExit(f"AI request failed: {error}")
    except json.JSONDecodeError as error:
        raise SystemExit(f"AI response is not valid JSON: {error}")

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        safe_response = json.dumps(data, ensure_ascii=False)[:2000]
        raise SystemExit(f"Unexpected AI response: {error}\n{safe_response}")

    elapsed_ms = int((time.time() - started_at) * 1000)
    print(f"AI review request completed in {elapsed_ms} ms", file=sys.stderr)
    return content


def call_ai_with_failure_report(base_url, api_key, model, messages, timeout, disable_proxy, retry_without_proxy):
    """调用 AI；如果失败，返回一份 Markdown 失败报告。

    这样 Git Hook / CI 即使遇到网络或配置问题，也能生成可读报告，而不是静默退出。
    第二个返回值表示 AI 请求是否失败。
    """

    try:
        return call_ai(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=messages,
            timeout=timeout,
            disable_proxy=disable_proxy,
            retry_without_proxy=retry_without_proxy,
        ), False
    except SystemExit as error:
        message = str(error)
        if not message:
            raise
        return f"""# AI Code Review

# 结论
- 状态：NEEDS_ATTENTION
- 摘要：AI 审查请求失败，未完成模型审查。

# BLOCKER
- 无

# MAJOR
- AI 审查请求失败：`{message}`

# MINOR
- 无

# 建议补充的测试
- 检查 `AI_BASE_URL`、`AI_MODEL`、网络代理和 API Key 配置后重新运行审查。
""", True


def has_blocker(report):
    """判断 AI 报告里是否有 BLOCKER。

    这里解析的是“模型输出的 Markdown 报告”，不是对源码做本地规则扫描。
    pre-commit 是否阻止提交，取决于 AI 是否在 BLOCKER 段写出问题。
    """

    match = re.search(r"(?ims)^#\s+BLOCKER\s*\n(?P<body>.*?)(?=^#\s+|\Z)", report)
    if not match:
        return False

    body = match.group("body").strip()
    if not body:
        return False

    no_issue_patterns = [
        r"^[-*\s]*(无|没有|none|n/a|no blockers?)\s*[。.]?$",
        r"^[-*\s]*(无明确问题|未发现|暂无)\s*[。.]?$",
    ]
    return not any(re.match(pattern, body, flags=re.IGNORECASE) for pattern in no_issue_patterns)


def write_report(path, report):
    """把 Markdown 报告写到指定路径，并自动创建目录。"""

    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write(report.rstrip())
        file.write("\n")


def missing_config_report(missing_names):
    """缺少 AI 配置时生成说明报告。

    例如本地没有导出 AI_BASE_URL / AI_API_KEY / AI_MODEL。
    pre-commit 会因为 AI_REVIEW_FAIL_ON_ERROR=true 阻止提交；
    post-commit 默认只写报告，不影响已经完成的提交。
    """

    missing = "、".join(f"`{name}`" for name in missing_names)
    return f"""# AI Code Review

# 结论
- 状态：NEEDS_ATTENTION
- 摘要：AI 审查未执行，缺少必要模型配置。

# BLOCKER
- 无

# MAJOR
- 缺少必要环境变量：{missing}。AI review hook 已触发并生成 diff，但无法调用 DeepSeek / OpenAI 兼容接口。

# MINOR
- 无

# 建议补充的测试
- 在执行 `git commit` 的同一个 shell 中导出 `AI_BASE_URL`、`AI_API_KEY`、`AI_MODEL` 后重新提交或手动运行 `.githooks/post-commit`。
"""


def main():
    """脚本入口：读取配置、调用 AI、写报告、按策略返回退出码。"""

    # 输出位置由调用方决定：
    # - pre-commit: build/ai-review/pre-commit-review.md
    # - post-commit: build/ai-review/last-commit-review.md
    # - CI: 通常是 build/ai-review.md
    output = env("AI_REVIEW_OUTPUT", "build/ai-review.md")

    # fail_on_blocker=true：AI 报告出现 BLOCKER 时返回非 0。
    # fail_on_error=true：AI 配置缺失或请求失败时也返回非 0。
    fail_on_blocker = truthy(env("AI_REVIEW_FAIL_ON_BLOCKER", "false"))
    fail_on_error = truthy(env("AI_REVIEW_FAIL_ON_ERROR", "false"))

    # 三个变量是调用 OpenAI 兼容接口的最低配置。
    required_config = {
        "AI_BASE_URL": os.getenv("AI_BASE_URL"),
        "AI_API_KEY": os.getenv("AI_API_KEY"),
        "AI_MODEL": os.getenv("AI_MODEL"),
    }
    missing_config = [name for name, value in required_config.items() if not value]
    if missing_config:
        report = missing_config_report(missing_config)
        write_report(output, report)
        print(report)
        if fail_on_error:
            raise SystemExit(2)
        return

    base_url = required_config["AI_BASE_URL"]
    api_key = required_config["AI_API_KEY"]
    model = required_config["AI_MODEL"]
    max_chars = int(env("AI_REVIEW_MAX_CHARS", str(DEFAULT_MAX_CHARS)))
    timeout = int(env("AI_REVIEW_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS)))
    language = env("AI_REVIEW_LANGUAGE", "zh-CN")
    project_name = env("AI_REVIEW_PROJECT_NAME", "")
    project_context = env("AI_REVIEW_PROJECT_CONTEXT", "")
    context_from_file = read_optional_file(env("AI_REVIEW_PROJECT_CONTEXT_FILE", ""))
    if context_from_file:
        project_context = (project_context + "\n\n" + context_from_file).strip()
    review_focus = env("AI_REVIEW_REVIEW_FOCUS", "")

    # 默认先尊重本机代理；如果代理连接被重置，默认再尝试直连一次。
    disable_proxy = truthy(env("AI_REVIEW_DISABLE_PROXY", "false"))
    retry_without_proxy = truthy(env("AI_REVIEW_RETRY_WITHOUT_PROXY", "true"))

    ai_failed = False
    diff, truncated = truncate_diff(read_diff(), max_chars)
    if not diff.strip():
        report = "# AI Code Review\n\n无可审查 diff。\n"
    else:
        messages = build_messages(
            diff=diff,
            language=language,
            truncated=truncated,
            project_name=project_name,
            project_context=project_context,
            review_focus=review_focus,
        )
        report, ai_failed = call_ai_with_failure_report(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=messages,
            timeout=timeout,
            disable_proxy=disable_proxy,
            retry_without_proxy=retry_without_proxy,
        )

    write_report(output, report)
    print(report)

    # AI 没跑成功时是否失败，由调用场景决定。
    # pre-commit 通常希望失败即阻止，post-commit 通常只提醒。
    if fail_on_error and ai_failed:
        raise SystemExit(2)

    # 这里只看 AI 报告是否有 BLOCKER，不做本地规则判断。
    if fail_on_blocker and has_blocker(report):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
````

## 附录 B：从空 Git 项目完整演练

这一节演示从一个空 Git 项目开始，完整跑通本地 AI 审查。

### B.1 创建空项目

```bash
mkdir -p /tmp/ai-review-demo
cd /tmp/ai-review-demo
git init
```

### B.2 创建目录

```bash
mkdir -p .githooks scripts ci build/ai-review
```

### B.3 放入四个脚本

把附录 A 的四段完整脚本分别放到：

```text
.githooks/pre-commit
.githooks/post-commit
scripts/ai_review.py
ci/ai-review.sh
```

设置权限：

```bash
chmod +x .githooks/pre-commit .githooks/post-commit scripts/ai_review.py ci/ai-review.sh
```

### B.4 启用 Git Hook

```bash
git config core.hooksPath .githooks
git config --get core.hooksPath
```

预期输出：

```text
.githooks
```

### B.5 配置 AI 环境变量

```bash
export AI_BASE_URL="https://api.deepseek.com"
export AI_API_KEY="你的 key"
export AI_MODEL="deepseek-v4-pro"
```

### B.6 先提交一份正常代码

```bash
cat > Demo.java <<'EOF'
public class Demo {
    public int ok() {
        return 1;
    }
}
EOF

git add Demo.java
git commit -m "test: initial demo"
```

如果模型配置和网络正常，commit 会成功，并生成：

```text
build/ai-review/pre-commit-review.md
build/ai-review/last-commit-review.md
```

### B.7 故意制造一个明显错误

```bash
cat > Demo.java <<'EOF'
public class Demo {
    public int ok() {
        return 1;
    }

    public int broken() {
        return 1 / 0;
    }
}
EOF

git add Demo.java
git commit -m "test: trigger ai blocker"
```

预期结果：

```text
Commit blocked by AI pre-commit review.
```

查看报告：

```bash
cat build/ai-review/pre-commit-review.md
```

如果这次没有被拦住，通常说明：

- 模型没有按预期输出 `# BLOCKER` 段。
- prompt 对“必现异常 / 除以 0”的要求不够明确。
- `AI_REVIEW_FAIL_ON_BLOCKER` 没有设置为 `true`。
- `pre-commit` 没有真正执行。

### B.8 修复后重新提交

```bash
cat > Demo.java <<'EOF'
public class Demo {
    public int ok() {
        return 1;
    }

    public int fixed() {
        return 2;
    }
}
EOF

git add Demo.java
git commit -m "test: fix blocker"
```

预期：提交成功。

### B.9 模拟 CI 审查

本地也可以手动跑 CI 脚本：

```bash
bash ci/ai-review.sh
cat build/ai-review.md
```

如果是在 GitLab MR 中，确认 artifact 里有：

```text
build/ai-review.diff
build/ai-review.md
build/ai-review.console.md
```

### B.10 演练完成后你应该理解什么

跑完这个演练后，应该能回答：

- 为什么只执行 `git config core.hooksPath .githooks` 不够。
- `pre-commit` 和 `post-commit` 分别什么时候运行。
- 为什么 MR 审查必须靠 CI，而不是靠本地 hook。
- `scripts/ai_review.py` 为什么是公共审查器。
- `BLOCKER` 为什么会阻止 commit。
- 报告文件分别在哪里看。
