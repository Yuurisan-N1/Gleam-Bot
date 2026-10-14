import re
import html

from . import keyspec


def clean(text):
    if text is None:
        return ""
    t = html.unescape(str(text))
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def field_for(entry):
    et = (entry.get("entry_type") or "").strip()
    cfg1 = entry.get("config1")
    cfg3 = entry.get("config3")
    cfg4 = entry.get("config4")
    desc = entry.get("action_description")
    label = " ".join([clean(cfg1), clean(cfg3), clean(cfg4), clean(desc)])

    if et == "wallet_address":
        return keyspec.wallet_field(cfg3), "chain:%s" % keyspec.norm_chain(cfg3)

    if et == "custom_action":
        hit = keyspec.detect_intent(label)
        if hit:
            return hit, "intent:%s" % hit
        if keyspec.is_no_data(label) or clean(entry.get("config2")).startswith("visit-"):
            return None, "visit-only"
        return None, "unknown custom_action"

    if et == "submit_url":
        dom = keyspec.norm_chain(cfg3)
        return "SUBMIT_URL", "domain:%s" % dom if dom else "submit_url"

    if et == "post_url":
        return "POST_URL", "post_url"

    if et == "upload_action":
        return "UPLOAD_FILE", "upload_action"

    if et in keyspec.ENTRY_TYPE_MAP:
        return keyspec.ENTRY_TYPE_MAP[et], "entry_type"

    hit = keyspec.detect_intent(label)
    if hit:
        return hit, "fallback-intent:%s" % hit
    if keyspec.is_no_data(label):
        return None, "visit-only"
    return None, "unmapped entry_type"


def resolve_entry(entry, store, campaign_key=None):
    field, how = field_for(entry)
    row = {
        "entry_type": entry.get("entry_type"),
        "worth": entry.get("worth"),
        "mandatory": entry.get("mandatory"),
        "requires_auth": entry.get("requires_authentication"),
        "api_denied": entry.get("api_denied"),
        "label": clean(entry.get("config1"))[:70],
        "chain": clean(entry.get("config3"))[:30],
        "field": field,
        "how": how,
        "value": None,
        "key": None,
        "status": "no-data",
        "note": "",
    }
    if field is None:
        row["status"] = "visit-only" if how == "visit-only" else "no-data"
        row["note"] = "visit only, no data needed" if how == "visit-only" else how
        return row

    if entry.get("api_denied"):
        row["status"] = "auth-only"
        row["note"] = "gleam api_denied -> needs real login session"

    res = store.resolve(field, campaign_key)
    if res["ok"]:
        row["value"] = res["value"]
        row["key"] = res["key"]
        row["status"] = "auth-only" if entry.get("api_denied") else "ready"
        row["note"] = ("ready to send via %s" % res["key"]) if not entry.get("api_denied") else row["note"]
    else:
        row["status"] = "auth-only" if entry.get("api_denied") else "missing"
        row["note"] = res["reason"]
    return row


def resolve_campaign(campaign, store):
    key = campaign.get("key") or campaign.get("short")
    out = {
        "campaign": campaign.get("name"),
        "key": key,
        "entries": [],
        "ready": 0,
        "missing": 0,
        "auth_only": 0,
        "visit_only": 0,
        "no_data": 0,
        "need_keys": [],
    }
    counters = {"ready": "ready", "missing": "missing", "auth-only": "auth_only",
                "visit-only": "visit_only", "no-data": "no_data"}
    for e in campaign.get("entry_methods") or []:
        row = resolve_entry(e, store, key)
        out["entries"].append(row)
        bucket = counters.get(row["status"])
        if bucket:
            out[bucket] += 1
        if row["status"] == "missing" and row["field"]:
            out["need_keys"].append(row["field"])
    out["need_keys"] = sorted(set(out["need_keys"]))
    out["actionable"] = out["ready"] + out["visit_only"]
    out["n_methods"] = len(out["entries"])
    return out
