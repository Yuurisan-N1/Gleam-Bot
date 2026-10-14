import os
import re

from .parse import entry_methods
from .resolver import clean
from .sources import xact

COMMENT_HINTS = (r"\bcomment\b", r"\breply\b", r"comment\s+section")
POST_HINTS = (r"\bshare\b", r"\btweet\b", r"\bpost\b", r"\bretweet\b", r"\brt\b")
RETWEET_HINTS = (r"\bretweet\b", r"\brepost\b", r"\brt\b")
LIKE_HINTS = (r"\blike\b", r"\bfavorite\b", r"\bheart\b")
FOLLOW_HINTS = (r"\bfollow\b", r"\bsubscribe\b")


def enabled():
    v = (os.environ.get("X_AUTO_ACTION") or "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def label_of(em):
    parts = [clean(em.get("config1")), clean(em.get("config3")), clean(em.get("config4")),
             clean(em.get("action_description"))]
    return " ".join(p for p in parts if p).strip()


def env_text(store, key, *names):
    for name in names:
        if store is None:
            break
        res = store.resolve(name, key, validate=False)
        if res.get("ok") and res.get("value"):
            return res["value"]
    for name in names:
        v = (os.environ.get(name) or "").strip()
        if v:
            return v
    return None


def tags_in(text):
    return re.findall(r"[$#][A-Za-z0-9_]{2,}", text or "")


def quoted_in(text):
    m = re.findall(r"[\"'\u201c\u2018]([^\"'\u201d\u2019]{2,120})[\"\u201d\u2019']", text or "")
    return m[0].strip() if m else None


def comment_token(label):
    q = quoted_in(label)
    if q:
        return q
    m = re.search(r"comment\s+([#$@]?[A-Za-z0-9_]{2,})", label or "", re.I)
    if m:
        return m.group(1)
    tags = tags_in(label)
    return tags[0] if tags else None


def post_text(label, campaign=None, store=None, key=None):
    override = env_text(store, key, "X_TWEET_TEXT", "TWEET_TEXT", "CUSTOM_TEXT", "PROMO_TEXT")
    if override:
        return override
    label = (label or "").strip()
    q = quoted_in(label)
    if q:
        return q
    tags = tags_in(label)
    m = re.search(r"(?:excited|happy|thrilled|hyped|glad)\s+(?:about|for|to)\s+(.+)", label, re.I)
    if m:
        body = "I am excited about %s" % m.group(1).strip(" .:-")
    else:
        body = re.sub(r"^(share|tweet|post|tell\s+us|say|write|drop|comment)\b[\s:,\-]*", "", label, flags=re.I)
        body = re.sub(r"^\d+\s*things?\s+(?:you\s+)?(?:about\s+)?", "", body, flags=re.I)
        body = re.sub(r"^(?:why|what)\s+you\s+(?:like|love|are\s+excited\s+about)\s*", "", body, flags=re.I)
        body = re.sub(r"\s+", " ", body).strip(" .:-")
    if not body:
        body = clean((campaign or {}).get("name")) or "Giveaway entry"
    tail = " ".join(dict.fromkeys(t for t in tags if t.lower() not in body.lower()))
    if tail:
        body = "%s %s" % (body, tail)
    return body[:270]


def follow_handles(campaign):
    out = []
    for em in entry_methods(campaign or {}):
        if (em.get("entry_type") or "") == "twitter_follow":
            h = clean(em.get("config1"))
            if h:
                out.append(h.lstrip("@"))
    return out


def reply_target(em, campaign, store=None, key=None):
    override = env_text(store, key, "X_REPLY_TARGET", "X_REPLY_TWEET_ID", "X_TWEET_TARGET")
    if override:
        m = re.search(r"(\d{6,25})", override)
        return m.group(1) if m else None
    label = label_of(em)
    tags = [t.lower() for t in tags_in(label)]
    handles = follow_handles(campaign)
    if not handles:
        return None
    ordered = list(reversed(handles))
    for handle in ordered:
        res = xact.user_tweets(handle, count=20)
        if not res.get("ok"):
            continue
        for tw in res["tweets"]:
            body = (tw.get("text") or "").lower()
            if not tags or any(t in body for t in tags):
                return tw["id"]
        if res["tweets"]:
            return res["tweets"][0]["id"]
    return None


def plan(em, campaign=None, store=None, key=None):
    et = (em.get("entry_type") or "").strip()
    label = label_of(em)
    title = clean(em.get("config1"))
    low = label.lower()
    row = {"entry_method_id": str(em.get("id")), "entry_type": et, "label": label[:80],
           "action": None, "target": None, "text": None, "reason": None}
    if et == "twitter_follow":
        row.update({"action": "follow", "target": clean(em.get("config1")).lstrip("@")})
        return row
    if et in ("twitter_retweet", "twitter_repost"):
        row.update({"action": "retweet", "target": clean(em.get("config2")) or None,
                    "reason": "target tweet id from entry config"})
        return row
    if et in ("twitter_tweet", "twitter_hashtags", "twitter_media", "twitter_like"):
        act = "like" if any(re.search(h, low) for h in LIKE_HINTS) else "post"
        row.update({"action": act, "text": post_text(title or label, campaign, store, key)})
        return row
    if et == "submit_url":
        if any(re.search(h, low) for h in RETWEET_HINTS):
            row.update({"action": "retweet", "target": reply_target(em, campaign, store, key)})
            return row
        if any(re.search(h, low) for h in LIKE_HINTS):
            row.update({"action": "like", "target": reply_target(em, campaign, store, key)})
            return row
        if any(re.search(h, low) for h in COMMENT_HINTS):
            override = env_text(store, key, "X_COMMENT_TEXT", "COMMENT_TEXT")
            token = override or comment_token(label) or post_text(title or label, campaign, store, key)
            row.update({"action": "reply", "text": token,
                        "target": reply_target(em, campaign, store, key)})
            return row
        if any(re.search(h, low) for h in POST_HINTS):
            row.update({"action": "post", "text": post_text(title or label, campaign, store, key)})
            return row
        row["reason"] = "submit_url without a detectable X action; using .env value"
        return row
    if et == "share_action":
        row["reason"] = "share_action needs a real viral share, no API path"
        return row
    if et in ("custom_action", "wallet_address", "email_subscribe", "gleam_subscribe", "verify_phone"):
        return row
    if any(re.search(h, low) for h in FOLLOW_HINTS):
        tags = [t.lstrip("@") for t in tags_in(label) if t.startswith("@")]
        if tags:
            row.update({"action": "follow", "target": tags[0]})
            return row
    if any(re.search(h, low) for h in RETWEET_HINTS):
        row.update({"action": "retweet", "target": reply_target(em, campaign, store, key)})
        return row
    if any(re.search(h, low) for h in LIKE_HINTS):
        row.update({"action": "like", "target": reply_target(em, campaign, store, key)})
        return row
    return row


def plans(campaign, store=None, key=None):
    return [plan(em, campaign, store, key) for em in entry_methods(campaign or {})]


def perform(p, log=None, browser=None):
    act = p.get("action")
    out = {"entry_method_id": p.get("entry_method_id"), "action": act,
           "target": p.get("target"), "ok": False}
    if not act:
        out["skipped"] = p.get("reason") or "no X action required"
        return out
    if not xact.status().get("creds"):
        out["error"] = "X cookie missing (session/x_cookie.json or X_AUTH_TOKEN/X_CT0)"
        return out
    if act == "follow":
        res = xact.follow(p["target"])
    elif act == "retweet":
        res = xact.retweet(p["target"], browser=browser)
    elif act == "like":
        res = xact.like(p["target"])
    elif act == "reply":
        res = xact.reply(p["target"], p["text"], browser=browser)
    elif act == "post":
        res = xact.post(p["text"])
    else:
        out["error"] = "unsupported action %s" % act
        return out
    out.update(res)
    if log:
        log("x %s %s -> %s" % (act, p.get("target") or p.get("text", "")[:30], res.get("ok")))
    return out


def run_campaign(campaign, store=None, key=None, log=None, only=None):
    rows = []
    for p in plans(campaign, store, key):
        if only and p["entry_method_id"] not in [str(x) for x in only]:
            continue
        if not p.get("action"):
            rows.append({"entry_method_id": p["entry_method_id"], "action": None,
                         "skipped": p.get("reason") or "no X action required"})
            continue
        rows.append(perform(p, log=log))
    return rows
