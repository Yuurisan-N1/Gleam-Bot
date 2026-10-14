import json
import os
import re
import sys
import time

from mcp.server.mcpserver import MCPServer

from . import actions as xact_plan
from . import keyspec
from . import browser as bsrc
from . import cookies as ck
from . import entry as en
from .envstore import EnvStore
from .parse import parse_campaign, entry_methods, campaign_key
from .resolver import resolve_campaign
from .sources import gleam as gsrc
from .sources import x as xsrc
from .sources import xact
from .transport import Transport, load_proxies

mcp = MCPServer("gleam-mcp")

_STORE = None
_TR = None


def _say(msg):
    sys.stderr.write("[gleam-mcp] %s\n" % msg)
    sys.stderr.flush()


def store():
    global _STORE
    if _STORE is None:
        _STORE = EnvStore()
        _say("env=%s keys=%d" % (_STORE.path, len(_STORE.data)))
    return _STORE


def transport():
    global _TR
    if _TR is None:
        _TR = Transport(log=_say)
        _say("transport impersonate=%s proxies=%d retry=%d"
             % (_TR.impersonate, len(_TR.proxies), _TR.retry))
    return _TR


def _fmt_ts(ts):
    if not ts:
        return None
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(int(ts))) + "Z"


def _fmt_left(sec):
    if sec is None:
        return None
    sec = int(sec)
    d, rem = divmod(max(sec, 0), 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    return "%dd %dh %dm" % (d, h, m)


@mcp.tool(description="Fetch and parse one gleam.io campaign. Input: full URL (gleam.io/<key>/<slug>) or key+slug.")
def gleam_get_campaign(campaign: str, slug: str = "") -> str:
    key, url_slug = gsrc.normalize_key(campaign)
    if not key:
        return json.dumps({"ok": False, "error": "unrecognized gleam key/URL"}, ensure_ascii=False)
    res = gsrc.fetch_campaign(key, slug or url_slug, transport=transport())
    if not res.get("ok"):
        return json.dumps(res, ensure_ascii=False, indent=2)
    types = gsrc.list_entry_types(res)
    out = {
        "ok": True,
        "key": res["key"],
        "name": res["name"],
        "url": res["url"],
        "http": res["status"],
        "attempts": res["attempts"],
        "proxy_used": res["proxy_used"],
        "live": gsrc.is_live(res["_campaign"]),
        "finished": res["finished"],
        "starts_at": _fmt_ts(res["starts_at"]),
        "ends_at": _fmt_ts(res["ends_at"]),
        "time_left": _fmt_left(gsrc.time_left(res["_campaign"])),
        "time_zone": res["time_zone"],
        "language": res["language"],
        "captcha": {"turnstile": res["use_turnstile"], "hcaptcha": res["use_hcaptcha"]},
        "login_providers": res["login_providers"],
        "requires_contact_info": res["requires_contact_info"],
        "incentive": res["incentive"],
        "n_methods": len(res["entry_methods"]),
        "entry_types": {k: v for k, v in sorted(types.items(), key=lambda kv: -kv[1]["worth"])},
    }
    return json.dumps(out, ensure_ascii=False, indent=2)


@mcp.tool(description="Entry plan: map every entry_method to its .env key, value and status.\n\n    Core tool: answers 'which .env data does this campaign need'.\n    ")
def gleam_entry_plan(campaign: str, account_index: int = 0, slug: str = "") -> str:
    key, url_slug = gsrc.normalize_key(campaign)
    if not key:
        return json.dumps({"ok": False, "error": "unrecognized gleam key/URL"}, ensure_ascii=False)
    res = gsrc.fetch_campaign(key, slug or url_slug, transport=transport())
    if not res.get("ok"):
        return json.dumps(res, ensure_ascii=False, indent=2)
    st = store()
    if account_index:
        st = EnvStore(st.path, index=account_index)
    rep = resolve_campaign(res["_campaign"], st)
    rep["ok"] = True
    rep["campaign_name"] = res["name"]
    rep["url"] = res["url"]
    rep["live"] = gsrc.is_live(res["_campaign"])
    rep["time_left"] = _fmt_left(gsrc.time_left(res["_campaign"]))
    rep["account_index"] = account_index
    rep["env_file"] = st.path
    rep["plan"] = [
        {
            "entry_type": r["entry_type"],
            "worth": r["worth"],
            "mandatory": r["mandatory"],
            "status": r["status"],
            "field": r["field"],
            "key": r["key"],
            "value": r["value"],
            "label": r["label"],
            "chain": r["chain"],
            "note": r["note"],
        }
        for r in rep.pop("entries")
    ]
    return json.dumps(rep, ensure_ascii=False, indent=2)


@mcp.tool(description="Connect an X account to one gleam campaign (OAuth \"Login with Twitter\").\n\n    This is the ONLY browser step: click Login with Twitter then authorize.\n    The resulting gleam cookie is saved to session/gleam_cookie.json and reused by\n    every HTTP tool below. Once per account is enough.\n\n    The gleam cookie IS the contestant identity (including entry history). If the\n    current session already has X linked, this tool refuses to run so history is not\n    lost. force=True creates a fresh session (new contestant, old entries are gone).\n    ")
def gleam_login(campaign: str, slug: str = "", screenshot: str = "", force: bool = False) -> str:
    key, url_slug = gsrc.normalize_key(campaign)
    if not key:
        return json.dumps({"ok": False, "error": "unrecognized gleam key/URL"}, ensure_ascii=False)
    s = slug or url_slug
    url = "https://gleam.io/%s/%s" % (key, s) if s else "https://gleam.io/%s" % key
    res = bsrc.gleam_login(url, screenshot=screenshot or None, force=force)
    res.pop("injected", None)
    res.pop("cookie_names", None)
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool(description="Contestant status plus every entry_method, over plain HTTP (no browser).\n\n    Answers: which X account is linked, which entries are done or pending, and\n    which .env key each method will use.\n    ")
def gleam_state(campaign: str, slug: str = "") -> str:
    key, url_slug = gsrc.normalize_key(campaign)
    if not key:
        return json.dumps({"ok": False, "error": "unrecognized gleam key/URL"}, ensure_ascii=False)
    try:
        h = en.GleamHTTP(log=_say)
    except RuntimeError as exc:
        return json.dumps({"ok": False, "error": str(exc),
                           "hint": "run gleam_login for this campaign first"},
                          ensure_ascii=False, indent=2)
    st = h.state(key, slug or url_slug, store=store())
    st["env_file"] = store().path
    return json.dumps(st, ensure_ascii=False, indent=2)


@mcp.tool(description="Take entries over plain HTTP (PATCH /queue-entry then poll /access-entry).\n\n    Empty entry_method_id means every pending method, in mandatory order.\n    dry_run True (default) only reports the plan and sends nothing.\n    auto True performs the required X action (follow/like/retweet/reply/post) first\n    and submits the resulting link for submit_url methods.\n    ")
def gleam_enter(campaign: str, entry_method_id: str = "", slug: str = "", dry_run: bool = True,
                auto: bool = True) -> str:
    key, url_slug = gsrc.normalize_key(campaign)
    if not key:
        return json.dumps({"ok": False, "error": "unrecognized gleam key/URL"}, ensure_ascii=False)
    try:
        h = en.GleamHTTP(log=_say)
    except RuntimeError as exc:
        return json.dumps({"ok": False, "error": str(exc),
                           "hint": "run gleam_login first"}, ensure_ascii=False, indent=2)
    only = [entry_method_id] if entry_method_id else None
    res = h.run(key, slug or url_slug, store=store(), only=only, dry_run=dry_run, log=_say,
                auto=auto)
    res["dry_run"] = dry_run
    return json.dumps(res, ensure_ascii=False, indent=2)


@mcp.tool(description="Show which X action (follow/like/retweet/reply/post) each gleam entry_method needs.\n\n    Derived from the live campaign, so it follows whatever the event asks for.\n    ")
def x_auto_plan(campaign: str, slug: str = "") -> str:
    key, url_slug = gsrc.normalize_key(campaign)
    if not key:
        return json.dumps({"ok": False, "error": "unrecognized gleam key/URL"}, ensure_ascii=False)
    res = gsrc.fetch_campaign(key, slug or url_slug, transport=transport())
    if not res.get("ok"):
        return json.dumps(res, ensure_ascii=False, indent=2)
    rows = xact_plan.plans(res["_campaign"], store(), key)
    return json.dumps({
        "ok": True,
        "campaign": res["name"],
        "key": key,
        "x_creds": xact.status().get("creds"),
        "handle": xact.status().get("handle"),
        "n_actions": sum(1 for r in rows if r.get("action")),
        "plan": rows,
    }, ensure_ascii=False, indent=2)


@mcp.tool(description="Perform the X actions a campaign asks for, without touching gleam entries.\n\n    Useful to pre-do follow/like/retweet/reply, then run gleam_enter.\n    ")
def x_auto_run(campaign: str, entry_method_id: str = "", slug: str = "") -> str:
    key, url_slug = gsrc.normalize_key(campaign)
    if not key:
        return json.dumps({"ok": False, "error": "unrecognized gleam key/URL"}, ensure_ascii=False)
    res = gsrc.fetch_campaign(key, slug or url_slug, transport=transport())
    if not res.get("ok"):
        return json.dumps(res, ensure_ascii=False, indent=2)
    only = [entry_method_id] if entry_method_id else None
    rows = xact_plan.run_campaign(res["_campaign"], store(), key, log=_say, only=only)
    return json.dumps({"ok": all(r.get("ok") or r.get("skipped") for r in rows),
                       "campaign": res["name"], "key": key, "results": rows},
                      ensure_ascii=False, indent=2)


@mcp.tool(description="Re-read X query ids from the live web bundle (they rotate over time).")
def x_ops_refresh() -> str:
    return json.dumps(xact.discover_ops(), ensure_ascii=False, indent=2)


@mcp.tool(description="Show the cached X operation ids and whether they drifted from the builtin map.")
def x_ops_report() -> str:
    return json.dumps(xact.ops_report(), ensure_ascii=False, indent=2)


@mcp.tool(description="Do one X action with the saved cookie: follow, unfollow, like, unlike, retweet, unretweet, post, reply.\n\n    target = handle for follow/unfollow, tweet id or URL for like/retweet/reply.\n    ")
def x_action(action: str, target: str = "", text: str = "") -> str:
    act = (action or "").strip().lower()
    tid = None
    m = None
    if target:
        m = re.search(r"(\d{6,25})", target)
        tid = m.group(1) if m else target.lstrip("@").strip()
    if act == "follow":
        out = xact.follow(target)
    elif act == "unfollow":
        out = xact.unfollow(target)
    elif act == "like":
        out = xact.like(tid)
    elif act == "unlike":
        out = xact.unlike(tid)
    elif act == "retweet":
        out = xact.retweet(tid)
    elif act == "unretweet":
        out = xact.unretweet(tid)
    elif act == "post":
        out = xact.post(text)
    elif act == "reply":
        out = xact.reply(tid, text)
    elif act in ("state", "verify"):
        out = xact.verify(tid)
    else:
        out = {"ok": False, "error": "unknown action %s" % action,
               "known": ["follow", "unfollow", "like", "unlike", "retweet", "unretweet",
                         "post", "reply", "verify"]}
    return json.dumps(out, ensure_ascii=False, indent=2)


@mcp.tool(description="Parse a campaign from a saved HTML file (offline, no network).")
def gleam_parse_local(path: str) -> str:
    try:
        page = open(path, encoding="utf-8", errors="replace").read()
    except OSError as exc:
        return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
    camp = parse_campaign(page)
    if not camp:
        return json.dumps({"ok": False, "error": "initCampaign not found"}, ensure_ascii=False)
    return json.dumps({
        "ok": True,
        "key": campaign_key(camp),
        "name": camp.get("name"),
        "n_methods": len(entry_methods(camp)),
        "entry_types": sorted({e.get("entry_type") for e in entry_methods(camp)}),
    }, ensure_ascii=False, indent=2)


@mcp.tool(description="Inventory .env and validate every value against gleam real regexes.")
def gleam_env_audit() -> str:
    st = store()
    return json.dumps({
        "env_file": st.path,
        "exists": bool(st.data),
        "n_keys": len(st.data),
        "filled": len([k for k, v in st.data.items() if v]),
        "inventory": st.inventory(),
        "problems": st.audit(),
        "proxies_loaded": len(load_proxies()),
    }, ensure_ascii=False, indent=2)


@mcp.tool(description="List entry_type values that already map to an .env key (internal catalog).")
def gleam_supported_types() -> str:
    return json.dumps({
        "entry_type_map": keyspec.ENTRY_TYPE_MAP,
        "wallet_chains": keyspec.WALLET_CHAIN,
        "exchange_uid_keys": ["%s_UID" % e for e in keyspec.EXCHANGES],
        "intent_rules": [{"pattern": p, "field": f} for p, f in keyspec.INTENT_RULES],
    }, ensure_ascii=False, indent=2)


@mcp.tool(description="Check whether X credentials (from x.json or .env) are still valid.")
def x_status() -> str:
    return json.dumps(xsrc.status(), ensure_ascii=False, indent=2)


@mcp.tool(description="Look up a public X profile using cookies (x.json / .env).")
def x_user_lookup(screen_name: str) -> str:
    return json.dumps(xsrc.user_lookup(screen_name), ensure_ascii=False, indent=2)


@mcp.tool(description="Status of *_cookie.json session files: exists, format, count, session cookies.\n\n    Empty service means every service (gleam, x, threads, instagram, discord, tiktok,\n    youtube, twitch, reddit, telegram, google, custom).\n    ")
def cookie_status(service: str = "") -> str:
    if service:
        return json.dumps(ck.status(service), ensure_ascii=False, indent=2)
    return json.dumps({"cookie_dir": ck.cookie_dir(), "services": ck.status_all()},
                      ensure_ascii=False, indent=2)


@mcp.tool(description="Open a TEMPORARY browser with a cookie file to check the session is alive.\n\n    Cookies are injected in memory and the browser closes after the check; nothing\n    is persisted.\n    ")
def cookie_connect(service: str, url: str = "", screenshot: str = "") -> str:
    return json.dumps(bsrc.connect(service, url=url or None, screenshot=screenshot or None),
                      ensure_ascii=False, indent=2)


@mcp.tool(description="Follow an X account with a cookie session via a temporary browser. target = handle without @.")
def x_follow(target: str, screenshot: str = "") -> str:
    return json.dumps(bsrc.follow(target, screenshot=screenshot or None), ensure_ascii=False, indent=2)


@mcp.tool(description="Auto browser engine (camoufox/chromium), headless flag, proxy, cookie_dir.")
def browser_info() -> str:
    return json.dumps(bsrc.available(), ensure_ascii=False, indent=2)


PROJECT = "Gleam MCP"


def _banner():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        from utils.banner import show_banner
    except Exception:
        return
    sys.stdout.flush()
    saved = os.dup(1)
    try:
        os.dup2(2, 1)
        show_banner(PROJECT)
        sys.stdout.flush()
    finally:
        os.dup2(saved, 1)
        os.close(saved)


def main():
    _say("starting stdio server")
    _banner()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
