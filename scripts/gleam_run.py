import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gleam_mcp import entry as en
from utils.banner import show_banner

show_banner("Gleam MCP")

KEY, SLUG = "oNewO", "kucoin-x-tina-x-space"
DRY = (os.environ.get("DRY") or "1") == "1"

h = en.GleamHTTP(log=lambda m: sys.stderr.write("[http] %s\n" % m))
st = h.state(KEY, SLUG)
print("campaign:", st["campaign"], "| contestant:", st["contestant"])
print("entries_total:", st["entries_total"], "| entered:", st["n_entered"], "/", st["n_methods"])
for m in st["methods"]:
    print("  %-11s %-16s done=%-5s cnt=%s worth=%s field=%-16s env=%s" % (
        m["entry_method_id"], m["entry_type"], m["entered"], m["count"], m["worth"],
        m["field"], m.get("env_ready")))

print("\n=== run dry_run=%s ===" % DRY)
res = h.run(KEY, SLUG, dry_run=DRY, log=lambda m: sys.stderr.write("[run] %s\n" % m), max_wait=40)
print(json.dumps(res, ensure_ascii=False, indent=2)[:2500])

if not DRY:
    st2 = h.state(KEY, SLUG)
    print("\nSETELAH: entries_total=%s entered=%s/%s" % (st2["entries_total"], st2["n_entered"], st2["n_methods"]))
    for m in st2["methods"]:
        print("  %-11s done=%-5s cnt=%s" % (m["entry_method_id"], m["entered"], m["count"]))
