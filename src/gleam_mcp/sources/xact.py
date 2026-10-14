import json
import os
import re
import time

from curl_cffi import requests

from . import x as xs

BASE = "https://x.com"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

OPS = {
    "CreateTweet": "wR5Z_lEibLvkew3tF9w-Sg",
    "CreateNoteTweet": "H7QXYuKegEKuUJvkuW5_dg",
    "DeleteTweet": "nxpZCY2K-I6QoFHAHeojFQ",
    "FavoriteTweet": "lI07N6Otwv1PhnEgXILM7A",
    "UnfavoriteTweet": "ZYKSe-w7KEslx3JhSIk5LA",
    "CreateRetweet": "mbRO74GrOvSfRcJnlMapnQ",
    "DeleteRetweet": "ZyZigVsNiFO6v1dEks1eWg",
    "UserByScreenName": "AMIBMjtxEEATh4z8V9GtRg",
    "UserTweets": "7_KBXBpG0zBPRN6UCIV0-w",
    "TweetDetail": "3BlMtudy4N-d78ch7zTLZQ",
}

FEATURES = {
    "hidden_profile_subscriptions_enabled": True,
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "subscriptions_verification_info_is_identity_verified_enabled": True,
    "subscriptions_verification_info_verified_since_enabled": True,
    "highlights_tweets_tab_ui_enabled": True,
    "responsive_web_twitter_article_notes_tab_enabled": True,
    "subscriptions_feature_can_gift_premium": True,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
}

DETAIL_FEATURES = {
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
}

DETAIL_TOGGLES = {"withArticleRichContentState": True}

_OPS_CACHE = None


def ops_file():
    from ..cookies import session_dir
    return os.path.join(session_dir(), "x_ops.json")


def load_ops():
    global _OPS_CACHE
    if _OPS_CACHE:
        return _OPS_CACHE
    ops = dict(OPS)
    try:
        with open(ops_file()) as fh:
            data = json.load(fh)
        for name, qid in (data.get("ops") or {}).items():
            if qid:
                ops[name] = qid
    except Exception:
        pass
    _OPS_CACHE = ops
    return ops


def save_ops(ops):
    global _OPS_CACHE
    _OPS_CACHE = dict(ops)
    try:
        with open(ops_file(), "w") as fh:
            json.dump({"ops": ops, "ts": int(time.time())}, fh, indent=2)
    except Exception:
        pass


def session():
    c = xs.creds()
    if not xs.has_creds():
        return None
    s = requests.Session(impersonate=os.environ.get("IMPERSONATE") or "chrome124")
    s.cookies.set("auth_token", c["auth_token"], domain=".x.com")
    s.cookies.set("ct0", c["ct0"], domain=".x.com")
    return s


def _headers():
    return xs.headers(xs.creds())


def _form_headers():
    h = dict(_headers())
    h["content-type"] = "application/x-www-form-urlencoded"
    return h


def discover_ops(timeout=60):
    s = session()
    if s is None:
        return {"ok": False, "error": "X cookie missing (session/x_cookie.json or X_AUTH_TOKEN/X_CT0)"}
    try:
        r = s.get(BASE + "/home", headers={"accept": "text/html,application/xhtml+xml",
                                           "accept-language": "en-US,en;q=0.9",
                                           "user-agent": UA}, timeout=timeout)
    except Exception as exc:
        return {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}
    if r.status_code != 200:
        return {"ok": False, "status": r.status_code, "error": "x.com/home rejected the session"}
    bundles = re.findall(r"https://abs\.twimg\.com/responsive-web/client-web/main\.[0-9a-f]+\.js", r.text)
    if not bundles:
        bundles = sorted(set(re.findall(r"https://abs\.twimg\.com/responsive-web/client-web/[^\"'\\ ]+\.js",
                                        r.text)), key=len, reverse=True)[:3]
    found = {}
    for url in dict.fromkeys(bundles):
        try:
            b = requests.get(url, headers={"user-agent": UA}, impersonate="chrome124", timeout=timeout)
        except Exception:
            continue
        if b.status_code != 200:
            continue
        text = b.text
        for m in re.finditer(r"queryId:\"([\w-]+)\",operationName:\"(\w+)\"", text):
            found[m.group(2)] = m.group(1)
        for m in re.finditer(r"operationName:\"(\w+)\",queryId:\"([\w-]+)\"", text):
            found[m.group(1)] = m.group(2)
    if not found:
        return {"ok": False, "error": "no operation ids found in bundles", "bundles": bundles}
    merged = dict(OPS)
    merged.update(found)
    save_ops(merged)
    return {"ok": True, "ops_found": len(found), "bundles": bundles[:3],
            "interesting": {k: merged.get(k) for k in OPS if merged.get(k) != OPS.get(k)}}


