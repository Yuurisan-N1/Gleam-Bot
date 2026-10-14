import hashlib
import json
import os
import time

from curl_cffi import requests

from . import cookies as ck
from .parse import campaign_key, entry_methods, parse_campaign

BASE = "https://gleam.io"
GOOD_STR = "5e`i|XV;>w6DtqPZ'"
BAD_STRS = (".gs__win_chance", "#winning-chance")
BACKOFF = (300, 700, 1000, 2000, 3000, 5000)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0")
SESSION_HINTS = {
    "not_logged_in": "gleam session has no contestant; re-run gleam_login to link X again",
    "invalid_entry_method": "entry method not in this campaign",
    "banned": "contestant is banned from this campaign",
}


def md5g(text):
    h = hashlib.md5(text.encode("utf-8")).hexdigest()
    return h[8:16] + h[0:8] + h[24:32] + h[16:24]


def signature(contestant_id, entry_method_id, entry_type, key):
    return md5g("-%s-%s-%s-%s" % (contestant_id, entry_method_id, entry_type, key))


def fraud_from(cookies):
    for c in cookies or []:
        if c.get("name") == "fpr" and c.get("value"):
            return c["value"]
    return None


def proxies():
    from .transport import dotenv, load_proxies
    dotenv()
    return load_proxies()


