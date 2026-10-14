import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gleam_mcp import EnvStore, parse_campaign, resolve_campaign
from gleam_mcp.parse import entry_methods

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.banner import show_banner

show_banner("Gleam MCP")

HTML = {
    "qFECm": "/tmp/gleam/new_campaign.html",
    "oNewO": "/tmp/gleam/tina.html",
    "5rO8Z": "/tmp/gleam/xdp.html",
    "hLHUI": "/tmp/gleam/pnt.html",
}

env_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", ".env.demo")
store = EnvStore(env_path)

print("env file :", store.path, "| keys:", len(store.data))
print("terisi   :", len([k for k, v in store.data.items() if v]))
print()

for key, path in HTML.items():
    camp = parse_campaign(open(path, encoding="utf-8", errors="replace").read())
    if not camp:
        print("!! parse failed", key)
        continue
    rep = resolve_campaign(camp, store)
    print("=" * 78)
    print("%s | %s | %d method" % (key, rep["campaign"], len(rep["entries"])))
    print("ready=%d visit-only=%d auth-only=%d missing=%d no-data=%d | actionable=%d/%d"
          % (rep["ready"], rep["visit_only"], rep["auth_only"], rep["missing"],
             rep["no_data"], rep["actionable"], rep["n_methods"]))
    for r in rep["entries"]:
        val = r["value"]
        shown = (val[:14] + "..." + val[-6:]) if val and len(val) > 24 else (val or "-")
        print("  [%-9s] %-22s %-24s %-22s %s"
              % (r["status"], r["entry_type"], r["field"] or "-", r["key"] or "-", shown))
        if r["status"] in ("missing", "no-data", "auth-only") and r["note"]:
            print("              -> %s" % r["note"])
    if rep["need_keys"]:
        print("  BUTUH DI .env: %s" % ", ".join(rep["need_keys"]))
    print()
