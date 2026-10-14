import os
import re


class EnvStore:
    def __init__(self, path=None, index=None):
        self.path = path or os.environ.get("GLEAM_ENV_FILE") or os.path.join(os.getcwd(), ".env")
        self.index = index
        self.data = {}
        self.load()

    def load(self):
        if not os.path.isfile(self.path):
            return
        with open(self.path, "r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[7:].strip()
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k:
                    self.data[k] = v

    def candidates(self, field, campaign_key=None):
        out = []
        if campaign_key:
            out.append("CAMPAIGN_%s_%s" % (campaign_key, field))
            out.append("CAMPAIGN_%s_%s" % (campaign_key.upper(), field))
        if self.index is not None:
            out.append("%s_%d" % (field, self.index))
        out.append(field)
        out.append("%s_DEFAULT" % field)
        if field.endswith("_UID") and field != "EXCHANGE_UID_DEFAULT":
            out.append("EXCHANGE_UID_DEFAULT")
        if field.startswith("WALLET_") and field != "WALLET_DEFAULT":
            out.append("WALLET_DEFAULT")
        if field == "CUSTOM_TEXT":
            out.append("PROMO_TEXT")
            out.append("COMMENT_TEXT")
        if field == "SUBMIT_URL":
            out.append("POST_URL")
            out.append("X_TWEET_URL")
        return out

    def resolve(self, field, campaign_key=None, validate=True):
        from . import keyspec
        for key in self.candidates(field, campaign_key):
            if key not in self.data:
                continue
            val = self.data[key]
            if val == "":
                continue
            if validate:
                ok, why = keyspec.validate(field, val)
                if not ok:
                    return {
                        "ok": False, "field": field, "key": key, "value": val,
                        "reason": why,
                    }
            return {"ok": True, "field": field, "key": key, "value": val, "reason": ""}
        return {"ok": False, "field": field, "key": None, "value": None, "reason": "not set in .env"}

    def inventory(self):
        from . import keyspec
        rows = []
        for k, v in sorted(self.data.items()):
            if not v:
                continue
            rows.append({"key": k, "kind": keyspec.guess_field(v) or "text", "len": len(v)})
        return rows

    def audit(self):
        from . import keyspec
        problems = []
        for k, v in sorted(self.data.items()):
            if not v:
                continue
            if k.startswith("CAMPAIGN_"):
                field = re.sub(r"^CAMPAIGN_[A-Za-z0-9]+_", "", k)
            elif re.match(r"^.+_\d+$", k):
                field = re.sub(r"_\d+$", "", k)
            else:
                field = k
            ok, why = keyspec.validate(field, v)
            if not ok:
                problems.append({"key": k, "why": why})
        return problems


def load_dotenv_into_env(path):
    store = EnvStore(path)
    for k, v in store.data.items():
        os.environ.setdefault(k, v)
    return store