def ops_report():
    ops = load_ops()
    return {"file": ops_file(), "count": len(ops),
            "core": {k: ops.get(k) for k in OPS},
            "changed_from_builtin": sorted(k for k in OPS if ops.get(k) != OPS.get(k))}


def _graphql(name, variables, post=False, timeout=40, features=None, toggles=None):
    ops = load_ops()
    qid = ops.get(name)
    if not qid:
        return {"ok": False, "error": "unknown operation %s" % name}
    s = session()
    if s is None:
        return {"ok": False, "error": "X cookie missing"}
    url = "%s/i/api/graphql/%s/%s" % (BASE, qid, name)
    body = {"variables": variables, "queryId": qid}
    if features:
        body["features"] = features
    if toggles:
        body["fieldToggles"] = toggles
    try:
        if post:
            r = s.post(url, headers=_headers(), json=body, timeout=timeout)
        else:
            r = s.get(url, headers=_headers(),
                      params={"variables": json.dumps(variables),
                              "features": json.dumps(features or {}),
                              "fieldToggles": json.dumps(toggles or {})}, timeout=timeout)
    except Exception as exc:
        return {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}
    out = {"ok": r.status_code == 200, "status": r.status_code, "op": name, "qid": qid}
    try:
        out["json"] = r.json()
    except Exception:
        out["json"] = None
    if not out["ok"]:
        errs = (out["json"] or {}).get("errors") or []
        out["error"] = (errs[0].get("message") if errs else (r.text or "")[:200])
        out["code"] = errs[0].get("code") if errs else r.status_code
    return out


def me(timeout=30):
    return _graphql("UserByScreenName", {"screen_name": "me", "withSafetyModeUserFields": True},
                    timeout=timeout, features={"hidden_profile_subscriptions_enabled": True})


def profile(handle, timeout=30):
    res = _graphql("UserByScreenName",
                   {"screen_name": handle.lstrip("@"), "withSafetyModeUserFields": True},
                   timeout=timeout, features={"hidden_profile_subscriptions_enabled": True})
    if not res.get("ok"):
        return res
    u = ((res["json"].get("data") or {}).get("user") or {}).get("result") or {}
    core = u.get("core") or {}
    return {"ok": True, "id": u.get("rest_id"), "screen_name": core.get("screen_name"),
            "name": core.get("name"), "following": (u.get("relationship_perspectives") or {}).get("following"),
            "followers": (u.get("relationship_counts") or {}).get("followers")}


def follow(handle, timeout=30):
    s = session()
    if s is None:
        return {"ok": False, "error": "X cookie missing"}
    p = profile(handle, timeout=timeout)
    if not p.get("ok"):
        return {"ok": False, "error": "target lookup failed", "detail": p.get("error")}
    if p.get("following"):
        return {"ok": True, "action": "follow", "target": p["screen_name"], "state": "already-following",
                "id": p["id"]}
    try:
        r = s.post(BASE + "/i/api/1.1/friendships/create.json", headers=_form_headers(),
                   data={"user_id": p["id"], "include_profile_interstitial_type": "1",
                         "skip_status": "true"}, timeout=timeout)
    except Exception as exc:
        return {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}
    out = {"ok": r.status_code == 200, "action": "follow", "target": p["screen_name"], "id": p["id"],
           "status": r.status_code}
    if not out["ok"]:
        out["error"] = (r.text or "")[:200]
    return out


def unfollow(handle, timeout=30):
    s = session()
    if s is None:
        return {"ok": False, "error": "X cookie missing"}
    p = profile(handle, timeout=timeout)
    if not p.get("ok"):
        return {"ok": False, "error": "target lookup failed", "detail": p.get("error")}
    try:
        r = s.post(BASE + "/i/api/1.1/friendships/destroy.json", headers=_form_headers(),
                   data={"user_id": p["id"], "include_profile_interstitial_type": "1",
                         "skip_status": "true"}, timeout=timeout)
    except Exception as exc:
        return {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}
    return {"ok": r.status_code == 200, "action": "unfollow", "target": p["screen_name"],
            "status": r.status_code, "error": None if r.status_code == 200 else (r.text or "")[:200]}


