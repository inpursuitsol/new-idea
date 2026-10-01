from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_TRADE_FILE = Path(os.environ.get("TV_TRADE_FILE", "trade.yaml"))


def _bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _csv(raw: str) -> tuple[str, ...]:
    raw = (raw or "").strip()
    if not raw:
        return ()
    return tuple(part.strip().upper() for part in raw.split(",") if part.strip())


def _file_values() -> dict:
    if not _TRADE_FILE.exists():
        return {}
    loaded = yaml.safe_load(_TRADE_FILE.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        return {}
    return loaded


@dataclass(frozen=True)
class Settings:
    """Runtime settings. Practice/dry-run is on unless you opt in."""

    broker: str = "upstox"
    kite_api_key: str = ""
    kite_api_secret: str = ""
    upstox_api_key: str = ""
    upstox_api_secret: str = ""
    upstox_redirect_uri: str = "http://127.0.0.1:8080/upstox/callback"
    upstox_instrument_key: str = ""
    access_token_path: Path = Path(".broker_access_token")
    webhook_secret: str = ""
    host: str = "127.0.0.1"
    port: int = 8080
    dry_run: bool = True
    default_exchange: str = "NSE"
    default_product: str = "MIS"
    default_order_type: str = "MARKET"
    default_symbol: str = ""
    default_quantity: int = 1
    max_quantity: int = 50
    allowed_symbols: tuple[str, ...] = field(default_factory=tuple)
    allowed_exchanges: tuple[str, ...] = ("NSE", "BSE", "NFO", "BFO", "MCX")
    variety: str = "regular"
    public_base_url: str = ""

    @classmethod
    def from_env(cls) -> Settings:
        file_vals = _file_values()

        def pick(env_name: str, *file_keys: str, default: str = "") -> str:
            env = os.environ.get(env_name)
            if env is not None and str(env).strip() != "":
                return str(env).strip()
            for key in file_keys:
                if key in file_vals and file_vals[key] not in (None, ""):
                    return str(file_vals[key]).strip()
            return default

        practice = file_vals.get("practice")
        dry_run = _bool(os.environ.get("TV_ZERODHA_DRY_RUN"), _bool(practice, True))
        if os.environ.get("TV_PRACTICE") is not None:
            dry_run = _bool(os.environ.get("TV_PRACTICE"), dry_run)

        token_path = pick("KITE_ACCESS_TOKEN_PATH", "access_token_path", default=".broker_access_token")
        qty = pick("TV_DEFAULT_QUANTITY", "quantity", default="1")
        max_qty = pick("TV_MAX_QUANTITY", "max_quantity", default="50")
        port = pick("TV_WEBHOOK_PORT", "port", default="8080")

        allowed = os.environ.get("TV_ALLOWED_SYMBOLS")
        allowed_symbols = _csv(allowed) if allowed is not None else _csv(str(file_vals.get("allowed_symbols") or ""))

        return cls(
            broker=pick("TV_BROKER", "broker", default="upstox").lower(),
            kite_api_key=pick("KITE_API_KEY", "kite_api_key"),
            kite_api_secret=pick("KITE_API_SECRET", "kite_api_secret"),
            upstox_api_key=pick("UPSTOX_API_KEY", "upstox_api_key"),
            upstox_api_secret=pick("UPSTOX_API_SECRET", "upstox_api_secret"),
            upstox_redirect_uri=pick(
                "UPSTOX_REDIRECT_URI",
                "upstox_redirect_uri",
                default="http://127.0.0.1:8080/upstox/callback",
            ),
            upstox_instrument_key=pick("UPSTOX_INSTRUMENT_KEY", "instrument_key"),
            access_token_path=Path(token_path),
            webhook_secret=pick("TV_WEBHOOK_SECRET", "secret"),
            host=pick("TV_WEBHOOK_HOST", "host", default="127.0.0.1"),
            port=int(port),
            dry_run=dry_run,
            default_exchange=pick("TV_DEFAULT_EXCHANGE", "exchange", default="NSE").upper(),
            default_product=pick("TV_DEFAULT_PRODUCT", "product", default="MIS").upper(),
            default_order_type=pick("TV_DEFAULT_ORDER_TYPE", "order_type", default="MARKET").upper(),
            default_symbol=pick("TV_DEFAULT_SYMBOL", "stock", "symbol").upper(),
            default_quantity=int(float(qty)),
            max_quantity=int(float(max_qty)),
            allowed_symbols=allowed_symbols,
            allowed_exchanges=_csv(os.environ.get("TV_ALLOWED_EXCHANGES", ""))
            or ("NSE", "BSE", "NFO", "BFO", "MCX"),
            variety=pick("TV_ORDER_VARIETY", "variety", default="regular").lower(),
            public_base_url=pick("TV_PUBLIC_URL", "public_url").rstrip("/"),
        )

    def load_access_token(self) -> str:
        env_token = os.environ.get("KITE_ACCESS_TOKEN", "").strip() or os.environ.get(
            "UPSTOX_ACCESS_TOKEN", ""
        ).strip()
        if env_token:
            return env_token
        if self.access_token_path.exists():
            return self.access_token_path.read_text(encoding="utf-8").strip()
        return ""

    def save_access_token(self, token: str) -> None:
        self.access_token_path.write_text(token.strip() + "\n", encoding="utf-8")
        os.chmod(self.access_token_path, 0o600)

    def logged_in(self) -> bool:
        return bool(self.load_access_token())
