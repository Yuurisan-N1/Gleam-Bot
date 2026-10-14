import re

EVM_RE = r"^0x[0-9a-fA-F]{40}$"
BTC_RE = r"^(?:[13]{1}[a-km-zA-HJ-NP-Z1-9]{26,33}|bc1[a-z0-9]{39,59})$"
BEP2_RE = r"^bnb1[0-9a-z]{38}$"
SOL_RE = r"^[1-9A-HJ-NP-Za-km-z]{32,44}$"
TON_RE = r"^[EU]Q[A-Za-z0-9_\-]{46}$"
TRON_RE = r"^T[1-9A-HJ-NP-Za-km-z]{33}$"
XRP_RE = r"^r[1-9A-HJ-NP-Za-km-z]{24,34}$"
XLM_RE = r"^G[A-Z2-7]{55}$"
SUI_RE = r"^0x[0-9a-fA-F]{64}$"
NEAR_RE = r"^[a-z0-9._\-]{2,64}\.(near|testnet)$"
ADA_RE = r"^addr1[a-z0-9]{20,}$"
DOGE_RE = r"^D[5-9A-HJ-NP-U][1-9A-HJ-NP-Za-km-z]{32}$"
LTC_RE = r"^(?:L[a-km-zA-HJ-NP-Z1-9]{26,33}|ltc1[a-z0-9]{39,59})$"
ATOM_RE = r"^cosmos1[a-z0-9]{38}$"
DOT_RE = r"^1[a-km-zA-HJ-NP-Z1-9]{45,47}$"
EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$"
URL_RE = r"^https?://[^\s]+$"
UID_RE = r"^[0-9]{3,20}$"
PHONE_RE = r"^\+?[0-9]{6,15}$"
HANDLE_RE = r"^@?[A-Za-z0-9._\-]{2,40}$"

WALLET_CHAIN = {
    "ETH / BEP-20": "WALLET_EVM",
    "ETH": "WALLET_EVM",
    "ERC-20": "WALLET_EVM",
    "ERC20": "WALLET_EVM",
    "BEP-20": "WALLET_EVM",
    "BEP20": "WALLET_EVM",
    "EVM": "WALLET_EVM",
    "POLYGON": "WALLET_EVM",
    "BASE": "WALLET_EVM",
    "ARBITRUM": "WALLET_EVM",
    "OPTIMISM": "WALLET_EVM",
    "BTC": "WALLET_BTC",
    "BITCOIN": "WALLET_BTC",
    "BEP-2": "WALLET_BEP2",
    "BEP2": "WALLET_BEP2",
    "SOL": "WALLET_SOL",
    "SOLANA": "WALLET_SOL",
    "TON": "WALLET_TON",
    "TRON": "WALLET_TRON",
    "TRC-20": "WALLET_TRON",
    "TRC20": "WALLET_TRON",
    "XRP": "WALLET_XRP",
    "XLM": "WALLET_XLM",
    "STELLAR": "WALLET_XLM",
    "SUI": "WALLET_SUI",
    "APT": "WALLET_APT",
    "APTOS": "WALLET_APT",
    "NEAR": "WALLET_NEAR",
    "ADA": "WALLET_ADA",
    "CARDANO": "WALLET_ADA",
    "DOGE": "WALLET_DOGE",
    "LTC": "WALLET_LTC",
    "ATOM": "WALLET_ATOM",
    "COSMOS": "WALLET_ATOM",
    "DOT": "WALLET_DOT",
    "POLKADOT": "WALLET_DOT",
    "OTHER": "WALLET_OTHER",
    "": "WALLET_DEFAULT",
}

WALLET_RE = {
    "WALLET_EVM": EVM_RE,
    "WALLET_BTC": BTC_RE,
    "WALLET_BEP2": BEP2_RE,
    "WALLET_SOL": SOL_RE,
    "WALLET_TON": TON_RE,
    "WALLET_TRON": TRON_RE,
    "WALLET_XRP": XRP_RE,
    "WALLET_XLM": XLM_RE,
    "WALLET_SUI": SUI_RE,
    "WALLET_APT": SUI_RE,
    "WALLET_NEAR": NEAR_RE,
    "WALLET_ADA": ADA_RE,
    "WALLET_DOGE": DOGE_RE,
    "WALLET_LTC": LTC_RE,
    "WALLET_ATOM": ATOM_RE,
    "WALLET_DOT": DOT_RE,
}