class GleamHTTP:
    def __init__(self, cookies=None, proxy=None, impersonate=None, timeout=60, log=None):
        from .transport import dotenv
        dotenv()
        self.log = log
        self.timeout = timeout
        self.cookies = cookies if cookies is not None else self._load_cookies()
        if not self.cookies:
            raise RuntimeError("empty gleam cookie: run gleam_login first")
        self.jar = {c["name"]: c["value"] for c in self.cookies if c.get("name")}
        self.s = requests.Session(impersonate=impersonate or os.environ.get("IMPERSONATE") or "chrome124")
        pl = proxy if proxy is not None else (proxies() or [None])[0]
        self.proxy = pl
        if pl:
            self.s.proxies = {"http": pl, "https": pl}
        self.s.cookies.update(self.jar)
        self._csrf_at = 0
        self._csrf = self.jar.get("XSRF-TOKEN")

    def _load_cookies(self):
        res = ck.load("gleam")
        return res.get("cookies") if res.get("ok") else None

    def _say(self, msg):
        if self.log:
            self.log(msg)

    def refresh_csrf(self, force=False):
        if not force and self._csrf and (time.time() - self._csrf_at) < 300:
            return self._csrf
        r = self.s.get(BASE + "/csrf", timeout=self.timeout)
        tok = self.s.cookies.get("XSRF-TOKEN") or self._csrf
        self._csrf = tok
        self._csrf_at = time.time()
        self._say("csrf %s token=%s" % (r.status_code, (tok or "")[:16]))
        return tok

    def headers(self, json_body=False, csrf=False):
        h = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9",
            "origin": BASE,
            "referer": BASE + "/",
            "user-agent": UA,
            "x-requested-with": "XMLHttpRequest",
        }
        if json_body:
            h["content-type"] = "application/json"
        if csrf:
            h["X-CSRF-Token"] = self.refresh_csrf()
        return h

    def page(self, url):
        r = self.s.get(url, headers={"user-agent": UA, "referer": BASE + "/"}, timeout=self.timeout)
        return r

    def campaign(self, key, slug=""):
        url = "%s/%s/%s" % (BASE, key, slug) if slug else "%s/%s" % (BASE, key)
        r = self.page(url)
        camp = parse_campaign(r.text)
        return {"ok": bool(camp), "status": r.status_code, "url": url, "campaign": camp,
                "html": r.text, "page": r}

    def contestant(self, key, slug=""):
        res = self.campaign(key, slug)
        html = res.get("html") or ""
        marker = "initContestant("
        i = html.find(marker)
        if i < 0:
            return {"ok": False, "reason": "initContestant missing (not logged in?)", "status": res.get("status")}
        from .parse import _extract_balanced
        import html as htmllib
        blob = _extract_balanced(html, i + len(marker))
        if not blob:
            return {"ok": False, "reason": "initContestant unreadable"}
        data = json.loads(htmllib.unescape(blob))
        return {"ok": True, "contestant": data.get("contestant") or {},
                "form": data.get("form") or {}, "raw": data,
                "allow_autoticking": data.get("allow_autoticking"),
                "location_allowed": data.get("location_allowed")}

    def methods(self, key, slug=""):
        res = self.campaign(key, slug)
        camp = res.get("campaign")
        if not camp:
            return []
        return entry_methods(camp)

    def _pull(self, url, sig, body, csrf=True):
        hh = self.headers(json_body=True, csrf=csrf)
        if sig:
            hh["task-signature"] = sig
            return self.s.patch(url, json=body, headers=hh, timeout=self.timeout)
        return self.s.get(url, headers=hh, timeout=self.timeout)

    def enter(self, key, slug, em, contestant_id=None, fraud=None, use_turnstile=True,
              details=None, max_wait=90):
        if contestant_id is None:
            st = self.contestant(key, slug)
            if not st.get("ok"):
                return {"ok": False, "error": st.get("reason")}
            contestant_id = (st["contestant"] or {}).get("id")
        et = em.get("entry_type")
        em_id = em.get("id")
        h = signature(contestant_id, em_id, et, key)
        f = fraud or fraud_from(self.cookies)
        body = {
            "details": details if details is not None else {},
            "h": h,
            "use_hcaptcha": False,
            "use_turnstile": bool(use_turnstile),
            "challenge_response": None,
            "dbg": {"eds": {str(em_id): {}}, "afd": {}, "efd": {}, "dtc": {}, "car": False},
            "dbge": {"eed": "7", "hedr": "4#%s:undefined" % em_id, "csefr": "r[object Object]",
                     "csefn": "#undefined:false", "ae": "ca", "aebps": "ae#2"},
            "stats": {"e": "nd", "mtp": 0, "m": 46, "c": 3, "k": 0, "ts": 0, "tm": 0, "ml": 46,
                      "cl": 3, "kl": 0, "tsl": 0, "tml": 0, "i": 0},
        }
        if f:
            body["f"] = f
        url = "%s/queue-entry/%s/%s" % (BASE, key, em_id)
        out = {"entry_method_id": em_id, "entry_type": et, "h": h, "f": f, "url": url}
        r = self.s.patch(url, json=body, headers=self.headers(json_body=True, csrf=True),
                         timeout=self.timeout)
        out["status"] = r.status_code
        if r.status_code not in (200, 201, 202):
            out["ok"] = False
            out["error"] = "queue-entry HTTP %s" % r.status_code
            out["body"] = (r.text or "")[:400]
            return out
        loc = r.headers.get("task-location")
        sig = r.headers.get("task-signature")
        if loc and loc.startswith("/"):
            loc = BASE + loc
        out["task_location"] = loc
        if not loc:
            out["ok"] = r.status_code in (200, 201)
            out["data"] = self._parse(r)
            return out
        started = time.time()
        attempt = 0
        while (time.time() - started) < max_wait:
            delay = BACKOFF[min(attempt, len(BACKOFF) - 1)] / 1000.0
            time.sleep(delay)
            attempt += 1
            pr = self._pull(loc, sig, body)
            out["poll_status"] = pr.status_code
            data = self._parse(pr)
            if pr.status_code == 200 and isinstance(data, dict) and data.get("status") == 100:
                out["ok"] = True
                out["data"] = data.get("value")
                out["polls"] = attempt
                return out
            if pr.status_code == 201:
                if isinstance(data, dict) and data.get("error"):
                    out["ok"] = False
                    out["data"] = data
                    out["error"] = data["error"]
                    out["polls"] = attempt
                    out["hint"] = SESSION_HINTS.get(data["error"])
                    return out
                out["ok"] = True
                out["data"] = data
                out["polls"] = attempt
                return out
            if pr.status_code not in (200, 202):
                out["ok"] = False
                out["error"] = "poll HTTP %s" % pr.status_code
                out["body"] = (pr.text or "")[:300]
                return out
            nloc = pr.headers.get("task-location")
            nsig = pr.headers.get("task-signature")
            if nloc:
                loc = BASE + nloc if nloc.startswith("/") else nloc
            if nsig:
                sig = nsig
        out["ok"] = False
        out["error"] = "poll timeout %ss" % max_wait
        return out

    @staticmethod
    def _parse(r):
        t = (r.text or "").strip()
        if not t or t == "null":
            return None
        try:
            return json.loads(t)
        except Exception:
            return t[:300]

    def campaign_meta(self, campaign):
        from .sources import gleam as gsrc
        key, slug = gsrc.normalize_key(campaign)
        if not key:
            return {"ok": False, "error": "unrecognized gleam key/URL"}
        st = self.contestant(key, slug)
        c = st.get("contestant") or {}
        auths = c.get("authentications") or []
        return {
            "ok": bool(st.get("ok")),
            "key": key,
            "slug": slug,
            "contestant": {"id": c.get("id"), "name": c.get("name")},
            "x_linked": next((a.get("reference") for a in auths
                              if a.get("provider") == "twitter"), None),
        }

    def state(self, key, slug="", store=None):
        from .resolver import field_for
        camp = self.campaign(key, slug)
        ms = entry_methods(camp.get("campaign") or {})
        st = self.contestant(key, slug)
        c = st.get("contestant") or {}
        entered = c.get("entered") or {}
        auths = c.get("authentications") or []
        rows = []
        total = 0
        for m in ms:
            mid = str(m.get("id"))
            recs = entered.get(mid) or []
            cnt = sum(int(r.get("c") or 1) for r in recs) if isinstance(recs, list) else 0
            total += cnt
            field, how = field_for(m)
            row = {
                "entry_method_id": mid,
                "entry_type": m.get("entry_type"),
                "worth": m.get("worth"),
                "mandatory": m.get("mandatory"),
                "label": (m.get("config1") or "")[:70],
                "api_denied": m.get("api_denied"),
                "requires_details": m.get("requires_details"),
                "field": field,
                "how": how,
                "entered": bool(recs),
                "count": cnt,
            }
            if store is not None and field:
                r = store.resolve(field, key)
                row["env_key"] = r.get("key")
                row["env_ready"] = bool(r.get("ok"))
                row["value_preview"] = (str(r.get("value"))[:40] if r.get("ok") else None)
            rows.append(row)
        return {
            "ok": True,
            "session_ok": bool(c.get("id")),
            "session_hint": None if c.get("id") else "gleam cookie has no contestant: re-run gleam_login",
            "campaign": (camp.get("campaign") or {}).get("name"),
            "key": key,
            "url": camp.get("url"),
            "contestant": {"id": c.get("id"), "name": c.get("name"),
                           "x_linked": next((a.get("reference") for a in auths
                                             if a.get("provider") == "twitter"), None)},
            "entries_total": total,
            "n_methods": len(ms),
            "n_entered": sum(1 for r in rows if r["entered"]),
            "methods": rows,
        }

    def details_for(self, em, store, key):
        from .resolver import field_for
        if em.get("api_denied"):
            return {}, "X_USERNAME", "auth-only (verified by gleam server)"
        field, how = field_for(em)
        if field is None:
            if how == "visit-only":
                return "V", None, "visit-only"
            return None, None, how
        res = store.resolve(field, key)
        if not res.get("ok"):
            return None, field, "missing:%s" % res.get("reason")
        return res["value"], field, how

    def run(self, key, slug="", store=None, only=None, dry_run=False, log=None, max_wait=90,
            auto=True):
        from . import actions
        from .envstore import EnvStore
        if store is None:
            store = EnvStore()
        st = self.state(key, slug, store=store)
        cid = (st.get("contestant") or {}).get("id")
        ms = self.methods(key, slug)
        camp = (self.campaign(key, slug) or {}).get("campaign") or {}
        done = {str(r["entry_method_id"]) for r in st["methods"] if r["entered"]}
        results = []
        if not cid and not dry_run:
            return {"ok": False, "campaign": st.get("campaign"), "contestant": st.get("contestant"),
                    "error": "not_logged_in", "hint": SESSION_HINTS["not_logged_in"],
                    "results": [], "session_ok": False}
        for em in ms:
            mid = str(em.get("id"))
            if only and mid not in [str(x) for x in only]:
                continue
            if mid in done:
                results.append({"entry_method_id": mid, "skipped": "already entered"})
                continue
            xres = None
            if auto and actions.enabled():
                p = actions.plan(em, camp, store, key)
                if p.get("action"):
                    if dry_run:
                        xres = {"action": p["action"], "target": p.get("target"),
                                "text": p.get("text"), "dry_run": True}
                    else:
                        xres = actions.perform(p, log=log)
            details, field, how = self.details_for(em, store, key)
            if xres and xres.get("url") and (details is None or (field or "").endswith(("SUBMIT_URL", "TWEET_URL", "COMMENT_URL")) or field in ("SUBMIT_URL", "X_TWEET_URL", "COMMENT_URL")):
                details = xres["url"]
                field = field or "SUBMIT_URL"
                how = "auto:%s" % xres.get("action")
            if details is None:
                results.append({"entry_method_id": mid, "entry_type": em.get("entry_type"),
                                "skipped": how, "field": field, "x_action": xres})
                if log:
                    log("skip %s: %s" % (mid, how))
                continue
            if dry_run:
                results.append({"entry_method_id": mid, "entry_type": em.get("entry_type"),
                                "field": field, "how": how, "details": str(details)[:60],
                                "would_send": True, "x_action": xres})
                continue
            res = self.enter(key, slug, em, contestant_id=cid, details=details, max_wait=max_wait)
            res["field"] = field
            res["how"] = how
            if xres:
                res["x_action"] = {k: v for k, v in xres.items() if k != "browser"}
            results.append(res)
            if log:
                log("entry %s %s -> %s" % (mid, em.get("entry_type"), res.get("ok")))
            if not res.get("ok"):
                break
            self.refresh_csrf(force=True)
        return {"ok": all(r.get("ok") or r.get("skipped") or r.get("would_send") for r in results),
                "campaign": st.get("campaign"), "contestant": st.get("contestant"),
                "results": results}
