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

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LOG_PATH = PROJECT_ROOT / "logs" / "api_log.jsonl"

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
                print(f"[ERROR HTTP {resp.status_code}] Sai JINA_API_KEY!", file=sys.stderr)
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

    def log_api_call(self, messages: list[dict], response: Any, fn: Optional[str | Path] = None) -> str:
        target_path = Path(fn) if fn else DEFAULT_LOG_PATH
        target_path.parent.mkdir(parents=True, exist_ok=True)

        log_entry = {
            "timestamp": getattr(response, "created", int(time.time())),
            "model": getattr(response, "model", self.default_model),
            "prompt": messages,
            "response": response.choices[0].message.content,
            "tool_calls": [
                {"name": tc.function.name, "arguments": tc.function.arguments}
                for tc in (response.choices[0].message.tool_calls or [])
            ] if hasattr(response.choices[0].message, "tool_calls") and response.choices[0].message.tool_calls else None,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "estimated_cost": estimate_cost(
                response.model, response.usage.prompt_tokens, response.usage.completion_tokens
            ),
            "finish_reason": response.choices[0].finish_reason,
        }
        with open(target_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        return str(target_path)

# === CHƯƠNG TRÌNH TEST TOÀN DIỆN CÁC HÀM TRONG LLM_CLIENT ===
if __name__ == "__main__":
    print("=== KIỂM THỬ TOÀN DIỆN LLM_CLIENT (EMBED, ESTIMATE_COST, CHAT, LOG_API_CALL) ===\n")
    client = LLMClient()

    # -------------------------------------------------------------
    # 1. Test hàm embed() (cả trường hợp bình thường và danh sách rỗng)
    # -------------------------------------------------------------
    print("1. Đang test embed()...")
    sample_texts = [
        "Quy chế đánh giá kết quả rèn luyện sinh viên",
        "Quy trình nộp đơn khiếu nại điểm rèn luyện",
    ]
    try:
        embeddings = client.embed(sample_texts)
        print(f" -> [OK] Embed thành công {len(embeddings)} câu.")
        print(f" -> Kích thước vector mỗi câu: {len(embeddings[0])} chiều.")
        print(f" -> 5 giá trị đầu vector 1: {embeddings[0][:5]}")

        # Edge case: danh sách rỗng
        empty_res = client.embed([])
        assert empty_res == [], "Embed danh sách rỗng phải trả về []"
        print(" -> [OK] Test trường hợp biên: embed([]) trả về [] thành công.")
    except Exception as e:
        print(f" -> [FAIL] Test embed() thất bại: {e}")

    print("\n" + "-" * 60 + "\n")

    # -------------------------------------------------------------
    # 2. Test hàm estimate_cost()
    # -------------------------------------------------------------
    print("2. Đang test hàm estimate_cost()...")
    try:
        sample_prompt_tokens = 1200
        sample_completion_tokens = 450
        cost = estimate_cost(DEFAULT_MODEL, sample_prompt_tokens, sample_completion_tokens)
        print(f" -> Model: {DEFAULT_MODEL}")
        print(f" -> Prompt tokens: {sample_prompt_tokens}, Completion tokens: {sample_completion_tokens}")
        print(f" -> [OK] Chi phí tính toán: ${cost:.6f}")
    except Exception as e:
        print(f" -> [FAIL] Test estimate_cost() thất bại: {e}")

    print("\n" + "-" * 60 + "\n")

    # -------------------------------------------------------------
    # 3. Test hàm chat() thông thường
    # -------------------------------------------------------------
    print(f"3. Đang test chat() thông thường với model '{DEFAULT_MODEL}'...")
    chat_messages = [
        {"role": "system", "content": "Bạn là trợ lý giải đáp ngắn gọn, súc tích."},
        {"role": "user", "content": "Chào bạn, hãy giới thiệu vai trò của bạn trong đúng 1 câu."},
    ]
    chat_response = None
    try:
        chat_response = client.chat(messages=chat_messages)
        content = chat_response.choices[0].message.content
        usage = chat_response.usage
        print(f" -> [OK] Trả lời: {content}")
        print(
            f" -> Usage: Prompt: {usage.prompt_tokens} tokens | "
            f"Completion: {usage.completion_tokens} tokens"
        )
    except Exception as e:
        print(f" -> [FAIL] Test chat() thất bại: {e}")

    print("\n" + "-" * 60 + "\n")

    # -------------------------------------------------------------
    # 4. Test hàm log_api_call()
    # -------------------------------------------------------------
    print("4. Đang test log_api_call()...")
    if chat_response:
        try:
            log_file_written = client.log_api_call(messages=chat_messages, response=chat_response)
            print(f" -> [OK] Đã ghi log vào file: {log_file_written}")
            assert os.path.exists(log_file_written), "File log không tồn tại trên ổ đĩa!"

            # Đọc lại dòng log cuối cùng để kiểm tra nội dung
            with open(log_file_written, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                last_line = json.loads(lines[-1])
            print(f" -> [OK] Đã xác minh dòng log vừa ghi:")
            print(f"    * Model: {last_line.get('model')}")
            print(f"    * Response: {last_line.get('response')[:50]}...")
            print(f"    * Estimated cost: ${last_line.get('estimated_cost'):.6f}")
        except Exception as e:
            print(f" -> [FAIL] Test log_api_call() thất bại: {e}")
    else:
        print(" -> [SKIP] Bỏ qua vì test chat() trước đó không có response.")

    print("\n" + "-" * 60 + "\n")

    # -------------------------------------------------------------
    # 5. Test hàm chat() với Tool Calling (Function Calling)
    # -------------------------------------------------------------
    print("5. Đang test chat() với Tool Calling...")
    dummy_tools = [
        {
            "type": "function",
            "function": {
                "name": "search_regulations",
                "description": "Tìm kiếm điều khoản trong quy định điểm rèn luyện.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Từ khóa hoặc câu hỏi cần tra cứu",
                        }
                    },
                    "required": ["query"],
                },
            },
        }
    ]
    tool_test_messages = [
        {"role": "user", "content": "Tìm giúp tôi quy định về điều 5 trong quy chế rèn luyện"}
    ]
    try:
        tool_response = client.chat(messages=tool_test_messages, tools=dummy_tools)
        msg = tool_response.choices[0].message
        if msg.tool_calls:
            print(" -> [OK] Model đã tự động kích hoạt Tool thành công!")
            for tc in msg.tool_calls:
                print(f"    * Tool gọi: {tc.function.name}")
                print(f"    * Tham số trích xuất: {tc.function.arguments}")
            # Ghi log luôn cho cuộc gọi tool
            client.log_api_call(messages=tool_test_messages, response=tool_response)
            print(" -> [OK] Đã ghi log thành công cuộc gọi Tool vào api_log.jsonl.")
        else:
            print(f" -> Model trả lời dạng text thông thường: {msg.content}")
    except Exception as e:
        print(f" -> [FAIL] Test tool calling thất bại: {e}")

    print("\n=== HOÀN THÀNH KIỂM THỬ TOÀN DIỆN LLM_CLIENT ===")