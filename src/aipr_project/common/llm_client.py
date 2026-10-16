import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional
import requests
from dotenv import load_dotenv
from groq import Groq, APIConnectionError, APIStatusError

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

load_dotenv()


DEFAULT_MODEL = "openai/gpt-oss-20b"

PRICING = {
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "openai/gpt-oss-20b": {"input": 0.15, "output": 0.6},
    "jina-embeddings-v3": {"input": 0.02, "output": 0.0},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
}


class AttrDict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name) from None

def _wrap(obj):
    if isinstance(obj, dict):
        return AttrDict({k: _wrap(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_wrap(v) for v in obj]
    return obj

def _jina_embeddings(
    input_data: str | list[str],
    api_key: str,
    model: str = "jina-embeddings-v3",
    task: str = "retrieval.passage",
    max_retries: int = 3,
    timeout: int = 30,
):
    if isinstance(input_data, str):
        texts = [input_data]
    else:
        texts = list(input_data)

    url = "https://api.jina.ai/v1/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model,
        "task": task,
        "normalized": True,
        "input": [{"text": t} for t in texts],
    }

    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)

            if resp.status_code in (401, 403):
                print(f"[CRITICAL HTTP {resp.status_code}] Sai JINA_API_KEY! Không retry.", file=sys.stderr)
                resp.raise_for_status()

            if resp.status_code == 200:
                result = resp.json()
                data = result.get("data", [])
                for i, item in enumerate(data):
                    item.setdefault("index", i)
                return _wrap(
                    {
                        "data": data,
                        "model": result.get("model", model),
                        "usage": result.get("usage", {}),
                    }
                )

            print(
                f"[HTTP {resp.status_code}] Jina lỗi tạm thời, đang thử lại lần {attempt + 1}...",
                file=sys.stderr,
            )

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code in (401, 403):
                raise e
            print(f"[HTTP {e.response.status_code if e.response else 'Error'}] Lỗi tạm thời, đang thử lại lần {attempt + 1}...", file=sys.stderr)

        except (requests.RequestException, TimeoutError) as e:
            print(f"[Network Error] {e}, thử lại lần {attempt + 1}...", file=sys.stderr)

        if attempt < max_retries:
            time.sleep(1.5 ** (attempt + 1))

    raise RuntimeError(f"Gọi Jina Embeddings thất bại sau {max_retries} lần retry.")

def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Tính chi phí ước tính dựa trên số lượng token."""
    pricing = PRICING.get(model, PRICING.get(DEFAULT_MODEL, {"input": 0.15, "output": 0.6}))
    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost

class LLMClient:
    def __init__(
        self,
        jina_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        default_model: str = DEFAULT_MODEL,
    ):
        self.jina_api_key = jina_api_key or os.getenv("JINA_API_KEY")
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.default_model = default_model

        if not self.groq_api_key:
            print("[WARNING] GROQ_API_KEY chưa được thiết lập trong .env!", file=sys.stderr)
        self.groq = Groq(api_key=self.groq_api_key)

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict[str, Any]]] = None,
        temperature: float = 0.0,
        model: Optional[str] = None,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        timeout: float = 30.0,
    ) -> Any:
        """
        Gửi yêu cầu chat tới Groq API.
        
        - Mặc định sử dụng model chuẩn duy nhất: openai/gpt-oss-20b.
        - Hỗ trợ truyền danh sách tool (function calling).
        - Retry exponential backoff khi gặp lỗi mạng/429/5xx.
        - KHÔNG retry khi sai API key hoặc lỗi client (400/401/403/404).
        - Toàn bộ log lỗi ghi ra sys.stderr (đảm bảo stdout sạch cho MCP stdio).
        """
        target_model = model or self.default_model
        kwargs: dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "timeout": timeout,
        }
        if tools:
            kwargs["tools"] = tools

        for attempt in range(max_retries + 1):
            try:
                response = self.groq.chat.completions.create(**kwargs)
                return response

            except APIStatusError as e:
                # 400/401/403/404: Lỗi client/xác thực/model không tồn tại -> ngắt ngay lập tức, không retry
                if e.status_code in (400, 401, 403, 404):
                    print(
                        f"[CRITICAL HTTP {e.status_code}] Lỗi yêu cầu hoặc xác thực: {e.message}. Không retry.",
                        file=sys.stderr,
                    )
                    raise e
                print(
                    f"[HTTP {e.status_code}] Groq API lỗi tạm thời (lần thử {attempt + 1}/{max_retries + 1}): {e.message}",
                    file=sys.stderr,
                )

            except (APIConnectionError, TimeoutError) as e:
                print(
                    f"[Network/Timeout Error] Lỗi kết nối Groq (lần thử {attempt + 1}/{max_retries + 1}): {str(e)}",
                    file=sys.stderr,
                )

            if attempt >= max_retries:
                err_msg = f"[FAILED] Gọi Groq chat thất bại sau {max_retries} lần retry."
                print(err_msg, file=sys.stderr)
                raise RuntimeError(err_msg)

            sleep_time = backoff_factor ** (attempt + 1)
            print(f"[Retry] Đang chờ {sleep_time:.2f}s trước khi thử lại...", file=sys.stderr)
            time.sleep(sleep_time)

    def embed(self, texts: list[str], model: str = "jina-embeddings-v3", task: str = "retrieval.passage") -> list[list[float]]:
        if not texts:
            return []
        resp = _jina_embeddings(input_data=texts, model=model, api_key=self.jina_api_key, task=task)
        return [item.embedding for item in resp.data]
