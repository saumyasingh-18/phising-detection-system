import re
from collections import Counter
from functools import lru_cache
from math import log2
from urllib.parse import urlparse


FEATURE_NAMES = [
    "url_length",
    "dot_count",
    "has_https",
    "has_at_symbol",
    "hyphen_count",
    "domain_length",
    "path_length",
    "has_digit",
    "query_param_count",
    "has_login",
    "has_secure",
    "has_verify",
    "subdomain_depth",
    "url_entropy",
    "suspicious_token_count",
    "is_shortener",
    "has_redirect_param",
    "is_punycode",
    "domain_age_days",
]


SUSPICIOUS_TOKENS = {
    "login",
    "signin",
    "sign-in",
    "verify",
    "verification",
    "secure",
    "update",
    "account",
    "bank",
    "paypal",
    "password",
    "confirm",
    "redirect",
    "session",
    "auth",
    "webscr",
    "billing",
    "invoice",
    "reset",
    "unlock",
    "oauth",
}

SHORTENER_DOMAINS = {
    "bit.ly",
    "goo.gl",
    "t.co",
    "tinyurl.com",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "rebrand.ly",
    "cutt.ly",
    "rb.gy",
    "s.id",
    "tr.ee",
    "bitly.ws",
    "tiny.cc",
    "shorturl.at",
}


def _safe_lower(value: str) -> str:
    return str(value or "").lower()


def _subdomain_depth(hostname: str) -> int:
    host = hostname.strip(".")
    if not host:
        return 0
    parts = host.split(".")
    return max(len(parts) - 2, 0)


def _url_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = Counter(text)
    length = len(text)
    return -sum((count / length) * log2(count / length) for count in counts.values())


def _suspicious_token_count(url: str) -> int:
    lowered = _safe_lower(url)
    return sum(1 for token in SUSPICIOUS_TOKENS if token in lowered)


def _is_shortener(parsed_url) -> int:
    hostname = (parsed_url.hostname or "").lower().strip()
    if hostname in SHORTENER_DOMAINS:
        return 1
    return int(any(hostname.endswith(f".{domain}") for domain in SHORTENER_DOMAINS))


def _has_redirect_param(url: str) -> int:
    lowered = _safe_lower(url)
    redirect_keys = (
        "redirect=",
        "redir=",
        "url=",
        "next=",
        "target=",
        "dest=",
        "destination=",
        "goto=",
        "return=",
        "continue=",
        "callback=",
        "forward=",
        "out=",
    )
    return int(any(key in lowered for key in redirect_keys))


def _is_punycode(parsed_url) -> int:
    hostname = (parsed_url.hostname or "").lower()
    return int(hostname.startswith("xn--") or ".xn--" in hostname)


@lru_cache(maxsize=1024)
def _domain_age_days(hostname: str) -> int:
    """Best-effort domain age lookup. Returns 0 when unavailable."""
    host = hostname.lower().strip()
    if not host:
        return 0

    # Optional dependency path. If the package is missing, return 0 cleanly.
    try:
        import whois  # type: ignore
    except Exception:
        return 0

    try:
        record = whois.whois(host)
        creation_date = getattr(record, "creation_date", None)
        if isinstance(creation_date, list):
            creation_date = creation_date[0] if creation_date else None
        if creation_date is None:
            return 0

        from datetime import datetime, timezone

        if getattr(creation_date, "tzinfo", None) is None:
            creation_date = creation_date.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max((now - creation_date).days, 0)
    except Exception:
        return 0


def extract_features(url):
    url = str(url)
    try:
        parsed = urlparse(url)
    except ValueError:
        # Some raw rows contain malformed URLs; treat them as plain strings.
        parsed = urlparse("")

    features = []

    # Basic features
    features.append(len(url))                    # URL length
    features.append(url.count("."))              # dots
    features.append(1 if "https" in url else 0)  # https
    features.append(1 if "@" in url else 0)      # @ symbol
    features.append(url.count("-"))              # hyphens

    # 🔥 Advanced features (IMPORTANT)
    features.append(len(parsed.netloc))          # domain length
    features.append(len(parsed.path))            # path length
    features.append(1 if re.search(r'\d', url) else 0)  # digits
    features.append(url.count("="))              # query params
    features.append(1 if "login" in url.lower() else 0)
    features.append(1 if "secure" in url.lower() else 0)
    features.append(1 if "verify" in url.lower() else 0)
    features.append(_subdomain_depth(parsed.hostname or ""))
    features.append(round(_url_entropy(url), 6))
    features.append(_suspicious_token_count(url))
    features.append(_is_shortener(parsed))
    features.append(_has_redirect_param(url))
    features.append(_is_punycode(parsed))
    features.append(_domain_age_days(parsed.hostname or ""))

    return features