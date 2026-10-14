import re

from ..parse import parse_campaign, entry_methods, campaign_key
from ..transport import Transport

BASE = "https://gleam.io"


def campaign_url(key, slug=None):
    if slug:
        return "%s/%s/%s" % (BASE, key, slug)
    return "%s/%s" % (BASE, key)


def fetch_campaign(key, slug=None, transport=None, store=None):
    tr = transport or Transport()
    url = campaign_url(key, slug)
    res = tr.get(url)
    if not res.get("ok"):
        err = res.get("error") or "not a campaign page (initCampaign missing)"
        if res.get("status") == 404 and not slug:
            err = ("404 without slug. bare gleam.io/<key> is invalid - "
                   "send the full URL: https://gleam.io/%s/<slug>" % key)
        return {
            "ok": False,
            "key": key,
            "url": url,
            "status": res.get("status"),
            "error": err,
            "attempts": res.get("attempt"),
            "proxy_used": bool(res.get("proxy")),
        }
    camp = parse_campaign(res["body"])
    if not camp:
        return {"ok": False, "key": key, "url": url, "status": res["status"], "error": "parse failed"}
    out = {
        "ok": True,
        "key": campaign_key(camp),
        "url": url,
        "status": res["status"],
        "attempts": res["attempt"],
        "proxy_used": bool(res["proxy"]),
        "name": camp.get("name"),
        "starts_at": camp.get("starts_at"),
        "ends_at": camp.get("ends_at"),
        "finished": camp.get("finished"),
        "paused": camp.get("paused"),
        "language": camp.get("language"),
        "time_zone": camp.get("time_zone"),
        "use_turnstile": camp.get("use_turnstile"),
        "use_hcaptcha": camp.get("use_hcaptcha"),
        "login_providers": camp.get("login_providers"),
        "requires_contact_info": camp.get("require_contact_info"),
        "contestant_details_groups": camp.get("contestant_details_groups"),
        "incentive": camp.get("incentive"),
        "entry_methods": entry_methods(camp),
        "_campaign": camp,
    }
    return out


def list_entry_types(campaign):
    seen = {}
    for e in campaign.get("entry_methods") or []:
        et = e.get("entry_type") or "?"
        seen.setdefault(et, {"n": 0, "worth": 0, "auth": 0, "api_denied": 0})
        row = seen[et]
        row["n"] += 1
        try:
            row["worth"] += float(e.get("worth") or 0)
        except (TypeError, ValueError):
            pass
        if e.get("requires_authentication"):
            row["auth"] += 1
        if e.get("api_denied"):
            row["api_denied"] += 1
    return seen


def time_left(campaign, now=None):
    import time as _t
    now = now or _t.time()
    ends = campaign.get("ends_at")
    if not ends:
        return None
    return int(ends - now)


def is_live(campaign, now=None):
    import time as _t
    now = now or _t.time()
    if campaign.get("finished"):
        return False
    if campaign.get("paused"):
        return False
    s, e = campaign.get("starts_at"), campaign.get("ends_at")
    if s and now < s:
        return False
    if e and now > e:
        return False
    return True


def normalize_key(text):
    t = (text or "").strip()
    m = re.search(r"gleam\.io/([A-Za-z0-9]+)(?:/([A-Za-z0-9\-_]+))?", t)
    if m:
        return m.group(1), m.group(2)
    m = re.match(r"^([A-Za-z0-9]{4,8})$", t)
    if m:
        return m.group(1), None
    return None, None
