import json
import os
import re

SERVICES = {
    "gleam": {
        "file": "gleam_cookie.json",
        "domains": [".gleam.io"],
        "home": "https://gleam.io/",
        "session": ["_gleam_session"],
        "handle": "owner_token",
        "env": {},
    },
    "x": {
        "file": "x_cookie.json",
        "domains": [".x.com", ".twitter.com"],
        "home": "https://x.com/home",
        "session": ["auth_token", "ct0"],
        "handle": "twid",
        "env": {"auth_token": "X_AUTH_TOKEN", "ct0": "X_CT0"},
    },
    "threads": {
        "file": "threads_cookie.json",
        "domains": [".threads.net", ".threads.com"],
        "home": "https://www.threads.net/",
        "session": ["sessionid"],
        "handle": "ds_user_id",
        "env": {},
    },
    "instagram": {
        "file": "instagram_cookie.json",
        "domains": [".instagram.com"],
        "home": "https://www.instagram.com/",
        "session": ["sessionid"],
        "handle": "ds_user_id",
        "env": {},
    },
    "discord": {
        "file": "discord_cookie.json",
        "domains": [".discord.com"],
        "home": "https://discord.com/channels/@me",
        "session": ["token"],
        "handle": None,
        "env": {"token": "DISCORD_TOKEN"},
    },
    "tiktok": {
        "file": "tiktok_cookie.json",
        "domains": [".tiktok.com"],
        "home": "https://www.tiktok.com/foryou",
        "session": ["sessionid"],
        "handle": "uid_tt",
        "env": {},
    },
    "youtube": {
        "file": "youtube_cookie.json",
        "domains": [".youtube.com", ".google.com"],
        "home": "https://www.youtube.com/",
        "session": ["SID", "SAPISID", "__Secure-3PSID"],
        "handle": None,
        "env": {},
    },
    "twitch": {
        "file": "twitch_cookie.json",
        "domains": [".twitch.tv"],
        "home": "https://www.twitch.tv/",
        "session": ["auth-token"],
        "handle": None,
        "env": {},
    },
    "reddit": {
        "file": "reddit_cookie.json",
        "domains": [".reddit.com"],
        "home": "https://www.reddit.com/",
        "session": ["reddit_session", "token_v2"],
        "handle": None,
        "env": {},
    },
    "telegram": {
        "file": "telegram_cookie.json",
        "domains": [".web.telegram.org", ".telegram.org"],
        "home": "https://web.telegram.org/k/",
        "session": ["stel_token", "stel_ssid"],
        "handle": None,
        "env": {},
    },
    "google": {
        "file": "google_cookie.json",
        "domains": [".google.com"],
        "home": "https://myaccount.google.com/",
        "session": ["SID", "SAPISID", "__Secure-3PSID"],
        "handle": None,
        "env": {},
    },
    "custom": {
        "file": "custom_cookie.json",
        "domains": [],
        "home": "",
        "session": [],
        "handle": None,
        "env": {},
    },
}


def project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def session_dir():
    return os.environ.get("SESSION_DIR") or os.path.join(project_root(), "session")


def cookie_dir():
    return os.environ.get("COOKIE_DIR") or os.path.join(project_root(), "cookies")


def _stem(service):
    s = spec(service)
    base = s["file"]
    if base.endswith(".json"):
        base = base[:-5]
    if base.endswith("_cookie"):
        base = base[:-7]
    return base or service.strip().lower()


def candidates(service):
    if not spec(service):
        return []
    stem = _stem(service)
    full = spec(service)["file"]
    out = []
    for d in (session_dir(), cookie_dir()):
        out.append(os.path.join(d, stem + ".json"))
        out.append(os.path.join(d, full))
    uniq = []
    for p in out:
        if p not in uniq:
            uniq.append(p)
    return uniq


def spec(service):
    name = (service or "").strip().lower()
    s = SERVICES.get(name)
    if not s:
        return None
    if name != "custom":
        return s
    doms = [d.strip() for d in (os.environ.get("CUSTOM_COOKIE_DOMAINS") or "").split(",") if d.strip()]
    sess = [d.strip() for d in (os.environ.get("CUSTOM_COOKIE_SESSION") or "").split(",") if d.strip()]
    return {
        "file": "custom_cookie.json",
        "domains": doms or [".example.com"],
        "home": os.environ.get("CUSTOM_COOKIE_URL") or "",
        "session": sess,
        "handle": os.environ.get("CUSTOM_COOKIE_HANDLE") or None,
        "env": {},
    }


