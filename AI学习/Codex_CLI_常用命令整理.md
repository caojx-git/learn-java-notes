# Codex CLI 常用命令整理

本文档基于本机 `codex-cli 0.132.0` 的 `--help` 输出整理，适合日常使用时快速查阅。

<!-- TOC -->

- [Codex CLI 常用命令整理](#codex-cli-常用命令整理)
  - [0. 命令速查与入门工作流](#0-命令速查与入门工作流)
    - [命令速查表](#命令速查表)
    - [任务跑偏时怎么处理](#任务跑偏时怎么处理)
    - [小白推荐工作流](#小白推荐工作流)
  - [1. 基础用法](#1-基础用法)
    - [`codex`](#codex)
    - [`codex --help`](#codex---help)
    - [`codex --version`](#codex---version)
  - [2. 非交互式执行](#2-非交互式执行)
    - [`codex exec`](#codex-exec)
    - [`codex exec resume`](#codex-exec-resume)
    - [`codex exec review`](#codex-exec-review)
  - [3. 代码审查](#3-代码审查)
    - [`codex review`](#codex-review)
  - [4. 登录与账号](#4-登录与账号)
    - [`codex login`](#codex-login)
    - [`codex logout`](#codex-logout)
  - [5. 会话管理](#5-会话管理)
    - [`codex resume`](#codex-resume)
    - [`codex fork`](#codex-fork)
  - [6. 应用补丁](#6-应用补丁)
    - [`codex apply`](#codex-apply)
  - [7. 常用全局选项](#7-常用全局选项)
    - [指定工作目录：`-C, --cd <DIR>`](#指定工作目录-c---cd-dir)
    - [指定模型：`-m, --model <MODEL>`](#指定模型-m---model-model)
    - [指定配置 profile：`-p, --profile <CONFIG_PROFILE>`](#指定配置-profile-p---profile-config_profile)
    - [覆盖配置：`-c, --config <key=value>`](#覆盖配置-c---config-keyvalue)
    - [指定沙箱模式：`-s, --sandbox <MODE>`](#指定沙箱模式-s---sandbox-mode)
    - [指定审批策略：`-a, --ask-for-approval <POLICY>`](#指定审批策略-a---ask-for-approval-policy)
    - [启用网页搜索：`--search`](#启用网页搜索--search)
    - [附加图片：`-i, --image <FILE>`](#附加图片-i---image-file)
  - [8. MCP 服务器管理](#8-mcp-服务器管理)
    - [`codex mcp`](#codex-mcp)
  - [9. 插件管理](#9-插件管理)
    - [`codex plugin`](#codex-plugin)
  - [10. 桌面 App 与服务](#10-桌面-app-与服务)
    - [`codex app`](#codex-app)
    - [`codex app-server`](#codex-app-server)
    - [`codex remote-control`](#codex-remote-control)
  - [11. 诊断、更新与补全](#11-诊断更新与补全)
    - [`codex doctor`](#codex-doctor)
    - [`codex update`](#codex-update)
    - [`codex completion`](#codex-completion)
  - [12. 沙箱命令](#12-沙箱命令)
    - [`codex sandbox`](#codex-sandbox)
  - [13. 功能开关](#13-功能开关)
    - [`codex features`](#codex-features)
  - [14. 其他命令](#14-其他命令)
    - [`codex mcp-server`](#codex-mcp-server)
    - [`codex cloud`](#codex-cloud)
    - [`codex exec-server`](#codex-exec-server)
    - [`codex debug`](#codex-debug)
  - [15. 推荐日常命令组合](#15-推荐日常命令组合)
    - [启动当前目录交互式开发](#启动当前目录交互式开发)
    - [在指定目录启动](#在指定目录启动)
    - [一次性执行任务](#一次性执行任务)
    - [审查当前未提交改动](#审查当前未提交改动)
    - [恢复最近会话](#恢复最近会话)
    - [检查本机 Codex 状态](#检查本机-codex-状态)
    - [查看插件](#查看插件)
    - [查看 MCP 配置](#查看-mcp-配置)
    - [更新 Codex](#更新-codex)
  - [16. 交互式斜杠命令](#16-交互式斜杠命令)
    - [会话与上下文](#会话与上下文)
    - [模型、风格与速度](#模型风格与速度)
    - [权限、安全与执行控制](#权限安全与执行控制)
    - [文件、项目与代码上下文](#文件项目与代码上下文)
    - [状态、配置与界面](#状态配置与界面)
    - [扩展能力](#扩展能力)
    - [账号与反馈](#账号与反馈)
    - [退出 Codex CLI](#退出-codex-cli)
    - [常用斜杠命令组合](#常用斜杠命令组合)
  - [17. 多消息与排队操作](#17-多消息与排队操作)
    - [Enter 引导当前任务](#enter-引导当前任务)
    - [排队斜杠命令](#排队斜杠命令)
    - [中断或修正当前任务](#中断或修正当前任务)
    - [推荐用法](#推荐用法)
  - [18. 注意事项](#18-注意事项)

<!-- /TOC -->

## 0. 命令速查与入门工作流

如果刚开始用 Codex CLI，先记住这一节就够了。完整命令可以后面再查。

### 命令速查表

速查表只放“该用哪个命令”。需要看参数、示例和注意事项时，再看后面的详细章节。

| 分类 | 操作 | 怎么用 | 作用 |
| --- | --- | --- | --- |
| 启动 | 启动 Codex | `codex` | 进入交互式 CLI。 |
| 启动 | 指定目录启动 | `codex -C /path/to/project` | 让 Codex 在指定项目目录工作。 |
| 启动 | 带初始需求启动 | `codex "帮我检查这个项目"` | 启动时直接给 Codex 一个任务。 |
| 基础 | 查看帮助 | `codex --help` | 查看 Codex 顶层帮助。 |
| 基础 | 查看版本 | `codex --version` | 查看当前安装的 Codex CLI 版本。 |
| 基础 | 本地 shell 命令 | `!pwd`、`!git status` | 在交互界面里临时执行本地命令。 |
| 启动选项 | 指定模型启动 | `codex -m <MODEL>` | 启动时指定使用哪个模型。 |
| 启动选项 | 指定配置 profile | `codex -p <PROFILE>` | 使用某套预设配置启动。 |
| 启动选项 | 覆盖配置项 | `codex -c key=value` | 临时覆盖某个配置值。 |
| 启动选项 | 指定沙箱模式 | `codex -s <MODE>` | 控制本次会话的文件系统/命令沙箱。 |
| 启动选项 | 指定审批策略 | `codex -a <POLICY>` | 控制 Codex 什么时候需要向你确认。 |
| 启动选项 | 启用网页搜索 | `codex --search` | 允许 Codex 使用网页搜索。 |
| 启动选项 | 附加图片 | `codex -i <FILE>` | 把图片作为初始上下文发给 Codex。 |
| 任务 | 一次性执行任务 | `codex exec "修复测试失败"` | 非交互式执行任务，适合脚本或 CI。 |
| 任务 | 恢复非交互任务 | `codex exec resume` | 恢复之前的非交互式会话。 |
| 任务 | 非交互式审查 | `codex exec review` | 用非交互方式执行代码审查。 |
| 任务 | 审查代码改动 | `codex review` 或 `/review` | 检查当前工作区改动中的问题。 |
| 任务 | 查看代码改动 | `/diff` | 查看当前 Git diff，包括未跟踪文件。 |
| 任务 | 应用补丁 | `codex apply` | 把 Codex 生成的补丁应用到工作区。 |
| 任务 | 复制最近输出 | `/copy` | 复制最近一次 Codex 完成的回复。 |
| 状态 | 查看当前状态 | `/status` | 看模型、权限、token、工作目录等。 |
| 状态 | 查询额度/limits | `/status` | 查看当前账号额度、限额窗口、token 使用等信息。 |
| 模型 | 切换模型/推理强度 | `/model` | 选择模型和 reasoning effort。 |
| 模型 | 切换快速模式 | `/fast` | 切换 Fast 服务层级。 |
| 模型 | 切换回复风格 | `/personality` | 调整 Codex 回复风格。 |
| 权限 | 调整权限 | `/permissions` | 控制 Codex 能读写什么、能否执行命令。 |
| 权限 | 批准被拦截操作 | `/approve` | 对最近一次被自动审查拒绝的操作批准重试。 |
| 会话 | 退出 Codex | `/quit` 或 `/exit` | 退出交互式 CLI。 |
| 会话 | 新开会话 | `/new` | 开始一个干净的新聊天。 |
| 会话 | 丢弃当前会话记忆 | `/clear` | 清空当前聊天上下文，从一个干净聊天重新开始。 |
| 会话 | 压缩上下文 | `/compact` | 对话很长时压缩历史，释放上下文空间。 |
| 会话 | 恢复会话 | `/resume` 或 `codex resume --last` | 回到之前的会话。 |
| 会话 | 分叉会话 | `/fork` | 保留当前上下文，但开一条新路线尝试。 |
| 会话 | 临时侧边对话 | `/side` | 开一个不打断主会话上下文的临时对话。 |
| 会话 | 计划模式 | `/plan` | 让 Codex 先给方案，再按方案执行。 |
| 会话 | 长期目标 | `/goal` | 设置、查看、暂停、恢复或清除长期任务目标。 |
| 执行 | 停止后台任务 | `/stop` | 停止当前会话启动的后台终端任务。 |
| 执行 | 查看后台任务 | `/ps` | 查看实验性的后台终端及最近输出。 |
| 项目 | 初始化项目说明 | `/init` | 生成 `AGENTS.md`，记录项目规则和偏好。 |
| 项目 | 添加文件上下文 | `/mention` | 把某个文件或目录附加到对话上下文。 |
| 项目 | 添加 IDE 上下文 | `/ide` | 引入 IDE 当前打开文件、选区等上下文。 |
| 扩展 | 查看 MCP 工具 | `/mcp` | 列出已配置 MCP 工具。 |
| 扩展 | 管理 MCP 服务器 | `codex mcp` | 添加、删除、查看 MCP 服务器配置。 |
| 扩展 | 查看插件 | `/plugins` | 浏览已安装或可发现的插件。 |
| 扩展 | 管理插件 | `codex plugin` | 安装、查看、管理 Codex 插件。 |
| 扩展 | 查看 Skills | `/skills` | 浏览并使用本地 skills。 |
| 扩展 | 查看 Apps | `/apps` | 浏览连接器或 App，并插入提示词。 |
| 扩展 | 查看 Hooks | `/hooks` | 查看和管理生命周期 hooks。 |
| 扩展 | 管理 Memories | `/memories` | 配置 memory 注入和生成。 |
| 扩展 | 实验性功能 | `/experimental` 或 `codex features` | 查看或开关实验性功能。 |
| 扩展 | MCP 服务模式 | `codex mcp-server` | 以 MCP server 方式运行 Codex。 |
| 配置 | 查看配置诊断 | `/debug-config` | 打印配置层、要求来源和策略诊断信息。 |
| 配置 | 配置状态栏 | `/statusline` | 配置 TUI 底部状态栏显示哪些信息。 |
| 配置 | 配置终端标题 | `/title` | 配置终端窗口或标签页标题显示内容。 |
| 配置 | 配置主题 | `/theme` | 选择终端语法高亮主题。 |
| 配置 | 配置快捷键 | `/keymap` | 重映射 TUI 快捷键。 |
| 配置 | Vim 输入模式 | `/vim` | 开关输入框的 Vim 编辑模式。 |
| 配置 | Raw scrollback | `/raw` | 开关 raw scrollback 模式，便于复制终端内容。 |
| 账号 | 登录账号 | `codex login` | 登录 Codex 账号。 |
| 账号 | 退出登录 | `/logout` 或 `codex logout` | 清除本地登录凭据。 |
| 诊断 | 检查本机状态 | `codex doctor` | 检查本机 Codex 环境和常见问题。 |
| 诊断 | 更新 Codex | `codex update` | 更新 Codex CLI。 |
| 诊断 | Shell 补全 | `codex completion` | 生成 shell completion 配置。 |
| 诊断 | 沙箱内执行命令 | `codex sandbox` | 在 Codex 沙箱环境中执行命令。 |
| 诊断 | 发送反馈 | `/feedback` | 向 Codex 维护者发送日志和反馈。 |
| 其他 | 桌面 App | `codex app` | 启动或管理 Codex 桌面 App 相关能力。 |
| 其他 | App 服务 | `codex app-server` | 启动 Codex App 本地服务。 |
| 其他 | 远程控制 | `codex remote-control` | 启动远程控制相关能力。 |
| 其他 | 云端能力 | `codex cloud` | 使用 Codex cloud 相关命令。 |
| 其他 | Exec 服务 | `codex exec-server` | 启动非交互执行服务。 |
| 其他 | 调试命令 | `codex debug` | 使用 Codex 调试相关命令。 |

`!` 开头的是交互界面里的本地 shell 命令，不是斜杠命令：

```text
!ls
```

在交互界面里，以 `!` 开头可以运行本地 shell 命令。例如：

```text
!pwd
```

```text
!git status
```

适合临时查看目录、Git 状态、文件列表等。

### 任务跑偏时怎么处理

Codex 正在执行任务时，你可以继续输入消息。这里最重要的是区分 `Enter` 和 `Tab`：

| 按键 | 效果 | 什么时候用 |
| --- | --- | --- |
| `Enter` | 立刻发送，作为当前任务的引导信息 | Codex 走偏了，需要马上纠正 |
| `Tab` | 排队，等当前任务结束后再执行 | 提前安排下一步，例如 `/diff`、`/review` |

Codex 跑偏时，直接按 `Enter` 发送明确纠偏消息：

```text
当前方向不对。不要继续改文件，先说明你准备怎么处理。
```

```text
这不是下一步任务，是对当前任务的修正：只更新 Markdown 文档，不写代码。
```

```text
停止刚才的实现方向，改为先分析问题原因。
```

如果只是想提前安排下一步，就用 `Tab` 排队：

```text
/diff
```

```text
/review
```

### 小白推荐工作流

第一次进入项目：

```bash
codex -C /path/to/project
```

进入后先看状态：

```text
/status
```

需要查额度时也用：

```text
/status
```

确认权限：

```text
/permissions
```

让 Codex 做任务：

```text
帮我修复这个项目的启动报错。
```

任务完成后检查改动：

```text
/diff
```

再让 Codex 自查：

```text
/review
```

对话太长时：

```text
/compact
```

结束时：

```text
/quit
```

## 1. 基础用法

### `codex`

启动 Codex 交互式命令行界面。

```bash
codex
```

也可以直接带上初始需求：

```bash
codex "帮我检查当前项目的测试失败原因"
```

常用场景：

- 和 Codex 进行交互式开发、排查、改代码。
- 在当前目录中让 Codex 读取项目并执行任务。
- 配合 `-C` 指定工作目录。

### `codex --help`

查看 Codex 顶层帮助。

```bash
codex --help
```

### `codex --version`

查看当前安装版本。

```bash
codex --version
```

## 2. 非交互式执行

### `codex exec`

非交互式运行 Codex，适合脚本、CI 或一次性任务。

```bash
codex exec "总结这个仓库的目录结构"
```

别名：

```bash
codex e "修复 lint 错误"
```

也可以从标准输入读取提示词：

```bash
cat task.txt | codex exec -
```

常用选项：

- `--json`：以 JSONL 事件流输出，适合程序处理。
- `-o, --output-last-message <FILE>`：把 Codex 最后一条回复写入文件。
- `--ephemeral`：不把会话文件持久化到磁盘。
- `--skip-git-repo-check`：允许在非 Git 仓库目录运行。

示例：

```bash
codex exec --json "检查当前目录有什么 Python 文件"
```

```bash
codex exec -o result.md "生成项目说明文档"
```

### `codex exec resume`

恢复之前的非交互式会话。

```bash
codex exec resume --last
```

适合继续上一次自动化任务。

### `codex exec review`

在 `exec` 模式下运行代码审查。

```bash
codex exec review
```

## 3. 代码审查

### `codex review`

非交互式执行代码审查。

```bash
codex review
```

常用选项：

- `--uncommitted`：审查 staged、unstaged 和 untracked 的本地改动。
- `--base <BRANCH>`：审查当前分支相对某个基础分支的改动。
- `--commit <SHA>`：审查某个提交引入的改动。
- `--title <TITLE>`：给审查摘要指定标题。

示例：

```bash
codex review --uncommitted
```

```bash
codex review --base main
```

```bash
codex review --commit abc1234
```

## 4. 登录与账号

### `codex login`

登录 Codex。

```bash
codex login
```

常用子命令和选项：

- `codex login status`：查看登录状态。
- `--with-api-key`：从标准输入读取 API Key。
- `--with-access-token`：从标准输入读取访问令牌。
- `--device-auth`：使用设备授权方式登录。

示例：

```bash
codex login status
```

```bash
printenv OPENAI_API_KEY | codex login --with-api-key
```

### `codex logout`

移除本机保存的认证凭据。

```bash
codex logout
```

## 5. 会话管理

### `codex resume`

恢复之前的交互式会话。

```bash
codex resume
```

常用选项：

- `--last`：直接恢复最近一次会话，不打开选择器。
- `--all`：显示所有会话，不按当前目录过滤。
- `--include-non-interactive`：选择范围包括非交互式会话。

示例：

```bash
codex resume --last
```

也可以指定会话 ID 或线程名：

```bash
codex resume <SESSION_ID>
```

### `codex fork`

从历史会话分叉出一个新会话。

```bash
codex fork
```

常用场景：

- 想保留原会话上下文，但走另一条实现路线。
- 基于之前的讨论另开一个方向继续。

## 6. 应用补丁

### `codex apply`

把 Codex Cloud 或任务产生的最新 diff 应用到本地工作区，底层类似 `git apply`。

```bash
codex apply <TASK_ID>
```

别名：

```bash
codex a <TASK_ID>
```

适合把远程任务结果落到本地代码。

## 7. 常用全局选项

这些选项可以搭配多个命令使用。

### 指定工作目录：`-C, --cd <DIR>`

```bash
codex -C /path/to/project
```

作用：让 Codex 使用指定目录作为工作根目录。

### 指定模型：`-m, --model <MODEL>`

```bash
codex -m gpt-5.4
```

作用：指定本次会话使用的模型。

### 指定配置 profile：`-p, --profile <CONFIG_PROFILE>`

```bash
codex -p work
```

作用：使用 `~/.codex/config.toml` 中的某个配置 profile。

### 覆盖配置：`-c, --config <key=value>`

```bash
codex -c model='"gpt-5.4"'
```

作用：临时覆盖配置文件中的值。支持点路径配置，例如：

```bash
codex -c shell_environment_policy.inherit=all
```

### 指定沙箱模式：`-s, --sandbox <MODE>`

```bash
codex -s workspace-write
```

可选值：

- `read-only`：只读。
- `workspace-write`：允许写当前工作区。
- `danger-full-access`：高权限模式，谨慎使用。

### 指定审批策略：`-a, --ask-for-approval <POLICY>`

```bash
codex -a on-request
```

常见值：

- `untrusted`：只有可信命令可直接执行，其他命令需要审批。
- `on-request`：由 Codex 判断何时请求审批。
- `never`：不请求审批，失败直接返回给模型。
- `on-failure`：已弃用，不推荐。

### 启用网页搜索：`--search`

```bash
codex --search
```

作用：为模型启用实时网页搜索工具。

### 附加图片：`-i, --image <FILE>`

```bash
codex -i screenshot.png "分析这个界面的问题"
```

作用：把图片作为初始输入的一部分。

## 8. MCP 服务器管理

### `codex mcp`

管理 Codex 可连接的外部 MCP 服务器。

```bash
codex mcp list
```

常用子命令：

- `list`：列出已配置 MCP 服务器。
- `get`：查看某个 MCP 服务器配置。
- `add`：添加 MCP 服务器。
- `remove`：移除 MCP 服务器。
- `login`：登录某个 MCP 服务。
- `logout`：退出某个 MCP 服务。

适合接入外部工具、数据库、服务 API 或企业内部系统。

## 9. 插件管理

### `codex plugin`

管理 Codex 插件。

```bash
codex plugin list
```

常用子命令：

- `list`：列出插件市场中可用插件。
- `add`：从已配置的 marketplace snapshot 安装插件。
- `remove`：删除已安装插件。
- `marketplace`：添加、列出、升级或移除插件市场配置。

示例：

```bash
codex plugin list
```

```bash
codex plugin add <PLUGIN_NAME>
```

## 10. 桌面 App 与服务

### `codex app`

启动 Codex 桌面应用。如果未安装，会打开安装器。

```bash
codex app
```

### `codex app-server`

实验性命令，用于运行 app server 或相关工具。

```bash
codex app-server
```

### `codex remote-control`

实验性命令，用于管理启用了远程控制的 app-server daemon。

```bash
codex remote-control
```

## 11. 诊断、更新与补全

### `codex doctor`

诊断本地 Codex 安装、配置、认证和运行环境。

```bash
codex doctor
```

常用选项：

- `--summary`：只显示摘要。
- `--json`：输出脱敏后的机器可读报告。
- `--all`：展开详细列表。
- `--no-color`：关闭颜色输出。
- `--ascii`：使用 ASCII 状态符号。

示例：

```bash
codex doctor --summary
```

### `codex update`

更新 Codex 到最新版本。

```bash
codex update
```

### `codex completion`

生成 shell 自动补全脚本。

```bash
codex completion zsh
```

支持：

- `bash`
- `elvish`
- `fish`
- `powershell`
- `zsh`

## 12. 沙箱命令

### `codex sandbox`

在 Codex 提供的沙箱中运行命令。

```bash
codex sandbox macos <COMMAND>
```

子命令：

- `macos`：在 macOS Seatbelt 沙箱中运行命令。
- `linux`：在 Linux 沙箱中运行命令。
- `windows`：在 Windows restricted token 下运行命令。

常用场景：

- 测试命令在受限环境下的行为。
- 降低脚本或工具运行风险。

## 13. 功能开关

### `codex features`

查看或修改 Codex 功能开关。

```bash
codex features list
```

子命令：

- `list`：列出已知功能、阶段和当前状态。
- `enable`：在配置中启用某个功能。
- `disable`：在配置中禁用某个功能。

示例：

```bash
codex features enable <FEATURE_NAME>
```

```bash
codex features disable <FEATURE_NAME>
```

## 14. 其他命令

### `codex mcp-server`

以 stdio 方式把 Codex 启动为 MCP server。

```bash
codex mcp-server
```

适合集成到支持 MCP 的外部客户端。

### `codex cloud`

实验性命令，用于浏览 Codex Cloud 中的任务，并把变更应用到本地。

```bash
codex cloud
```

### `codex exec-server`

实验性命令，用于运行独立的 exec-server 服务。

```bash
codex exec-server
```

### `codex debug`

调试工具集合。

```bash
codex debug
```

## 15. 推荐日常命令组合

### 启动当前目录交互式开发

```bash
codex
```

### 在指定目录启动

```bash
codex -C /path/to/project
```

### 一次性执行任务

```bash
codex exec "帮我找出这个项目启动失败的原因"
```

### 审查当前未提交改动

```bash
codex review --uncommitted
```

### 恢复最近会话

```bash
codex resume --last
```

### 检查本机 Codex 状态

```bash
codex doctor --summary
```

### 查看插件

```bash
codex plugin list
```

### 查看 MCP 配置

```bash
codex mcp list
```

### 更新 Codex

```bash
codex update
```

## 16. 交互式斜杠命令

斜杠命令是在 `codex` 交互界面的输入框里使用的命令，不是终端里的 `codex <command>` 子命令。

进入 Codex 后，输入 `/` 可以打开命令弹窗；继续输入关键词可以筛选命令，例如输入 `/status`、`/model`、`/permissions`。

### 会话与上下文

| 命令 | 作用 |
| --- | --- |
| `/new` | 在当前 CLI 里开始一个新对话。 |
| `/resume` | 从历史会话列表恢复一个保存过的会话。 |
| `/fork` | 从当前会话分叉出一个新线程，用于尝试另一条路线。 |
| `/side` | 开启一个临时侧边对话，不打断主会话上下文。 |
| `/clear` | 清空终端界面并开始一个新聊天。 |
| `/compact` | 压缩当前对话上下文，释放 token 空间。 |
| `/goal` | 设置、查看、暂停、恢复或清除长期任务目标。需要启用 goals 功能。 |
| `/plan` | 切换到计划模式，可让 Codex 先给方案再执行。 |
| `/quit` | 退出 Codex CLI。 |
| `/exit` | 退出 Codex CLI，等同于 `/quit`。 |

### 模型、风格与速度

| 命令 | 作用 |
| --- | --- |
| `/model` | 切换当前模型，也可调整 reasoning effort。 |
| `/fast` | 切换 Fast 服务层级。是否可用取决于当前模型目录。 |
| `/personality` | 选择 Codex 回复风格，例如更简洁或更解释型。 |

### 权限、安全与执行控制

| 命令 | 作用 |
| --- | --- |
| `/permissions` | 调整 Codex 可以在不询问的情况下做什么。 |
| `/approve` | 对最近一次自动审查拒绝的操作批准重试。 |
| `/sandbox-add-read-dir` | 给沙箱增加额外只读目录。官方文档标注为 Windows only。 |
| `/review` | 让 Codex 审查当前工作区改动。 |
| `/diff` | 查看 Git diff，包括未被 Git 跟踪的文件。 |
| `/stop` | 停止当前会话启动的所有后台终端任务。 |
| `/ps` | 查看实验性的后台终端及最近输出。 |

### 文件、项目与代码上下文

| 命令 | 作用 |
| --- | --- |
| `/init` | 在当前目录生成 `AGENTS.md` 项目说明脚手架。 |
| `/mention` | 把某个文件或目录附加到对话上下文。 |
| `/ide` | 引入 IDE 当前打开文件、选区等上下文。 |
| `/copy` | 复制最近一次 Codex 完成的输出。 |

### 状态、配置与界面

| 命令 | 作用 |
| --- | --- |
| `/status` | 查看当前模型、审批策略、可写目录、token 使用、账号额度和限额窗口等状态。 |
| `/debug-config` | 打印配置层、要求来源和策略诊断信息。 |
| `/statusline` | 配置 TUI 底部状态栏显示哪些信息。 |
| `/title` | 配置终端窗口或标签页标题显示内容。 |
| `/theme` | 选择终端语法高亮主题。 |
| `/keymap` | 重映射 TUI 快捷键。 |
| `/vim` | 开关输入框的 Vim 编辑模式。 |
| `/raw` | 开关 raw scrollback 模式，便于复制终端内容。 |

### 扩展能力

| 命令 | 作用 |
| --- | --- |
| `/mcp` | 列出已配置 MCP 工具；可用 `/mcp verbose` 查看详情。 |
| `/apps` | 浏览连接器或 App，并把它们插入提示词。 |
| `/plugins` | 浏览已安装或可发现的插件。 |
| `/skills` | 浏览并使用本地 skills。 |
| `/hooks` | 查看和管理生命周期 hooks。 |
| `/memories` | 配置 memory 注入和生成。 |
| `/experimental` | 开关实验性功能。 |

### 账号与反馈

| 命令 | 作用 |
| --- | --- |
| `/logout` | 退出 Codex 登录，清除本地凭据。 |
| `/feedback` | 向 Codex 维护者发送日志和反馈。 |

### 退出 Codex CLI

在 Codex 交互界面里退出程序，推荐使用：

```text
/quit
```

或：

```text
/exit
```

两者都是退出 Codex CLI。

注意：

- `/logout` 不是退出程序，而是退出账号登录、清除本地凭据。
- `Ctrl+C` 在不同状态下行为可能不同：空闲时通常可以退出或返回；任务运行中更常用于中断当前操作。需要明确退出时优先用 `/quit` 或 `/exit`。

### 常用斜杠命令组合

```text
/status
```

确认当前模型、权限、上下文容量、token 使用和额度/limits。

```text
/model
```

切换模型或 reasoning effort。

```text
/permissions
```

调整 Codex 的读写和执行权限。

```text
/diff
```

查看 Codex 已经改了哪些文件。

```text
/review
```

让 Codex 对当前改动做一次代码审查。

```text
/compact
```

长对话快到上下文上限时压缩上下文。

```text
/mcp verbose
```

查看 MCP 服务器和工具的详细信息。

## 17. 多消息与排队操作

Codex CLI 交互界面支持在任务运行时继续输入内容。这里要区分两个动作：

- `Enter`：发送消息，引导当前正在执行的任务。
- `Tab`：把消息或斜杠命令排队，等当前任务结束后再执行。

### Enter 引导当前任务

当 Codex 正在执行任务时，你可以继续在输入框里写纠偏消息，然后按 `Enter` 发送。这个动作不是排队，而是把消息作为当前 turn 的引导信息，让 Codex 调整正在进行的工作。

常见用途：

- 补充刚才漏掉的约束。
- 发现 Codex 走偏时立刻纠正方向。
- 要求 Codex 暂停实现，先解释或确认。

示例：

```text
当前方向不对。不要改后端，只改 frontend 目录里的页面样式。
```

```text
这条不是下一步任务，是对当前任务的修正：不要生成测试文件，只修改 QuickSort.java。
```

```text
不要继续修改文件。先解释你准备改哪些地方，等我确认。
```

### 排队斜杠命令

当任务正在运行时，可以输入消息或斜杠命令，并按 `Tab` 将它排队到下一轮执行。

示例：

```text
/status
```

```text
/diff
```

```text
/review
```

排队后的命令会等当前 turn 结束后再处理。这个方式适合在 Codex 还没完成当前操作时，提前安排下一步检查。

简单区分：

| 操作 | 效果 | 适合场景 |
| --- | --- | --- |
| `Enter` | 立刻发送，用来引导当前任务 | Codex 走偏、需要纠正、需要补充约束 |
| `Tab` | 排队到下一轮 | 提前安排 `/diff`、`/review`、`/status` 等后续检查 |

### 中断或修正当前任务

如果当前任务方向明显不对，可以直接发送修正消息。写法要具体，避免只说“不是这个”。

推荐写法：

```text
先暂停实现。请只分析原因，不要继续改文件。
```

```text
上一条要求改一下：不要生成 PDF，只保留 Markdown。
```

```text
当前任务完成后，先运行测试，再总结改动。
```

不推荐：

```text
不是这个
```

```text
你错了
```

这类消息太短，Codex 不一定能判断该停止什么、保留什么、改向哪里。

### 推荐用法

```text
当前方向不对。先停止改文件，改为只更新 Markdown 文档。
```

```text
/diff
```

```text
/review
```

第一条用 `Enter` 发送，用来纠正当前任务；后面的 `/diff`、`/review` 可以用 `Tab` 排队，等当前任务结束后再检查结果。

## 18. 注意事项

- `--dangerously-bypass-approvals-and-sandbox` 会跳过审批和沙箱，风险很高，只应在外部已经有可靠隔离的自动化环境中使用。
- `danger-full-access` 沙箱模式权限很大，使用前应确认当前目录和命令风险。
- `review` 更适合找 bug、回归风险和缺失测试，不等同于格式化工具。
- `exec` 适合自动化任务；需要持续讨论和调整时，用普通 `codex` 交互模式更方便。
- 插件和 MCP 会扩展 Codex 能力，但也会引入额外依赖、权限和认证配置。
- 斜杠命令只在 `codex` 交互界面里使用；在普通 shell 里直接输入 `/status` 不会执行 Codex 命令。
