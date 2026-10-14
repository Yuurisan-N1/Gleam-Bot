import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.banner import show_banner

show_banner("Gleam MCP")

PY = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", ".venv", "bin", "python")


async def main():
    params = StdioServerParameters(
        command=PY,
        args=["-m", "gleam_mcp"],
        env={**os.environ, "PYTHONPATH": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            si = getattr(init, "server_info", None) or getattr(init, "serverInfo", None)
            print("server:", si.name, si.version)
            tools = await session.list_tools()
            print("tools :", len(tools.tools))
            for t in tools.tools:
                print("   -", t.name, "|", (t.description or "").split("\n")[0][:60])
            print()
            for name, args in [
                ("gleam_env_audit", {}),
                ("gleam_parse_local", {"path": "/tmp/gleam/tina.html"}),
                ("gleam_supported_types", {}),
                ("browser_info", {}),
                ("cookie_status", {}),
                ("cookie_status", {"service": "x"}),
            ]:
                r = await session.call_tool(name, args)
                txt = r.content[0].text
                try:
                    d = json.loads(txt)
                    if name == "gleam_env_audit":
                        print("%s -> keys=%s filled=%s problems=%s proxies=%s"
                              % (name, d.get("n_keys"), d.get("filled"), len(d.get("problems") or []), d.get("proxies_loaded")))
                    elif name == "gleam_parse_local":
                        print("%s -> %s" % (name, json.dumps(d, ensure_ascii=False)))
                    elif name == "gleam_supported_types":
                        print("%s -> entry_type_map=%d chains=%d"
                              % (name, len(d["entry_type_map"]), len(d["wallet_chains"])))
                    elif name == "browser_info":
                        print("%s -> engine=%s headless=%s camoufox_pkg=%s cache=%s chromium=%s"
                              % (name, d.get("engine"), d.get("headless"), d.get("camoufox_pkg"),
                                 d.get("camoufox_cache"), bool(d.get("chromium_binary"))))
                    elif name == "cookie_status" and "services" in d:
                        known = {k: v for k, v in d["services"].items() if v.get("file_exists")}
                        print("%s -> dir=%s services=%d with_file=%s"
                              % (name, d.get("cookie_dir"), len(d["services"]), sorted(known.keys())))
                    elif name == "cookie_status":
                        print("%s -> %s ok=%s file=%s format=%s needs=%s"
                              % (name, d.get("service"), d.get("ok"), d.get("file_exists"),
                                 d.get("format"), d.get("needs")))
                except Exception:
                    print("%s -> %s" % (name, txt[:200]))


asyncio.run(main())
