import os
import random
import time

from curl_cffi import requests

DEFAULT_IMPERSONATE = "chrome124"
RETRY_STATUS = (403, 429, 500, 502, 503, 504)


def project_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def dotenv(force=False):
    if getattr(dotenv, "_done", False) and not force:
        return dict(dotenv._vals)
    vals = {}
    for p in (os.path.join(os.getcwd(), ".env"), os.path.join(project_root(), ".env")):
        if not os.path.isfile(p):
            continue
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    vals.setdefault(k, v)
                    os.environ.setdefault(k, v)
        except OSError:
            continue
    dotenv._done = True
    dotenv._vals = vals
    return vals


def load_proxies(path=None):
    path = path or os.environ.get("GLEAM_PROXY_FILE") or os.environ.get("PROXY_FILE")
    if not path:
        path = dotenv().get("GLEAM_PROXY_FILE") or dotenv().get("PROXY_FILE")
    if not path:
        return []
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "://" not in line:
                line = "http://" + line
            out.append(line)
    return out


class Transport:
    def __init__(self, proxies=None, impersonate=None, retry=None, timeout=None, log=None):
        self.proxies = proxies if proxies is not None else load_proxies()
        self.impersonate = impersonate or os.environ.get("IMPERSONATE") or DEFAULT_IMPERSONATE
        self.retry = int(retry or os.environ.get("RETRY") or 6)
        self.timeout = int(timeout or os.environ.get("TIMEOUT") or 60)
        self.log = log
        self._session = None
        self._proxy = None

    def _sess(self, force_new=False):
        if self._session is None or force_new:
            self._proxy = random.choice(self.proxies) if self.proxies else None
            self._session = requests.Session(impersonate=self.impersonate)
            if self._proxy:
                self._session.proxies = {"http": self._proxy, "https": self._proxy}
        return self._session

    def get(self, url, headers=None, params=None, max_tries=None):
        tries = max_tries or self.retry
        last = None
        for attempt in range(1, tries + 1):
            s = self._sess(force_new=(attempt > 1))
            try:
                r = s.get(url, headers=headers, params=params, timeout=self.timeout,
                          allow_redirects=True)
            except Exception as exc:
                last = {"ok": False, "status": None, "error": "%s: %s" % (type(exc).__name__, exc),
                        "attempt": attempt, "proxy": self._proxy}
                self._say("get %s attempt %d failed: %s" % (url, attempt, last["error"]))
                continue
            body = r.text
            if r.status_code in RETRY_STATUS and attempt < tries:
                last = {"ok": False, "status": r.status_code, "error": "retryable",
                        "attempt": attempt, "proxy": self._proxy}
                self._say("get %s %d -> retry (new proxy)" % (url, r.status_code))
                continue
            ok = r.status_code == 200 and "initCampaign(" in body
            return {
                "ok": ok,
                "status": r.status_code,
                "url": str(r.url),
                "body": body,
                "attempt": attempt,
                "proxy": self._proxy,
                "cf_mitigated": r.headers.get("cf-mitigated"),
            }
        return last or {"ok": False, "status": None, "error": "no attempt", "body": ""}

    def _say(self, msg):
        if self.log:
            self.log(msg)
