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
