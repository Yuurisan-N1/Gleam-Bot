import html
import json
import re


def _extract_balanced(text, start):
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def parse_campaign(page):
    if isinstance(page, bytes):
        page = page.decode("utf-8", "replace")
    marker = "initCampaign("
    idx = page.find(marker)
    if idx < 0:
        return None
    blob = _extract_balanced(page, idx + len(marker))
    if not blob:
        return None
    data = json.loads(html.unescape(blob))
    camp = dict(data.get("campaign") or {})
    camp["entry_methods"] = data.get("entry_methods") or []
    camp["incentive"] = data.get("incentive") or {}
    camp["_root_keys"] = sorted(data.keys())
    return camp


def entry_methods(campaign):
    for k in ("entry_methods", "entryMethods", "entries"):
        v = campaign.get(k)
        if isinstance(v, list):
            return v
    return []


def campaign_key(campaign):
    return campaign.get("key") or campaign.get("short") or ""


def short_summary(campaign):
    ets = entry_methods(campaign)
    return {
        "name": campaign.get("name"),
        "key": campaign_key(campaign),
        "starts_at": campaign.get("starts_at"),
        "ends_at": campaign.get("ends_at"),
        "n_methods": len(ets),
        "types": [e.get("entry_type") for e in ets],
    }


def find_json_urls(page):
    return sorted(set(re.findall(r"https?://[^\"'\s]+\.json[^\"'\s]*", page)))
