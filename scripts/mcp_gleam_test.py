import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.banner import show_banner

show_banner("Gleam MCP")

PY = os.path.join(os.path.dirname(__file__), "..", ".venv", "bin", "python")
CAMPAIGN = "https://gleam.io/oNewO/kucoin-x-tina-x-space"


async def main():
    params = StdioServerParameters(
        command=PY, args=["-m", "gleam_mcp"],
        env={**os.environ, "PYTHONPATH": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print("tools:", len(names))
            for t in tools.tools:
                print("   -", t.name)

            r = await session.call_tool("gleam_state", {"campaign": CAMPAIGN})
            d = json.loads(r.content[0].text)
            print("\n[gleam_state] ok=%s campaign=%s contestant=%s entries=%s/%s"
                  % (d.get("ok"), d.get("campaign"), d.get("contestant"),
                     d.get("entries_total"), d.get("n_methods")))
            for m in d.get("methods", []):
                print("   %-11s %-16s done=%-5s field=%-16s env=%s"
                      % (m["entry_method_id"], m["entry_type"], m["entered"],
                         m["field"], m.get("env_ready")))

            r = await session.call_tool("gleam_enter", {"campaign": CAMPAIGN, "dry_run": True})
            d = json.loads(r.content[0].text)
            print("\n[gleam_enter dry_run] ok=%s" % d.get("ok"))
            for x in d.get("results", []):
                print("   %-11s %s" % (x.get("entry_method_id"),
                                       str(x.get("skipped") or x.get("how") or "")[:60]))


asyncio.run(main())