ENTRY_TYPE_MAP = {
    "email_subscribe": "EMAIL",
    "gleam_subscribe": "EMAIL",
    "verify_phone": "PHONE",
    "twitter_follow": "X_USERNAME",
    "twitter_retweet": "X_RETWEET_URL",
    "twitter_tweet": "TWEET_TEXT",
    "twitter_hashtags": "TWEET_TEXT",
    "twitter_media": "X_USERNAME",
    "youtube_subscribe": "YOUTUBE_CHANNEL_URL",
    "youtube_video": "YOUTUBE_VIDEO_URL",
    "twitchtv_follow": "TWITCH_USERNAME",
    "twitchtv_subscribe": "TWITCH_USERNAME",
    "twitchtv_channel_reward": "TWITCH_USERNAME",
    "tiktok_follow": "TIKTOK_USERNAME",
    "instagram_visit_profile": "INSTAGRAM_USERNAME",
    "instagram_media_post": "INSTAGRAM_PROFILE_URL",
    "instagram_media_reel": "INSTAGRAM_PROFILE_URL",
    "kick_follow": "KICK_USERNAME",
    "linkedin_follow": "LINKEDIN_URL",
    "linkedin_share": "LINKEDIN_URL",
    "facebook_share": "FACEBOOK_POST_URL",
    "facebook_view_post": "FACEBOOK_POST_URL",
    "messenger_subscribe": "MESSENGER_URL",
    "discord_join_server": "DISCORD_SERVER_INVITE",
    "telegram_join": "TELEGRAM_USERNAME",
    "telegram_view_post": "TELEGRAM_CHANNEL_URL",
    "bluesky_like": "BLUESKY_HANDLE",
    "bluesky_post": "BLUESKY_HANDLE",
    "bluesky_repost": "BLUESKY_HANDLE",
    "soundcloud_follow": "SOUNDCLOUD_URL",
    "soundcloud_like": "SOUNDCLOUD_URL",
    "soundcloud_repost": "SOUNDCLOUD_URL",
    "substack_subscribe": "SUBSTACK_URL",
    "pinterest_choose_board": "PINTEREST_URL",
    "steam": "STEAM_ID",
    "download_app": "APP_DOWNLOAD_URL",
    "share_action": "REFERRAL_LINK",
    "coupon_action": "COUPON_CODE",
    "submit_url": "SUBMIT_URL",
    "post_url": "POST_URL",
    "media_action": "POST_URL",
    "media_object_post": "POST_URL",
    "media_object_photo": "POST_URL",
    "media_object_video": "POST_URL",
    "upload_action": "UPLOAD_FILE",
    "typeform_completed": "CUSTOM_TEXT",
    "custom_action": "CUSTOM_TEXT",
    "wallet_address": "WALLET_DEFAULT",
}

EXCHANGES = ("KUCOIN", "BINANCE", "OKX", "BYBIT", "GATE", "BITGET", "MEXC", "HTX", "KRAKEN", "UPHOLD")

INTENT_RULES = [
    (r"kucoin\s*(uid|kcuid)|kcuid", "KUCOIN_UID"),
    (r"binance\s*uid", "BINANCE_UID"),
    (r"okx\s*uid", "OKX_UID"),
    (r"bybit\s*uid", "BYBIT_UID"),
    (r"gate\s*uid", "GATE_UID"),
    (r"bitget\s*uid", "BITGET_UID"),
    (r"mexc\s*uid", "MEXC_UID"),
    (r"htx\s*uid", "HTX_UID"),
    (r"kraken\s*uid", "KRAKEN_UID"),
    (r"uphold\s*uid", "UPHOLD_UID"),
    (r"submit\s+(your\s+)?uid|your\s+uid|account\s+uid", "EXCHANGE_UID_DEFAULT"),
    (r"link\s+to\s+your\s+comment|comment\s+(url|link)|your\s+comment\s+below", "COMMENT_URL"),
    (r"link\s+to\s+your\s+tweet|tweet\s+(url|link)|your\s+tweet\s+below", "X_TWEET_URL"),
    (r"submit\s+the\s+link|link\s+to\s+your\s+(post|video)", "SUBMIT_URL"),
    (r"evm\s*address|bep-?20|erc-?20|eth\s*address|0x", "WALLET_EVM"),
    (r"solana|sol\s*address", "WALLET_SOL"),
    (r"bitcoin|btc\s*address", "WALLET_BTC"),
    (r"\bton\b|ton\s*address", "WALLET_TON"),
    (r"tron|trc-?20", "WALLET_TRON"),
    (r"wallet\s*address|wallet\b", "WALLET_DEFAULT"),
    (r"coupon", "COUPON_CODE"),
    (r"promo\s*code|promocode", "PROMO_CODE"),
    (r"secret\s*code|enter\s*the\s*code|invite\s*code", "SECRET_CODE"),
    (r"referral\s*(code|link)", "REFERRAL_CODE"),
    (r"e-?mail", "EMAIL"),
    (r"telegram\s*(username|handle)", "TELEGRAM_USERNAME"),
    (r"(x|twitter)\s*(username|handle)", "X_USERNAME"),
    (r"discord\s*(username|handle|id)", "DISCORD_USERNAME"),
    (r"youtube\s*(channel|name)", "YOUTUBE_CHANNEL_URL"),
    (r"tiktok\s*(username|handle)", "TIKTOK_USERNAME"),
    (r"instagram\s*(username|handle)", "INSTAGRAM_USERNAME"),
    (r"twitch\s*(username|handle)", "TWITCH_USERNAME"),
    (r"quiz|answer|trivia", "QUIZ_ANSWER"),
    (r"feedback|suggestion|tell\s*us|why\s+you|what\s+do\s+you|comment|thoughts|excited", "CUSTOM_TEXT"),
    (r"hashtag", "HASHTAG_TEXT"),
]