def path_for(service):
    s = spec(service)
    if not s:
        return None
    env_key = "%s_COOKIE_FILE" % service.strip().upper()
    explicit = os.environ.get(env_key) or ""
    if explicit:
        return explicit
    cands = candidates(service)
    for p in cands:
        if os.path.isfile(p):
            return p
    return cands[0]


def _kv_pairs(text):
    out = []
    for chunk in re.split(r"[;\n]+", text):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        k, v = chunk.split("=", 1)
        k = k.strip()
        if k.lower() in ("cookie", "set-cookie"):
            continue
        out.append({"name": k, "value": v.strip().strip('"')})
    return out


def sniff(text):
    raw = (text or "").strip()
    if not raw:
        return None, []
    body = re.sub(r"^\s*(cookie|set-cookie)\s*:\s*", "", raw, flags=re.I)
    try:
        data = json.loads(body)
    except Exception:
        return "header", _kv_pairs(body)
    if isinstance(data, list):
        rows = []
        for item in data:
            if isinstance(item, dict) and item.get("name") is not None:
                rows.append({
                    "name": str(item.get("name")),
                    "value": str(item.get("value", "")),
                    "domain": item.get("domain"),
                    "path": item.get("path") or "/",
                    "expires": item.get("expirationDate") or item.get("expires"),
                    "secure": item.get("secure"),
                    "httpOnly": item.get("httpOnly"),
                })
            elif isinstance(item, str):
                rows.extend(_kv_pairs(item))
        return "list", rows
    if isinstance(data, dict):
        if isinstance(data.get("cookies"), list):
            rows = []
            for item in data["cookies"]:
                if not isinstance(item, dict) or item.get("name") is None:
                    continue
                rows.append({
                    "name": str(item["name"]),
                    "value": str(item.get("value", "")),
                    "domain": item.get("domain"),
                    "path": item.get("path") or "/",
                    "expires": item.get("expires"),
                    "secure": item.get("secure"),
                    "httpOnly": item.get("httpOnly"),
                })
            return "storage_state", rows
        if data.get("name") is not None and "value" in data:
            return "single", [{
                "name": str(data["name"]),
                "value": str(data.get("value", "")),
                "domain": data.get("domain"),
                "path": data.get("path") or "/",
            }]
        rows = []
        for k, v in data.items():
            if isinstance(v, (str, int, float, bool)):
                rows.append({"name": str(k), "value": str(v)})
            elif isinstance(v, dict) and "value" in v:
                rows.append({"name": str(k), "value": str(v.get("value", "")),
                             "domain": v.get("domain"), "path": v.get("path") or "/"})
        return "map", rows
    return None, []


def _fill(rows, s):
    domains = s["domains"]
    for row in rows:
        if not row.get("domain"):
            row["domain"] = domains[0]
        if not row.get("path"):
            row["path"] = "/"
    return rows


def env_fallback(service):
    s = spec(service)
    if not s:
        return []
    rows = []
    for name, key in (s.get("env") or {}).items():
        val = os.environ.get(key)
        if val:
            rows.append({"name": name, "value": val, "domain": s["domains"][0], "path": "/"})
    return rows


