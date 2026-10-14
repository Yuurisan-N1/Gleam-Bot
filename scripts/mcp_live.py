import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.banner import show_banner

show_banner("Gleam MCP")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PY = os.path.join(ROOT, ".venv", "bin", "python")
CAMPAIGN = sys.argv[1] if len(sys.argv) > 1 else "oNewO"


async def main():
    params = StdioServerParameters(
        command=PY,
        args=["-m", "gleam_mcp"],
        env={**os.environ, "PYTHONPATH": os.path.join(ROOT, "src"), "GLEAM_ENV_FILE": os.path.join(ROOT, ".env")},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            r = await session.call_tool("gleam_get_campaign", {"campaign": CAMPAIGN})
            d = json.loads(r.content[0].text)
            if not d.get("ok"):
                print("GAGAL:", json.dumps(d, ensure_ascii=False))
                return
            print("LIVE OK  %s | %s" % (d["key"], d["name"]))
            print("  http=%s attempts=%s proxy=%s live=%s left=%s"
                  % (d["http"], d["attempts"], d["proxy_used"], d["live"], d["time_left"]))
            print("  captcha=%s methods=%d" % (d["captcha"], d["n_methods"]))
            print("  entry_types:")
            for k, v in d["entry_types"].items():
                print("    %-22s n=%d worth=%s auth=%d api_denied=%d"
                      % (k, v["n"], v["worth"], v["auth"], v["api_denied"]))
            r2 = await session.call_tool("gleam_entry_plan", {"campaign": CAMPAIGN})
            p = json.loads(r2.content[0].text)
            print("  PLAN: ready=%d missing=%d auth_only=%d visit_only=%d"
                  % (p["ready"], p["missing"], p["auth_only"], p.get("visit_only", 0)))
            for e in p["plan"]:
                print("    [%-9s] %-16s -> %-24s %s"
                      % (e["status"], e["entry_type"], e["field"] or "-", e["value"] or ""))


asyncio.run(main())
