"""Five business tools on one loopback MCP server; no approval authority is exposed."""
from urllib.parse import urlsplit
import os

import httpx
from mcp.server import MCPServer

from backend.common.config import env, settings
from backend.common.log import request_id, span
from backend.common.response import reply

mcp = MCPServer("Equipment assistant", instructions="조회·제안·결정 기록만 제공합니다. 사람 승인 기능은 제공하지 않습니다.")


async def call(path: str, payload: dict, rid: str, name: str):
    token = request_id.set(rid)
    try:
        with span("tools", "tools.call."+name, "mcp_server/server.py:call"):
            async with httpx.AsyncClient(timeout=120) as client:
                base=os.getenv("BACKEND_URL",settings()["service"]["backend"])
                if os.getenv("PORT"):
                    base="http://127.0.0.1:"+str(int(os.environ["PORT"]))
                response = await client.post(base+path, json=payload,
                    headers={"Authorization":"Bearer "+env("SERVICE_TOKEN"),"X-Request-ID":rid})
            content = response.json()
            if not isinstance(content,dict) or "status" not in content:
                response.raise_for_status()
                raise ValueError("API 응답 형식이 다릅니다")
            return content
    except httpx.HTTPError as exc:
        return reply(rid,status="failed",reason="도구 연결 실패: "+type(exc).__name__).model_dump()
    finally:
        request_id.reset(token)


@mcp.tool()
async def query_events(profile: str, source_id: str, lot_id: str | None, rid: str) -> dict:
    """Retrieve recorded events. Empty results mean none, not a healthy machine."""
    return await call("/api/detect/events",{"profile":profile,"source_id":source_id,"lot_id":lot_id},rid,"query_events")


@mcp.tool()
async def search_docs(profile: str, question: str, rid: str) -> dict:
    """Retrieve current document evidence without generating an answer."""
    return await call("/api/rag/search",{"profile":profile,"question":question},rid,"search_docs")


@mcp.tool()
async def graph_path(start: str, end: str, rid: str) -> dict:
    """Find bounded relationship evidence between two known entity identifiers."""
    return await call("/api/ontology/path",{"start":start,"end":end},rid,"graph_path")


@mcp.tool()
async def propose_action(rule_id: str, event_ids: list[str], new_width: float, rationale: str, rid: str) -> dict:
    """Create a guarded proposal that remains pending until a human decides."""
    return await call("/api/process/propose",{"rule_id":rule_id,"event_ids":event_ids,
        "new_width":new_width,"rationale":rationale},rid,"propose_action")


@mcp.tool()
async def record_decision(identity: str, version: int, payload_hash: str, rid: str) -> dict:
    """Record exactly the proposal already approved on the server, then update its rule."""
    return await call("/api/process/record",{"identity":identity,"version":version,"payload_hash":payload_hash},rid,"record_decision")


if __name__ == "__main__":
    endpoint = urlsplit(settings()["service"]["mcp"])
    if endpoint.hostname not in {"localhost","127.0.0.1"}:
        raise ValueError("MCP 서버는 이 구성에서 로컬 연결만 허용합니다")
    mcp.run(transport="streamable-http",host="127.0.0.1",port=endpoint.port or 8001,
            streamable_http_path=endpoint.path or "/mcp")
