import asyncio
import os
import time
from urllib.parse import urlsplit

from . import cookies as ck

LOGIN_MARKERS = ("/i/flow/login", "/login", "accounts/login", "/auth/", "/signin", "/sign_in")


def headless():
    v = (os.environ.get("BROWSER_HEADLESS") or "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def engine():
    v = (os.environ.get("BROWSER_ENGINE") or "auto").strip().lower()
    if v in ("camoufox", "chromium", "firefox"):
        return v
    try:
        import camoufox
        return "camoufox" if camoufox else "chromium"
    except Exception:
        return "chromium"


def timeout_s():
    try:
        return float(os.environ.get("BROWSER_TIMEOUT") or 60)
    except ValueError:
        return 60.0


def root_dir():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _dotenv():
    vals = {}
    for p in (os.path.join(os.getcwd(), ".env"), os.path.join(root_dir(), ".env")):
        if not os.path.isfile(p):
            continue
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    vals.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        except Exception:
            pass
    return vals


def proxy():
    raw = ""
    for key in ("BROWSER_PROXY", "PROXY_URL", "GLEAM_PROXY"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            break
    if not raw:
        p = (os.environ.get("GLEAM_PROXY_FILE") or os.environ.get("PROXY_FILE") or "").strip()
        if not p:
            p = _dotenv().get("PROXY_FILE") or ""
        if not p:
            p = os.path.join(root_dir(), "proxy.txt")
        if p and os.path.isfile(p):
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        raw = line
                        break
    if not raw:
        return None
    u = urlsplit(raw if "://" in raw else "http://" + raw)
    if not u.hostname:
        return None
    d = {"server": "%s://%s:%s" % (u.scheme or "http", u.hostname, u.port or 80)}
    if u.username:
        d["username"] = u.username
        d["password"] = u.password or ""
    return d


def chromium_path():
    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or "/root/.cache/ms-playwright"
    if not os.path.isdir(root):
        return None
    for name in sorted(os.listdir(root), reverse=True):
        cand = os.path.join(root, name, "chrome-linux64", "chrome")
        if os.path.isfile(cand):
            return cand
    return None


def available():
    eng = engine()
    out = {"engine": eng, "headless": headless(), "timeout": timeout_s(),
           "proxy": bool(proxy()), "cookie_dir": ck.cookie_dir()}
    if eng == "camoufox":
        try:
            from camoufox.async_api import AsyncCamoufox
            out["camoufox_pkg"] = bool(AsyncCamoufox)
        except Exception as exc:
            out["camoufox_pkg"] = False
            out["camoufox_error"] = str(exc)
        cache = os.environ.get("CAMOUFOX_CACHE") or os.path.expanduser("~/.cache/camoufox")
        out["camoufox_cache"] = os.path.isdir(cache)
    else:
        try:
            import playwright
            out["playwright_pkg"] = bool(playwright)
        except Exception as exc:
            out["playwright_pkg"] = False
            out["playwright_error"] = str(exc)
        out["chromium_binary"] = chromium_path()
    return out


async def _launch(eng, persistent=None):
    if eng == "camoufox":
        from camoufox.async_api import AsyncCamoufox
        try:
            from camoufox.fingerprints import Screen
        except Exception:
            from browserforge.fingerprints import Screen
        kw = {
            "headless": headless(),
            "humanize": True,
            "os": os.environ.get("CAMOUFOX_OS") or "windows",
            "screen": Screen(max_width=1920, max_height=1080),
            "window": (1366, 900),
        }
        px = proxy()
        if px:
            kw["proxy"] = px
        if persistent:
            kw["persistent_context"] = True
            kw["user_data_dir"] = persistent
        return "camoufox", AsyncCamoufox(**kw)
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    binp = chromium_path()
    kw = {"headless": headless(),
          "args": ["--no-sandbox", "--disable-dev-shm-usage",
                   "--disable-blink-features=AutomationControlled"]}
    if binp:
        kw["executable_path"] = binp
    px = proxy()
    if px:
        kw["proxy"] = px
    browser = await pw.chromium.launch(**kw)
    ctx = await browser.new_context(
        viewport={"width": 1366, "height": 900},
        user_agent=os.environ.get("USER_AGENT") or None,
    )
    return "chromium", (pw, browser, ctx)


async def _session_state(ctx, page, service):
    s = ck.spec(service) or {}
    names = set()
    try:
        for c in await ctx.cookies():
            names.add(c.get("name"))
    except Exception:
        pass
    url = (page.url or "").lower()
    blocked = any(m in url for m in LOGIN_MARKERS)
    has = any(n in names for n in (s.get("session") or []))
    return {
        "logged_in": bool(has and not blocked),
        "session_cookie": has,
        "redirected_to_login": blocked,
        "cookie_names": sorted(n for n in names if n),
    }


async def _drive(service, url=None, actions=None, screenshot=None, persistent=None):
    started = time.time()
    s = ck.spec(service)
    if not s:
        return {"ok": False, "error": "unknown service '%s'" % service,
                "known": sorted(ck.SERVICES.keys())}
    target = url or s["home"]
    eng = engine()
    out = {"ok": False, "service": service.lower(), "engine": eng,
           "headless": headless(), "url": target, "proxy": bool(proxy())}
    handle = None
    cm = None
    pw = browser = None
    try:
        eng, launched = await _launch(eng, persistent=persistent)
        out["engine"] = eng
        if eng == "camoufox":
            cm = launched
            obj = await cm.__aenter__()
            if hasattr(obj, "add_cookies"):
                ctx = obj
            else:
                browser = obj
                ctx = await obj.new_context()
        else:
            pw, browser, ctx = launched
        try:
            inj = await ck.apply_to_context(ctx, service)
            out["injected"] = inj
            page = ctx.pages[0] if getattr(ctx, "pages", None) else await ctx.new_page()
            await page.goto(target, wait_until="domcontentloaded", timeout=int(timeout_s() * 1000))
            try:
                await page.wait_for_timeout(3500)
            except Exception:
                pass
            out["final_url"] = page.url
            try:
                out["title"] = await page.title()
            except Exception:
                out["title"] = None
            state = await _session_state(ctx, page, service)
            out.update(state)
            out["handle"] = ck.handle(service)
            if actions:
                out["actions"] = await actions(page, ctx)
            if screenshot:
                try:
                    await page.screenshot(path=screenshot, full_page=False)
                    out["screenshot"] = screenshot
                except Exception as exc:
                    out["screenshot_error"] = str(exc)
        finally:
            if eng == "camoufox":
                if browser is not None:
                    try:
                        await browser.close()
                    except Exception:
                        pass
                try:
                    await cm.__aexit__(None, None, None)
                except Exception:
                    pass
            else:
                try:
                    await browser.close()
                    await pw.stop()
                except Exception:
                    pass
        out["ok"] = bool(out.get("logged_in"))
        if not out["ok"] and out.get("session_cookie"):
            out["ok"] = False
            out["reason"] = "session cookie present but server still redirects to login (cookie expired?)"
        elif not out.get("session_cookie"):
            out["reason"] = "session cookie (%s) missing from file" % ", ".join(s.get("session") or [])
    except Exception as exc:
        out["error"] = "%s: %s" % (type(exc).__name__, exc)
    out["elapsed"] = round(time.time() - started, 2)
    return out


def connect(service, url=None, screenshot=None, persistent=None):
    return asyncio.run(_drive(service, url=url, screenshot=screenshot, persistent=persistent))


def _follow_actions(target):
    async def act(page, ctx):
        clean = target.lstrip("@").strip()
        await page.goto("https://x.com/%s" % clean, wait_until="domcontentloaded",
                        timeout=int(timeout_s() * 1000))
        try:
            await page.wait_for_timeout(4000)
        except Exception:
            pass
        follow = page.locator('[data-testid$="-follow"]').first
        unfollow = page.locator('[data-testid$="-unfollow"]').first
        res = {"target": clean, "final_url": page.url}
        try:
            if await unfollow.count() and await unfollow.is_visible():
                res["state"] = "already-following"
                res["clicked"] = False
                return res
        except Exception:
            pass
        try:
            if await follow.count() and await follow.is_visible():
                await follow.click(timeout=15000)
                await page.wait_for_timeout(3000)
                res["state"] = "followed"
                res["clicked"] = True
                return res
        except Exception as exc:
            res["state"] = "click-failed"
            res["error"] = "%s: %s" % (type(exc).__name__, exc)
            return res
        res["state"] = "no-follow-button"
        res["clicked"] = False
        return res
    return act


def follow(target, screenshot=None):
    return asyncio.run(_drive("x", actions=_follow_actions(target), screenshot=screenshot))


HEAVY = ("image", "media", "font")


def _clean_cookies(rows):
    keep = ("name", "value", "domain", "path", "expires", "httpOnly", "secure", "sameSite")
    out = []
    for c in rows or []:
        if not c.get("name"):
            continue
        d = {k: c[k] for k in keep if k in c}
        if not d.get("domain"):
            d["domain"] = ".gleam.io"
        if not d.get("path"):
            d["path"] = "/"
        out.append(d)
    return out


def _gleam_login_actions(campaign, cookie_out, log_path=None):
    async def act(page, ctx):
        out = {"steps": []}

        def lg(msg):
            if not log_path:
                return
            with open(log_path, "a") as fh:
                fh.write("%s\n" % msg)

        async def guard(route):
            try:
                if route.request.resource_type in HEAVY:
                    await route.abort()
                else:
                    await route.continue_()
            except Exception:
                pass

        await ctx.route("**/*", guard)
        for _ in range(20):
            t = await page.title() or ""
            if "just a moment" not in t.lower():
                break
            await page.wait_for_timeout(2000)

        tw = None
        for _ in range(30):
            ctl = await page.evaluate("""() => Array.from(document.querySelectorAll('a,button')).map((el, i) => ({
                i, text: (el.innerText || '').trim().slice(0, 40), cls: (el.className || '').toString() }))""")
            for c in ctl:
                if "twitter" in (str(c.get("text")) + str(c.get("cls"))).lower():
                    tw = c
                    break
            if tw:
                break
            await page.wait_for_timeout(2000)
        if not tw:
            out["error"] = "Login with Twitter button not found"
            return out
        out["login_button"] = tw

        async with ctx.expect_page(timeout=60000) as pinfo:
            await page.evaluate("""(i) => { const el = document.querySelectorAll('a,button')[i];
                el.scrollIntoView({block:'center'}); el.click(); }""", tw["i"])
        popup = await pinfo.value
        lg("popup %s" % popup.url[:120])

        for _ in range(40):
            try:
                u = popup.url
            except Exception:
                break
            if "x.com" in u and "authorize" in u:
                break
            await popup.wait_for_timeout(1500)
        await popup.wait_for_timeout(9000)

        advanced = False
        import re as _re
        for attempt in range(5):
            try:
                loc = popup.get_by_role("button", name=_re.compile("authorize app", _re.I)).first
                if await loc.count():
                    await loc.click(timeout=8000)
            except Exception:
                pass
            try:
                await popup.wait_for_url(_re.compile(r"resume_oauth|gleam\.io"), timeout=12000)
                advanced = True
                out["steps"].append("oauth-ok:%d" % attempt)
                break
            except Exception:
                try:
                    await popup.wait_for_timeout(3000)
                except Exception:
                    break
        out["oauth_ok"] = advanced
        if not advanced:
            out["error"] = "authorize failed"
            return out

        await page.wait_for_timeout(4000)
        try:
            await page.reload(wait_until="domcontentloaded")
        except Exception:
            pass
        for _ in range(20):
            t = await page.title() or ""
            if "just a moment" not in t.lower():
                break
            await page.wait_for_timeout(2000)
        await page.wait_for_timeout(6000)

        rows = [c for c in await ctx.cookies() if "gleam" in (c.get("domain") or "")]
        os.makedirs(os.path.dirname(cookie_out), exist_ok=True)
        import json as _json
        with open(cookie_out, "w") as fh:
            _json.dump(_clean_cookies(rows), fh, indent=2)
        out["cookie_file"] = cookie_out
        out["cookie_names"] = sorted(c["name"] for c in rows)
        try:
            from . import entry as _en
            h = _en.GleamHTTP()
            camp = h.campaign_meta(campaign)
            out["contestant"] = camp.get("contestant")
            out["x_linked"] = camp.get("x_linked")
        except Exception as exc:
            out["contestant_error"] = "%s: %s" % (type(exc).__name__, exc)
        lg("login done x=%s" % out.get("x_linked"))
        return out
    return act


def _x_action_actions(kind, url, text=None):
    async def act(page, ctx):
        res = {"kind": kind, "url": url}

        async def guard(route):
            if route.request.resource_type in HEAVY:
                return await route.abort()
            return await route.continue_()

        async def textarea_count():
            return await page.locator('[data-testid="tweetTextarea_0"]').count()

        try:
            await page.route("**/*", guard)
            await page.goto(url, wait_until="domcontentloaded", timeout=int(timeout_s() * 1000))
            await page.wait_for_timeout(6000)
            res["title"] = (await page.title())[:80]
            if kind == "retweet":
                unfollow = page.locator('[data-testid="unretweet"]').first
                if await unfollow.count() and await unfollow.is_visible():
                    res["state"] = "already-retweeted"
                    return res
                btn = page.locator('[data-testid="retweet"]').first
                if not await btn.count():
                    res["state"] = "no-retweet-button"
                    return res
                await btn.click(timeout=15000)
                await page.wait_for_timeout(2500)
                conf = page.locator('[data-testid="retweetConfirm"]').first
                if not await conf.count():
                    res["state"] = "no-confirm-menu"
                    return res
                await conf.click(timeout=15000)
                await page.wait_for_timeout(4000)
                res["state"] = "confirmed"
                return res
            if kind == "reply":
                btn = page.locator('[data-testid="reply"]').first
                if not await btn.count():
                    res["state"] = "no-reply-button"
                    return res
                await btn.click(timeout=15000)
                await page.wait_for_timeout(4000)
                await page.evaluate(
                    """() => { const t = document.querySelector('[data-testid=\\"tweetTextarea_0\\"]'); if (t) t.focus(); }""")
                await page.wait_for_timeout(800)
                await page.keyboard.type(text or "", delay=90)
                await page.wait_for_timeout(2000)
                res["typed"] = await page.evaluate(
                    """() => { const t = document.querySelector('[data-testid=\\"tweetTextarea_0\\"]'); return t ? t.innerText : null; }""")
                sent = await page.evaluate("""() => {
                    const b = document.querySelector('div[role=\\"dialog\\"] [data-testid=\\"tweetButton\\"]');
                    if (!b || b.disabled) return 'no-button';
                    b.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                    return 'dispatched';
                }""")
                res["dispatch"] = sent
                await page.wait_for_timeout(5000)
                if await textarea_count():
                    await page.keyboard.press("Control+Enter")
                    await page.wait_for_timeout(6000)
                res["state"] = "submitted" if not await textarea_count() else "modal-open"
                res["alerts"] = await page.evaluate(
                    """() => Array.from(document.querySelectorAll('[role=\\"alert\\"]')).map(e => (e.innerText||'').trim()).filter(Boolean)""")
                return res
            res["state"] = "unsupported"
        except Exception as exc:
            res["state"] = "error"
            res["error"] = "%s: %s" % (type(exc).__name__, str(exc)[:300])
        return res
    return act


def x_action(kind, url, text=None, screenshot=None):
    return asyncio.run(_drive("x", url=url, actions=_x_action_actions(kind, url, text),
                              screenshot=screenshot))


def gleam_login(campaign, cookie_out=None, screenshot=None, log_path=None, force=False):
    out_path = cookie_out or os.path.join(ck.session_dir(), "gleam_cookie.json")
    if not force:
        try:
            from . import entry as en
            meta = en.GleamHTTP().campaign_meta(campaign)
            if meta.get("x_linked") and (meta.get("contestant") or {}).get("id"):
                return {"ok": True, "skipped": "already linked",
                        "reason": "gleam session already has X linked; re-login creates a new contestant",
                        "cookie_file": out_path, "contestant": meta.get("contestant"),
                        "x_linked": meta.get("x_linked"), "campaign_key": meta.get("key")}
        except Exception:
            pass
    res = asyncio.run(_drive("x", url=campaign,
                             actions=_gleam_login_actions(campaign, out_path, log_path),
                             screenshot=screenshot))
    if res.get("actions", {}).get("oauth_ok") and not res.get("actions", {}).get("x_linked"):
        try:
            from . import entry as en
            meta = en.GleamHTTP().campaign_meta(campaign)
            res["actions"]["contestant"] = meta.get("contestant")
            res["actions"]["x_linked"] = meta.get("x_linked")
        except Exception:
            pass
    return res

