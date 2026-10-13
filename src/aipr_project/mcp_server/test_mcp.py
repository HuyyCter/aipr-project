import asyncio
import re
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SERVER = PROJECT_ROOT / "src" / "aipr_project" / "mcp_server" / "server.py"


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()

            tools = (await s.list_tools()).tools
            print(f"Discovered {len(tools)} tools: {[t.name for t in tools]}")

            async def call(name: str, args: dict) -> str:
                res = await s.call_tool(name, args)
                text = res.content[0].text
                print(f"\n>>> {name}({args})\n{text[:400]}")
                return text

            # tra cứu: trong corpus / ngoài corpus
            await call(
                "search_regulations",
                {"query": "mục chấp hành nội quy tối đa bao nhiêu điểm"},
            )
            await call("search_regulations", {"query": "học bổng khuyến khích học tập"})

            # get_document: id có thật (sửa theo kết quả search) / id sai
            await call("get_document", {"doc_id": "DOC0001"})
            await call("get_document", {"doc_id": "XXX"})

            # tính điểm: đủ 5 mục / thiếu mục
            await call(
                "calculate_conduct_score",
                {
                    "category_scores": {
                        "hoc_tap": 18,
                        "chap_hanh_noi_quy": 22,
                        "chinh_tri_xa_hoi": 15,
                        "pham_chat_cong_dan": 20,
                        "cong_tac_lop_doan_hoi": 8,
                    }
                },
            )
            await call("calculate_conduct_score", {"category_scores": {"hoc_tap": 18}})

            # ghi -> verify
            out = await call(
                "submit_appeal",
                {
                    "student_id": "SV001",
                    "reason": "thiếu minh chứng",
                    "category": "chinh_tri_xa_hoi",
                },
            )
            m = re.search(r"#(\w+)", out)
            if m:
                await call("get_appeal_by_id", {"appeal_id": m.group(1)})
            await call("get_appeal_by_id", {"appeal_id": "khongtontai"})
            await call("list_appeals", {"student_id": "SV001"})


asyncio.run(main())