def tweet_state(tweet_id, timeout=40):
    res = _graphql("TweetDetail",
                   {"focalTweetId": str(tweet_id), "with_rux_injections": False,
                    "rankingMode": "Relevance", "includePromotedContent": True,
                    "withCommunity": True, "withQuickPromoteEligibilityTweetFields": True,
                    "withBirdwatchNotes": True, "withVoice": True},
                   timeout=timeout, features=DETAIL_FEATURES, toggles=DETAIL_TOGGLES)
    if not res.get("ok"):
        return res
    j = res["json"]
    try:
        ins = j["data"]["threaded_conversation_with_injections_v2"]["instructions"]
    except Exception:
        return {"ok": False, "error": "unrecognized TweetDetail shape"}
    focal = None
    replies = []
    for ins_item in ins:
        for e in ins_item.get("entries") or []:
            ic = (e.get("content") or {}).get("itemContent") or {}
            tr = (ic.get("tweet_results") or {}).get("result") or {}
            lg = tr.get("legacy") or {}
            core = ((tr.get("core") or {}).get("user_results") or {}).get("result") or {}
            handle = (core.get("core") or {}).get("screen_name")
            if not lg:
                for it in (e.get("content") or {}).get("items") or []:
                    tr2 = ((it.get("item") or {}).get("itemContent") or {}).get("tweet_results", {}).get("result", {}) or {}
                    lg = tr2.get("legacy") or {}
                    core2 = ((tr2.get("core") or {}).get("user_results") or {}).get("result") or {}
                    handle = (core2.get("core") or {}).get("screen_name")
                    if lg.get("id_str"):
                        replies.append({"id": lg["id_str"], "user": handle,
                                        "text": lg.get("full_text") or ""})
                    continue
            if str(lg.get("id_str")) == str(tweet_id):
                focal = {"id": lg["id_str"], "favorited": lg.get("favorited"),
                         "retweeted": lg.get("retweeted"),
                         "favorite_count": lg.get("favorite_count"),
                         "retweet_count": lg.get("retweet_count"),
                         "reply_count": lg.get("reply_count")}
            elif lg.get("id_str"):
                replies.append({"id": lg["id_str"], "user": handle, "text": lg.get("full_text") or ""})
    seen = set()
    unique = []
    for r in replies:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        unique.append(r)
    return {"ok": True, "tweet": focal, "replies": unique}


def like(tweet_id, timeout=30):
    res = _graphql("FavoriteTweet", {"tweet_id": str(tweet_id)}, post=True, timeout=timeout)
    if res.get("ok"):
        return {"ok": True, "action": "like", "tweet_id": str(tweet_id)}
    return {"ok": False, "action": "like", "tweet_id": str(tweet_id), "status": res.get("status"),
            "error": res.get("error")}


def unlike(tweet_id, timeout=30):
    res = _graphql("UnfavoriteTweet", {"tweet_id": str(tweet_id)}, post=True, timeout=timeout)
    return {"ok": res.get("ok"), "action": "unlike", "tweet_id": str(tweet_id),
            "status": res.get("status"), "error": res.get("error")}


def post(text, reply_to=None, timeout=40):
    variables = {
        "tweet_text": text,
        "dark_request": False,
        "media": {"media_entities": [], "possibly_sensitive": False},
        "semantic_annotation_ids": [],
    }
    if reply_to:
        variables["reply"] = {"in_reply_to_tweet_id": str(reply_to), "exclude_reply_user_ids": []}
    res = _graphql("CreateTweet", variables, post=True, timeout=timeout)
    out = {"ok": False, "action": "reply" if reply_to else "post", "text": text,
           "reply_to": str(reply_to) if reply_to else None}
    if res.get("ok"):
        j = res.get("json") or {}
        result = (((j.get("data") or {}).get("create_tweet") or {}).get("tweet_results") or {}).get("result") or {}
        tid = result.get("rest_id")
        lg = result.get("legacy") or {}
        out.update({"ok": bool(tid), "tweet_id": tid, "url": permalink(tid, reply_to),
                    "reply_id": lg.get("in_reply_to_status_id_str")})
        if not tid:
            out["error"] = "create_tweet returned no id"
        return out
    out["status"] = res.get("status")
    out["code"] = res.get("code")
    out["error"] = res.get("error")
    if res.get("code") == 187:
        out["ok"] = True
        out["duplicate"] = True
        out["error"] = None
    return out


def permalink(tweet_id, parent_id=None):
    if not tweet_id:
        return None
    who = own_handle()
    if parent_id:
        return "https://x.com/%s/status/%s" % (who, tweet_id)
    return "https://x.com/%s/status/%s" % (who, tweet_id)


_OWN = None


def own_handle(timeout=30):
    global _OWN
    if _OWN:
        return _OWN
    s = session()
    if s is None:
        return "i"
    try:
        r = s.get(BASE + "/i/api/1.1/account/settings.json", headers=_headers(), timeout=timeout)
        if r.status_code == 200:
            _OWN = (r.json() or {}).get("screen_name") or "i"
            return _OWN
    except Exception:
        pass
    try:
        r = s.get(BASE + "/settings/profile", headers={"user-agent": UA}, timeout=timeout)
        m = re.search(r'"screen_name":"([A-Za-z0-9_]{1,15})"', r.text)
        if m:
            _OWN = m.group(1)
            return _OWN
    except Exception:
        pass
    return "i"


