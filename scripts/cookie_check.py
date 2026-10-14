import json
import os
import sys
import tempfile

from gleam_mcp import cookies as ck

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.banner import show_banner

show_banner("Gleam MCP")

CASES = {
    "x_cookie.json": json.dumps([
        {"name": "auth_token", "value": "ATOKEN123"},
        {"name": "ct0", "value": "CTOKEN456"},
        {"name": "twid", "value": "u%3D777"},
    ]),
    "threads_cookie.json": json.dumps({
        "cookies": [
            {"name": "sessionid", "value": "SID789", "domain": ".threads.net", "path": "/"},
            {"name": "ds_user_id", "value": "555", "domain": ".threads.net", "path": "/"},
        ],
        "origins": [],
    }),
    "reddit_cookie.json": json.dumps({"reddit_session": "RS1", "token_v2": "TV2"}),
    "twitch_cookie.json": "auth-token=TWTOK; other=1",
    "custom_cookie.json": json.dumps([{"name": "sid", "value": "SECRET123"}]),
}

EXPECT = {
    "x": ("list", 3, True, "u%3D777"),
    "threads": ("storage_state", 2, True, None),
    "reddit": ("map", 2, True, None),
    "twitch": ("header", 2, True, None),
    "custom": ("list", 1, True, None),
}

out = {}
with tempfile.TemporaryDirectory() as tmp:
    for name, body in CASES.items():
        with open(os.path.join(tmp, name), "w", encoding="utf-8") as fh:
            fh.write(body)
    os.environ["COOKIE_DIR"] = tmp
    os.environ["CUSTOM_COOKIE_DOMAINS"] = ".paidadz.xyz"
    os.environ["CUSTOM_COOKIE_URL"] = "https://paidadz.xyz/"
    os.environ["CUSTOM_COOKIE_SESSION"] = "sid"
    os.environ.pop("X_AUTH_TOKEN", None)
    os.environ.pop("X_CT0", None)
    os.environ.pop("X_COOKIE_FILE", None)

    fails = []
    for svc, (fmt, count, has_sess, handle) in EXPECT.items():
        st = ck.status(svc)
        ok = (st.get("format") == fmt and st.get("count") == count
              and st.get("has_session") == has_sess)
        h = ck.handle(svc)
        if handle is not None:
            ok = ok and h == handle
        if not ok:
            fails.append(svc)
        out[svc] = {
            "format": st.get("format"), "count": st.get("count"),
            "has_session": st.get("has_session"), "handle": h,
            "domains": st.get("domains"), "file": os.path.basename(st.get("file") or ""),
            "verdict": "OK" if ok else "GAGAL",
        }

    hdr, res = ck.header("x")
    out["header_x"] = hdr
    out["header_x_ok"] = hdr == "auth_token=ATOKEN123; ct0=CTOKEN456; twid=u%3D777"

    doms = {r["name"]: r["domain"] for r in ck.load("custom")["cookies"]}
    out["custom_domain_injected"] = doms

    missing = ck.status("discord")
    out["missing_service"] = {"ok": missing.get("ok"), "file_exists": missing.get("file_exists"),
                              "reason": missing.get("reason")}

print(json.dumps(out, ensure_ascii=False, indent=2))
print("\nSUMMARY: %d/%d formats valid; X header %s" % (
    len(EXPECT) - len(fails), len(EXPECT), "OK" if out["header_x_ok"] else "GAGAL"))
if fails:
    print("GAGAL: %s" % ", ".join(fails))
    sys.exit(1)
