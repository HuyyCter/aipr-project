"""Vòng lặp Agent (Agent Loop) — ReAct & Tool-calling.

Nhiệm vụ:
- Nhận câu hỏi, khởi tạo hội thoại kèm system prompt.
- Lấy danh sách tool động từ MCP Client.
- Lặp tối đa MAX_STEPS:
    + Gửi hội thoại và tool schema tới LLMClient.
    + Ghi log từng bước (llm_call kèm token usage).
    + Nếu LLM trả lời trực tiếp -> Ghi log final_answer và trả kết quả.
    + Nếu LLM gọi tool -> Parse tham số an toàn, ghi log tool_call,
      gọi thực thi qua mcp_client.call(), ghi log tool_result và đưa vào hội thoại.
- Nếu vượt quá số bước cho phép: Ghi log error và trả về thông báo.
"""

import json
from pathlib import Path
from typing import Any, Optional

from aipr_project.agent import mcp_client
from aipr_project.agent.logger import generate_run_id, log_step
from aipr_project.common.llm_client import LLMClient

MAX_STEPS = 6
PROMPT_FILE = Path(__file__).resolve().parents[3] / "prompts" / "system_agent.txt"


def load_prompt(file_path=PROMPT_FILE) -> str:
    """Đọc system prompt từ file txt bên ngoài."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def convert_tools(mcp_tools: list[Any]) -> list[dict]:
    """Chuyển đổi danh sách Tool từ MCP sang định dạng function calling của LLM."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.input_schema or {"type": "object", "properties": {}},
            },
        }
        for t in mcp_tools
    ]


async def run_agent(
    question: str,
    session: Any,
    history: Optional[list[dict]] = None,
    max_steps: int = MAX_STEPS,
    run_id: Optional[str] = None,
    question_id: str = "interactive_0",
) -> str:
    """Vòng lặp chính điều phối Agent nhận câu hỏi, gọi LLM và thực thi tool qua MCP."""
    # Bước 1: Khởi tạo run_id và chỉ số step_index
    run_id = run_id or generate_run_id()
    step_index = 0

    # Bước 2: Chuẩn bị messages (system prompt + history + question)
    system_prompt = load_prompt()
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    # Bước 3: Khởi tạo LLMClient và lấy tool schema từ MCP Client
    client = LLMClient()
    mcp_tools = await mcp_client.discover(session)
    tools = convert_tools(mcp_tools)

    for step in range(1, max_steps + 1):
        response = client.chat(messages=messages, tools=tools)

        usage = {
            "calls": 1,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
        }
        log_step(
            run_id=run_id,
            question_id=question_id,
            step_index=step_index,
            step_type="llm_call",
            usage=usage,
        )
        step_index += 1

        message = response.choices[0].message

        if not message.tool_calls:
            final_answer = message.content or "(the model returned no content)"
            log_step(
                run_id=run_id,
                question_id=question_id,
                step_index=step_index,
                step_type="final_answer",
                result=final_answer,
            )
            return final_answer

        messages.append(message)

        for tc in message.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception as exc:
                args = {}
                result = f"Error: không parse được tham số: {exc}"
                log_step(
                    run_id=run_id,
                    question_id=question_id,
                    step_index=step_index,
                    step_type="error",
                    tool_name=name,
                    result=result,
                )
                step_index += 1
            else:
                log_step(
                    run_id=run_id,
                    question_id=question_id,
                    step_index=step_index,
                    step_type="tool_call",
                    tool_name=name,
                    args=args,
                )
                step_index += 1

                result = await mcp_client.call(session, name, args)

                log_step(
                    run_id=run_id,
                    question_id=question_id,
                    step_index=step_index,
                    step_type="tool_result",
                    tool_name=name,
                    result=result,
                )
                step_index += 1

            print(f"step {step}: {name}({args}) -> {result}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    overstep_msg = "Đã vượt quá số bước xử lý cho phép."
    log_step(
        run_id=run_id,
        question_id=question_id,
        step_index=step_index,
        step_type="error",
        result=overstep_msg,
    )
    return overstep_msg