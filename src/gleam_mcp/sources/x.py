import json
import os

from curl_cffi import requests

WEB_BEARER = ("AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
              "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA")
USER_BY_SCREEN_NAME = "G3KGOASz96M-Qu0nwmGXNg"
BASE = "https://x.com"


def cookie_jar():
    from .. import cookies as ck
    hdr, res = ck.header("x")
    jar = {}
    if hdr:
        for part in hdr.split("; "):
            if "=" in part:
                k, v = part.split("=", 1)
                jar[k.strip()] = v.strip()
    return jar, (res or {})


def creds():
    jar, res = cookie_jar()
    return {
        "auth_token": jar.get("auth_token") or os.environ.get("X_AUTH_TOKEN") or "",
        "ct0": jar.get("ct0") or os.environ.get("X_CT0") or "",
        "bearer": os.environ.get("X_BEARER") or WEB_BEARER,
        "source": res.get("source"),
        "cookie_file": res.get("path"),
    }


def has_creds():
    c = creds()
    return bool(c["auth_token"] and c["ct0"])


def headers(c):
    return {
        "authorization": "Bearer %s" % c["bearer"],
        "x-csrf-token": c["ct0"],
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-active-user": "yes",
        "x-twitter-client-language": "en",
        "content-type": "application/json",
        "referer": BASE + "/home",
    }


def status():
    c = creds()
    if not has_creds():
        return {
            "ok": False,
            "configured": False,
            "reason": "X cookie missing: fill %s (x.json) or X_AUTH_TOKEN/X_CT0 in .env" % (c["cookie_file"] or "-"),
            "note": "without this cookie, gleam entries flagged api_denied cannot proceed",
        }
    s = requests.Session(impersonate=os.environ.get("IMPERSONATE") or "chrome124")
    s.cookies.set("auth_token", c["auth_token"], domain=".x.com")
    s.cookies.set("ct0", c["ct0"], domain=".x.com")
    try:
        r = s.get(BASE + "/home", headers=headers(c), timeout=30, allow_redirects=True)
    except Exception as exc:
        return {"ok": False, "configured": True, "error": "%s: %s" % (type(exc).__name__, exc)}
    logged_in = "auth_token" in {k for k in s.cookies.keys()}
    return {
        "ok": r.status_code == 200 and "login" not in str(r.url),
        "configured": True,
        "status": r.status_code,
        "final_url": str(r.url),
        "cookies_present": logged_in,
        "source": c["source"],
        "cookie_file": c["cookie_file"],
    }


def user_lookup(screen_name):
    c = creds()
    if not has_creds():
        return {"ok": False, "error": "X credentials not set in .env"}
    s = requests.Session(impersonate=os.environ.get("IMPERSONATE") or "chrome124")
    s.cookies.set("auth_token", c["auth_token"], domain=".x.com")
    s.cookies.set("ct0", c["ct0"], domain=".x.com")
    params = {
        "variables": json.dumps({"screen_name": screen_name.lstrip("@"), "withSafetyModeUserFields": True}),
        "features": json.dumps({"hidden_profile_subscriptions_enabled": True}),
    }
    url = "%s/i/api/graphql/%s/UserByScreenName" % (BASE, USER_BY_SCREEN_NAME)
    try:
        r = s.get(url, headers=headers(c), params=params, timeout=30)
    except Exception as exc:
        return {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}
    if r.status_code != 200:
        return {"ok": False, "status": r.status_code, "error": r.text[:200]}
    try:
        data = r.json()
        u = data["data"]["user"]["result"]["legacy"]
    except Exception:
        return {"ok": False, "error": "unrecognized response shape", "raw": r.text[:200]}
    return {
        "ok": True,
        "screen_name": u.get("screen_name"),
        "id": u.get("id_str"),
        "name": u.get("name"),
        "followers": u.get("followers_count"),
        "following": u.get("friends_count"),
        "protected": u.get("protected"),
        "verified": u.get("verified"),
    }
