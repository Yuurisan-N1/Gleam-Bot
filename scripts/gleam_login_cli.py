import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gleam_mcp import browser as br
from utils.banner import show_banner

show_banner("Gleam MCP")

url = sys.argv[1] if len(sys.argv) > 1 else ""
if not url or "gleam.io/" not in url:
    sys.stderr.write("usage: gleam_login_cli.py https://gleam.io/<key>/<slug>\n")
    sys.exit(2)

shot = os.environ.get("GLEAM_SHOT") or "/tmp/gleam_login.png"
log = os.environ.get("GLEAM_LOG") or "/tmp/gleam_login.log"
res = br.gleam_login(url, screenshot=shot, log_path=log)
res.pop("injected", None)
res.pop("cookie_names", None)
print(json.dumps(res, ensure_ascii=False, indent=2))
