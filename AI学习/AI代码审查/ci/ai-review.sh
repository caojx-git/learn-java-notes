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
