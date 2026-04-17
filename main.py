from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from urllib.parse import urlsplit
from functools import lru_cache
from pathlib import Path
from collections import OrderedDict
from threading import Lock
from time import monotonic
import ipaddress
import pandas as pd

try:
    from backend.model_loader import get_model, predict_url_probability
except ModuleNotFoundError:
    from model_loader import get_model, predict_url_probability


app = FastAPI()

TRUSTED_EXACT_HOSTS = {
    "github.com",
    "www.github.com",
    "accounts.github.com",
    "google.com",
    "www.google.com",
    "mail.google.com",
    "accounts.google.com",
    "youtube.com",
    "www.youtube.com",
    "paypal.com",
    "www.paypal.com",
    "accounts.paypal.com",
    "stackoverflow.com",
    "www.stackoverflow.com",
    "microsoft.com",
    "www.microsoft.com",
    "accounts.microsoft.com",
    "wix.com",
    "www.wix.com",
    "users.wix.com",
    "accounts.wix.com",
    "login.wix.com",
}

TRUSTED_SUFFIX_HOSTS = (
    ".github.com",
    ".google.com",
    ".youtube.com",
    ".paypal.com",
    ".stackoverflow.com",
    ".microsoft.com",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLEAN_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "training_data_clean.csv"
THRESHOLD_CONFIG_PATH = PROJECT_ROOT / "data" / "processed" / "threshold_config.json"

PREDICTION_CACHE_TTL_SECONDS = 90
PREDICTION_CACHE_MAX_ITEMS = 2048

_prediction_cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()
_prediction_cache_lock = Lock()


SUSPICIOUS_TOKENS = {
    "login",
    "signin",
    "sign-in",
    "verify",
    "verification",
    "secure",
    "update",
    "account",
    "password",
    "confirm",
    "auth",
    "billing",
    "invoice",
    "reset",
    "unlock",
    "mfa",
    "2fa",
    "otp",
    "wallet",
    "support",
}

SHORTENER_HINTS = (
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "rb.gy",
)

HOSTED_PLATFORM_HINTS = (
    "wixstudio.com",
    "wixsite.com",
    "webflow.io",
    "webnode.page",
    "weebly.com",
    "site123.me",
    "github.io",
    "netlify.app",
    "vercel.app",
    "pages.dev",
    "wordpress.com",
)


def get_hostname(url: str) -> str:
    try:
        return urlsplit(url).hostname or ""
    except Exception:
        return ""


@lru_cache(maxsize=1)
def get_threshold() -> float:
    """Load threshold from config when available; otherwise use recall-favoring default."""
    default_threshold = 0.95
    if not THRESHOLD_CONFIG_PATH.exists():
        return default_threshold

    try:
        cfg = pd.read_json(THRESHOLD_CONFIG_PATH, typ="series")
        value = float(cfg.get("threshold", default_threshold))
    except Exception:
        return default_threshold

    return max(0.5, min(0.999, value))


def _is_ip_host(hostname: str) -> bool:
    host = hostname.strip().lower()
    if not host:
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _suspicious_token_hits(url: str) -> list[str]:
    lowered = url.lower()
    return [token for token in sorted(SUSPICIOUS_TOKENS) if token in lowered]


def _subdomain_depth(hostname: str) -> int:
    host = hostname.strip(".")
    if not host:
        return 0
    parts = host.split(".")
    return max(len(parts) - 2, 0)


def _is_shortener_hint(hostname: str) -> bool:
    host = hostname.lower().strip()
    return any(host == hint or host.endswith(f".{hint}") for hint in SHORTENER_HINTS)


def _hosted_platform_hint(hostname: str) -> str:
    host = hostname.lower().strip()
    for hint in HOSTED_PLATFORM_HINTS:
        if host == hint or host.endswith(f".{hint}"):
            return hint
    return ""


def evaluate_heuristics(url: str, hostname: str) -> tuple[int, list[str], dict]:
    """Return heuristic risk score and explanations to improve live phishing recall."""
    score = 0
    reasons: list[str] = []
    lowered = url.lower()
    token_hits = _suspicious_token_hits(url)
    subdomain_depth = _subdomain_depth(hostname)
    ip_host = _is_ip_host(hostname)
    hosted_platform = _hosted_platform_hint(hostname)
    first_label = hostname.strip(".").lower().split(".")[0] if hostname.strip(".") else ""
    suspicious_hosted_subdomain = False

    if len(url) >= 90:
        score += 1
        reasons.append("URL is unusually long")

    if url.count(".") >= 4:
        score += 1
        reasons.append("URL has many dot segments")

    if subdomain_depth >= 3:
        score += 2
        reasons.append("Domain has deep subdomain nesting")

    if "@" in url:
        score += 3
        reasons.append("Contains '@' symbol")

    if "xn--" in lowered:
        score += 3
        reasons.append("Contains punycode marker")

    if "//" in lowered.split("://", 1)[-1]:
        score += 2
        reasons.append("Contains double slash path trick")

    redirect_markers = (
        "redirect=",
        "redir=",
        "url=",
        "next=",
        "target=",
        "continue=",
        "callback=",
    )
    if any(marker in lowered for marker in redirect_markers):
        score += 2
        reasons.append("Contains redirect-style query markers")

    if _is_shortener_hint(hostname):
        score += 1
        reasons.append("Uses URL shortener domain")

    if hosted_platform:
        score += 2
        reasons.append(f"Uses hosted platform domain ({hosted_platform})")

        if first_label:
            if "-" in first_label:
                score += 2
                suspicious_hosted_subdomain = True
                reasons.append("Hosted subdomain uses hyphenated branding")

            if len(first_label) >= 10:
                score += 1
                suspicious_hosted_subdomain = True
                reasons.append("Hosted subdomain is unusually long")

            if first_label.count("-") >= 2:
                score += 1
                suspicious_hosted_subdomain = True
                reasons.append("Hosted subdomain has multiple hyphens")

    if ip_host:
        score += 3
        reasons.append("Uses direct IP address host")

    if len(token_hits) >= 2:
        score += 2
        reasons.append("Contains multiple credential-related keywords")

    return score, reasons, {
        "subdomain_depth": subdomain_depth,
        "token_hits": token_hits,
        "ip_host": ip_host,
        "hosted_platform": bool(hosted_platform),
        "suspicious_hosted_subdomain": suspicious_hosted_subdomain,
    }


def is_trusted_host(hostname: str) -> bool:
    host = hostname.lower().strip()
    if not host:
        return False
    if host in TRUSTED_EXACT_HOSTS:
        return True
    if host in get_data_trusted_hosts():
        return True
    return any(host.endswith(suffix) for suffix in TRUSTED_SUFFIX_HOSTS)


@lru_cache(maxsize=1)
def get_data_trusted_hosts() -> set[str]:
    """Build a trusted host set from cleaned labels to cut false positives."""
    if not CLEAN_DATA_PATH.exists():
        return set()

    try:
        df = pd.read_csv(CLEAN_DATA_PATH, usecols=["url", "label"])
    except Exception:
        return set()

    def host_of(value: str) -> str:
        try:
            return (urlsplit(str(value)).hostname or "").lower().strip()
        except Exception:
            return ""

    df["host"] = df["url"].map(host_of)
    df = df[df["host"] != ""]
    if df.empty:
        return set()

    grouped = df.groupby("host")["label"].agg(["count", "sum"])
    grouped = grouped.rename(columns={"sum": "phishing_count"})
    grouped["phishing_ratio"] = grouped["phishing_count"] / grouped["count"]

    # A host is trusted if it appears enough times and is mostly/fully legitimate.
    trusted = grouped[
        (grouped["count"] >= 5)
        & (grouped["phishing_ratio"] <= 0.02)
    ]
    return set(trusted.index.tolist())


class URLRequest(BaseModel):
    url: str


def _cache_get(url: str) -> dict | None:
    now = monotonic()
    with _prediction_cache_lock:
        item = _prediction_cache.get(url)
        if item is None:
            return None

        expires_at, payload = item
        if now >= expires_at:
            _prediction_cache.pop(url, None)
            return None

        # LRU touch: keep hot keys near the tail.
        _prediction_cache.move_to_end(url)
        return payload.copy()


def _cache_set(url: str, payload: dict) -> None:
    expires_at = monotonic() + PREDICTION_CACHE_TTL_SECONDS
    with _prediction_cache_lock:
        _prediction_cache[url] = (expires_at, payload.copy())
        _prediction_cache.move_to_end(url)

        # Remove expired entries first (cheap cleanup while mutating).
        now = monotonic()
        expired_keys = [
            key for key, (entry_expires_at, _) in _prediction_cache.items()
            if entry_expires_at <= now
        ]
        for key in expired_keys:
            _prediction_cache.pop(key, None)

        while len(_prediction_cache) > PREDICTION_CACHE_MAX_ITEMS:
            _prediction_cache.popitem(last=False)


@app.post("/predict")
def predict(data: URLRequest):
    url = str(data.url).strip()
    cached = _cache_get(url)
    if cached is not None:
        return cached

    model = get_model()
    proba = predict_url_probability(model, url)
    hostname = get_hostname(url)

    # Check trusted hosts early to always bypass phishing checks.
    has_spoof_marker = ("@" in url) or ("xn--" in hostname)
    if is_trusted_host(hostname) and not has_spoof_marker:
        response = {
            "prediction": 0,
            "confidence": min(proba, 0.25),
            "explanation": ["Trusted domain matched"],
        }
        _cache_set(url, response)
        return response

    # Realtime mode favors recall over extreme precision to avoid missing live phishing pages.
    threshold = max(0.9, min(get_threshold(), 0.97))
    heuristic_score, heuristic_reasons, heuristic_meta = evaluate_heuristics(url, hostname)

    # Promote risky URLs even when model probability is slightly below threshold.
    heuristic_trigger = (
        heuristic_score >= 7
        or (heuristic_score >= 5 and proba >= 0.7)
        or (heuristic_meta["ip_host"] and proba >= 0.55)
        or (
            heuristic_meta["hosted_platform"]
            and heuristic_meta["suspicious_hosted_subdomain"]
            and proba >= 0.25
        )
    )

    prediction = 1 if (proba >= threshold or heuristic_trigger) else 0
    confidence = max(proba, 0.86) if heuristic_trigger and proba < threshold else proba

    explanation: list[str] = list(dict.fromkeys(heuristic_reasons))

    if prediction == 1 and not explanation:
        explanation.append("Suspicious pattern detected")

    if prediction == 0:
        if not explanation:
            explanation = ["No major security issues detected"]

    response = {
        "prediction": prediction,
        "confidence": confidence,
        "explanation": explanation,
    }

    _cache_set(url, response)
    return response


@app.exception_handler(RuntimeError)
def runtime_error_handler(_, exc: RuntimeError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})