NO_DATA_INTENT = [
    r"visit\s+this|visit\s+the|create\s+your\s+\w+\s+account|join\s+the\s+space|join\s+space",
    r"check-?in|daily\s+check|days\s+check|follow\s+us|watch\s+the|read\s+the",
]


def norm_chain(cfg3):
    if not cfg3:
        return ""
    key = str(cfg3).strip().upper()
    key = re.sub(r"\s+", " ", key)
    return key


def wallet_field(cfg3):
    k = norm_chain(cfg3)
    if k in WALLET_CHAIN:
        return WALLET_CHAIN[k]
    for name, field in WALLET_CHAIN.items():
        if name and name in k:
            return field
    return "WALLET_DEFAULT"


def is_no_data(text):
    if not text:
        return False
    t = re.sub(r"<[^>]+>", " ", str(text).lower())
    return any(re.search(pat, t) for pat in NO_DATA_INTENT)


def detect_intent(text):
    if not text:
        return None
    t = str(text).lower()
    t = re.sub(r"<[^>]+>", " ", t)
    if is_no_data(t):
        return None
    for pat, field in INTENT_RULES:
        if re.search(pat, t):
            return field
    return None


def validate(field, value):
    if value is None or str(value).strip() == "":
        return False, "empty"
    v = str(value).strip()
    if field in WALLET_RE:
        ok = re.match(WALLET_RE[field], v) is not None
        return ok, "wallet format %s mismatch" % field if not ok else ""
    if field.startswith(("WALLET_",)) or field == "WALLET_DEFAULT":
        ok = re.match(EVM_RE, v) or re.match(SOL_RE, v) or re.match(BTC_RE, v)
        return bool(ok), "unrecognized address format" if not ok else ""
    if field.endswith("_UID"):
        ok = re.match(UID_RE, v) is not None
        return ok, "UID must be 3-20 digits" if not ok else ""
    if "EMAIL" in field:
        ok = re.match(EMAIL_RE, v) is not None
        return ok, "invalid email" if not ok else ""
    if field.endswith("_URL") or field in ("SUBMIT_URL", "POST_URL"):
        ok = re.match(URL_RE, v) is not None
        return ok, "URL must be http(s)://" if not ok else ""
    if field == "PHONE":
        ok = re.match(PHONE_RE, v) is not None
        return ok, "invalid phone number" if not ok else ""
    return True, ""


def guess_field(value):
    v = str(value).strip()
    if re.match(EVM_RE, v):
        return "WALLET_EVM"
    if re.match(TON_RE, v):
        return "WALLET_TON"
    if re.match(TRON_RE, v):
        return "WALLET_TRON"
    if re.match(BEP2_RE, v):
        return "WALLET_BEP2"
    if re.match(XRP_RE, v):
        return "WALLET_XRP"
    if re.match(XLM_RE, v):
        return "WALLET_XLM"
    if re.match(BTC_RE, v):
        return "WALLET_BTC"
    if re.match(SOL_RE, v):
        return "WALLET_SOL"
    if re.match(EMAIL_RE, v):
        return "EMAIL"
    if re.match(UID_RE, v):
        return "EXCHANGE_UID_DEFAULT"
    if re.match(URL_RE, v):
        return "SUBMIT_URL"
    return None