def user_tweets(handle, count=20, timeout=40):
    p = profile(handle, timeout=timeout)
    if not p.get("ok"):
        return {"ok": False, "error": "profile lookup failed", "detail": p.get("error")}
    res = _graphql("UserTweets", {"userId": p["id"], "count": count, "includePromotedContent": False,
                                  "withQuickPromoteEligibilityTweetFields": False, "withVoice": True},
                   timeout=timeout, features=FEATURES, toggles={"withArticlePlainText": False})
    if not res.get("ok"):
        return {"ok": False, "error": res.get("error")}
    try:
        ins = res["json"]["data"]["user"]["result"]["timeline"]["timeline"]["instructions"]
    except Exception:
        return {"ok": False, "error": "unrecognized timeline shape"}
    rows = []
    for item in ins:
        for e in item.get("entries") or []:
            m = re.match(r"(?:tweet|profile-conversation)-(\d+)", e.get("entryId") or "")
            if not m:
                continue
            lg = (((e.get("content") or {}).get("itemContent") or {}).get("tweet_results") or {}).get("result", {}).get("legacy") or {}
            if not lg:
                for it in (e.get("content") or {}).get("items") or []:
                    lg = (((it.get("item") or {}).get("itemContent") or {}).get("tweet_results") or {}).get("result", {}).get("legacy") or {}
                    if lg.get("id_str"):
                        break
            if lg.get("id_str"):
                rows.append({"id": lg["id_str"], "created_at": lg.get("created_at"),
                             "text": lg.get("full_text") or ""})
    return {"ok": True, "handle": p["screen_name"], "id": p["id"], "tweets": rows}


def retweet(tweet_id, timeout=60, browser=None):
    res = _graphql("CreateRetweet", {"tweet_id": str(tweet_id), "dark_request": False},
                   post=True, timeout=timeout)
    out = {"ok": res.get("ok"), "action": "retweet", "tweet_id": str(tweet_id),
           "method": "http", "status": res.get("status"), "error": res.get("error")}
    if res.get("ok"):
        return out
    if browser is None:
        from .. import browser as br
        browser = br.x_action
    alt = browser("retweet", "https://x.com/i/status/%s" % tweet_id)
    out["method"] = "browser"
    out["browser"] = alt.get("actions") or {}
    out["ok"] = bool((out["browser"] or {}).get("state") in ("confirmed", "already-retweeted"))
    if not out["ok"]:
        out["error"] = alt.get("error") or "browser retweet failed"
    return out


def unretweet(tweet_id, timeout=30):
    res = _graphql("DeleteRetweet", {"source_tweet_id": str(tweet_id), "dark_request": False},
                   post=True, timeout=timeout)
    return {"ok": res.get("ok"), "action": "unretweet", "tweet_id": str(tweet_id),
            "status": res.get("status"), "error": res.get("error")}


def reply(tweet_id, text, timeout=60, browser=None):
    res = post(text, reply_to=tweet_id, timeout=timeout)
    if res.get("ok"):
        res["method"] = "http"
        return res
    if browser is None:
        from .. import browser as br
        browser = br.x_action
    alt = browser("reply", "https://x.com/i/status/%s" % tweet_id, text)
    st = tweet_state(tweet_id)
    mine = [r for r in (st.get("replies") or []) if r.get("user") == own_handle()]
    out = {"ok": bool(mine), "action": "reply", "tweet_id": str(tweet_id), "text": text,
           "method": "browser", "browser": alt.get("actions") or {}, "http_error": res.get("error")}
    if mine:
        out["tweet_id"] = mine[0]["id"]
        out["url"] = "https://x.com/%s/status/%s" % (mine[0].get("user"), mine[0]["id"])
    else:
        out["error"] = alt.get("error") or "reply not visible after browser attempt"
    return out


def verify(tweet_id, timeout=40):
    st = tweet_state(tweet_id, timeout=timeout)
    if not st.get("ok"):
        return st
    mine = own_handle()
    return {"ok": True, "tweet": st.get("tweet"),
            "my_replies": [r for r in (st.get("replies") or []) if r.get("user") == mine]}


def status():
    ops = load_ops()
    return {"creds": xs.has_creds(), "handle": own_handle() if xs.has_creds() else None,
            "ops_file": ops_file(), "ops": len(ops),
            "builtin_drift": sorted(k for k in OPS if ops.get(k) != OPS.get(k))}