def load(service):
    s = spec(service)
    if not s:
        return {"ok": False, "error": "unknown service '%s'" % service,
                "known": sorted(SERVICES.keys())}
    p = path_for(service)
    out = {"ok": False, "service": service.lower(), "path": p, "format": None,
           "count": 0, "names": [], "has_session": False, "source": None, "cookies": []}
    if p and os.path.isfile(p):
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            out["error"] = str(exc)
            return out
        fmt, rows = sniff(text)
        rows = [r for r in _fill(rows, s) if r.get("name")]
        if rows:
            names = [r["name"] for r in rows]
            out.update({
                "ok": True,
                "format": fmt,
                "count": len(rows),
                "names": names,
                "has_session": any(n in names for n in s["session"]),
                "source": "file",
                "cookies": rows,
            })
            return out
        out["error"] = "file ada tapi 0 cookie terbaca (format: %s)" % fmt
        return out
    fb = env_fallback(service)
    if fb:
        names = [r["name"] for r in fb]
        out.update({
            "ok": True,
            "format": "env",
            "count": len(fb),
            "names": names,
            "has_session": any(n in names for n in s["session"]),
            "source": "env",
            "cookies": fb,
        })
        return out
    out["error"] = "no file %s and no .env fallback" % (p or "-")
    out["hint"] = "create %s containing at least %s" % (candidates(service)[0], ", ".join(s["session"]))
    return out


def header(service, extra=None):
    res = load(service)
    if not res.get("ok"):
        return None, res
    parts = ["%s=%s" % (r["name"], r["value"]) for r in res["cookies"]]
    if extra:
        parts.extend("%s=%s" % (k, v) for k, v in extra.items() if v)
    return "; ".join(parts), res


def handle(service):
    res = load(service)
    s = spec(service)
    if not res.get("ok") or not s or not s.get("handle"):
        return None
    for row in res["cookies"]:
        if row["name"] == s["handle"]:
            return row["value"]
    return None


def status(service):
    s = spec(service)
    if not s:
        return {"ok": False, "service": service, "error": "unknown service"}
    p = path_for(service)
    res = load(service)
    out = {
        "ok": res.get("ok", False),
        "service": service.lower(),
        "home": s["home"],
        "domains": s["domains"],
        "needs": s["session"],
        "file": p,
        "file_exists": bool(p and os.path.isfile(p)),
        "candidates": candidates(service),
        "session_dir": session_dir(),
        "format": res.get("format"),
        "count": res.get("count", 0),
        "names": res.get("names", []),
        "has_session": res.get("has_session", False),
        "source": res.get("source"),
    }
    if not res.get("ok"):
        out["reason"] = res.get("error")
        out["hint"] = res.get("hint")
    if out["file_exists"]:
        try:
            out["mode"] = oct(os.stat(p).st_mode & 0o777)
        except OSError:
            pass
    return out


def status_all():
    return {name: status(name) for name in sorted(SERVICES.keys())}


def secure(service):
    p = path_for(service)
    if p and os.path.isfile(p):
        os.chmod(p, 0o600)
        return True
    return False


async def apply_to_context(context, service):
    res = load(service)
    if not res.get("ok"):
        return res
    s = spec(service)
    added = 0
    routes = {}
    failed = []
    for row in res["cookies"]:
        base = {"name": row["name"], "value": row["value"]}
        if row.get("expires"):
            try:
                base["expires"] = float(row["expires"])
            except (TypeError, ValueError):
                pass
        if row.get("secure") is not None:
            base["secure"] = bool(row["secure"])
        if row.get("httpOnly") is not None:
            base["httpOnly"] = bool(row["httpOnly"])
        dom = row.get("domain") or ""
        path = row.get("path") or "/"
        attempts = []
        if dom:
            attempts.append(("domain", dict(base, domain=dom, path=path)))
            if dom.startswith("."):
                attempts.append(("domain-host", dict(base, domain=dom.lstrip("."), path=path)))
        if s.get("home"):
            attempts.append(("url", dict(base, url=s["home"])))
        elif dom:
            attempts.append(("url", dict(base, url="https://" + dom.lstrip(".") + path)))
        last = "no usable cookie format found"
        for route, payload in attempts:
            try:
                await context.add_cookies([payload])
                added += 1
                routes[route] = routes.get(route, 0) + 1
                last = None
                break
            except Exception as exc:
                last = "%s: %s" % (type(exc).__name__, str(exc)[:120])
        if last:
            failed.append({"name": row["name"], "error": last})
    bad = {f["name"] for f in failed}
    session_failed = [n for n in (s.get("session") or []) if n in bad]
    return {
        "ok": bool(added) and not session_failed,
        "added": added,
        "service": service.lower(),
        "source": res.get("source"),
        "has_session": res.get("has_session"),
        "routes": routes,
        "failed": failed,
        "session_failed": session_failed,
    }
