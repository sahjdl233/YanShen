import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class AiConfigError(Exception):
    pass


class AiRequestError(Exception):
    pass


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 YanShen/local"
)


def masked_key(value):
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


def resolve_api_key(settings):
    inline_key = (settings["api_key"] or "").strip()
    if inline_key:
        return inline_key
    env_name = (settings["api_key_env"] or "").strip()
    if env_name:
        return os.environ.get(env_name, "").strip()
    return ""


def build_chat_url(base_url):
    base = base_url.strip().rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    parsed = urlparse(base)
    path = parsed.path.strip("/")
    path_parts = path.split("/") if path else []
    versioned_path = bool(path_parts and re.fullmatch(r"v\d+[a-z]*", path_parts[-1], flags=re.I))
    if (not versioned_path and len(path_parts) >= 2
            and re.fullmatch(r"v\d+[a-z]*", path_parts[-2], flags=re.I)
            and path_parts[-1].lower() == "openai"):
        versioned_path = True
    if parsed.netloc.endswith("api.deepseek.com") or versioned_path or base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"


def build_models_url(base_url):
    chat_url = build_chat_url(base_url)
    if chat_url.endswith("/chat/completions"):
        return chat_url.removesuffix("/chat/completions") + "/models"
    return chat_url.rstrip("/") + "/models"


def api_request_headers(api_key):
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }


def fetch_available_models(settings):
    api_key = resolve_api_key(settings)
    if not api_key:
        raise AiConfigError("未找到 API key。请在设置页填写 API key，或设置对应环境变量。")
    base_url = (settings["api_base_url"] or "").strip()
    if not base_url:
        raise AiConfigError("API Base URL 不能为空。")

    request = Request(build_models_url(base_url), headers=api_request_headers(api_key), method="GET")
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
        payload = json.loads(raw)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AiRequestError(f"获取模型列表失败：HTTP {exc.code}。{detail[:500]}") from exc
    except (URLError, TimeoutError) as exc:
        raise AiRequestError(f"获取模型列表失败：{getattr(exc, 'reason', exc)}") from exc
    except json.JSONDecodeError as exc:
        raise AiRequestError("模型列表返回格式无法解析，请手动填写模型名。") from exc

    rows = payload.get("data") if isinstance(payload, dict) else None
    if rows is None and isinstance(payload, dict):
        rows = payload.get("models")
    if rows is None and isinstance(payload, list):
        rows = payload
    if not isinstance(rows, list):
        raise AiRequestError("服务商未返回 OpenAI-compatible 模型列表，请手动填写模型名。")

    models = []
    for row in rows:
        if isinstance(row, str):
            name = row
        elif isinstance(row, dict):
            name = row.get("id") or row.get("model") or row.get("name") or ""
        else:
            continue
        name = str(name).strip()
        if name and name not in models:
            models.append(name)
    if not models:
        raise AiRequestError("服务商返回的模型列表为空，请手动填写模型名。")
    models.sort(key=str.casefold)
    return models


def chat_completion(settings, prompt, request_options=None):
    api_key = resolve_api_key(settings)
    if not api_key:
        raise AiConfigError("未找到 API key。请在设置页填写 API key，或设置对应环境变量。")

    base_url = (settings["api_base_url"] or "").strip().rstrip("/")
    if not base_url:
        raise AiConfigError("API Base URL 不能为空。")
    url = build_chat_url(base_url)
    model = (settings["model"] or "").strip()
    if not model:
        raise AiConfigError("模型名不能为空。")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是专业、严格、可操作的申论批改老师。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": float(settings["temperature"] or 0.2),
    }
    request_options = request_options or {}
    thinking_type = request_options.get("thinking")
    api_host = (urlparse(base_url).hostname or "").lower()
    if (
        thinking_type in {"enabled", "disabled"}
        and api_host == "api.deepseek.com"
        and model.startswith("deepseek-v4")
    ):
        payload["thinking"] = {"type": thinking_type}
    response_format = request_options.get("response_format")
    json_schema = request_options.get("json_schema")
    use_json = isinstance(response_format, dict) and response_format.get("type") == "json_object"
    if use_json:
        payload["messages"][0]["content"] += (
            " 当前任务要求 JSON 输出：最终内容必须是单个合法 JSON 对象，"
            "不要输出 Markdown、XML 标签或任何额外文字。"
            "字符串值内的英文双引号必须用反斜杠转义。"
            "禁止尾逗号、单引号、Python True/False/None。"
        )
        if isinstance(json_schema, dict):
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "grading_result", "strict": False, **json_schema},
            }
        else:
            payload["response_format"] = {"type": "json_object"}
    max_tokens = request_options.get("max_tokens")
    if isinstance(max_tokens, int) and 1 <= max_tokens <= 384000:
        payload["max_tokens"] = max_tokens
    def _send(p):
        req = Request(url, data=json.dumps(p, ensure_ascii=False).encode("utf-8"), headers=api_request_headers(api_key), method="POST")
        ai_timeout = int(os.environ.get("GONGKAO_AI_TIMEOUT", "300"))
        with urlopen(req, timeout=max(30, ai_timeout)) as resp:
            return resp.read().decode("utf-8")

    try:
        raw = _send(payload)
    except HTTPError as exc:
        if exc.code in (400, 422) and payload.get("response_format", {}).get("type") == "json_schema":
            payload["response_format"] = {"type": "json_object"}
            try:
                raw = _send(payload)
            except HTTPError as exc2:
                detail2 = exc2.read().decode("utf-8", errors="replace")
                raise AiRequestError(f"API 请求失败：HTTP {exc2.code}。{detail2[:500]}") from exc2
            except URLError as exc2:
                raise AiRequestError(f"API 连接失败：{exc2.reason}") from exc2
            except TimeoutError as exc2:
                raise AiRequestError("API 请求超时，请稍后重试或换用 Codex 手动模式。") from exc2
        else:
            detail = exc.read().decode("utf-8", errors="replace")
            raise AiRequestError(f"API 请求失败：HTTP {exc.code}。{detail[:500]}") from exc
    except URLError as exc:
        raise AiRequestError(f"API 连接失败：{exc.reason}") from exc
    except TimeoutError as exc:
        raise AiRequestError("API 请求超时，请稍后重试或换用 Codex 手动模式。") from exc

    try:
        parsed = json.loads(raw)
        content = parsed["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise AiRequestError("API 返回格式无法解析，请检查服务商是否兼容 OpenAI chat completions。") from exc
    return content, raw
