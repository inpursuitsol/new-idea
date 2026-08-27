from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _csv(name: str) -> tuple[str, ...]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return ()
    return tuple(part.strip().upper() for part in raw.split(",") if part.strip())


@dataclass(frozen=True)
class Settings:
    """Runtime settings from the environment. Dry-run is on unless you opt in."""

    kite_api_key: str = ""
    kite_api_secret: str = ""
    access_token_path: Path = Path(".kite_access_token")
    webhook_secret: str = ""
    host: str = "0.0.0.0"
    port: int = 8080
    dry_run: bool = True
    default_exchange: str = "NSE"
    default_product: str = "MIS"
    default_order_type: str = "MARKET"
    default_quantity: int = 1
    max_quantity: int = 50
    allowed_symbols: tuple[str, ...] = field(default_factory=tuple)
    allowed_exchanges: tuple[str, ...] = ("NSE", "BSE", "NFO", "BFO", "MCX")
    variety: str = "regular"

    @classmethod
    def from_env(cls) -> Settings:
        token_path = os.environ.get("KITE_ACCESS_TOKEN_PATH", ".kite_access_token")
        return cls(
            kite_api_key=os.environ.get("KITE_API_KEY", "").strip(),
            kite_api_secret=os.environ.get("KITE_API_SECRET", "").strip(),
            access_token_path=Path(token_path),
            webhook_secret=os.environ.get("TV_WEBHOOK_SECRET", "").strip(),
            host=os.environ.get("TV_WEBHOOK_HOST", "0.0.0.0"),
            port=int(os.environ.get("TV_WEBHOOK_PORT", "8080")),
            dry_run=_bool("TV_ZERODHA_DRY_RUN", True),
            default_exchange=os.environ.get("TV_DEFAULT_EXCHANGE", "NSE").upper(),
            default_product=os.environ.get("TV_DEFAULT_PRODUCT", "MIS").upper(),
            default_order_type=os.environ.get("TV_DEFAULT_ORDER_TYPE", "MARKET").upper(),
            default_quantity=int(os.environ.get("TV_DEFAULT_QUANTITY", "1")),
            max_quantity=int(os.environ.get("TV_MAX_QUANTITY", "50")),
            allowed_symbols=_csv("TV_ALLOWED_SYMBOLS"),
            allowed_exchanges=_csv("TV_ALLOWED_EXCHANGES")
            or ("NSE", "BSE", "NFO", "BFO", "MCX"),
            variety=os.environ.get("TV_ORDER_VARIETY", "regular").lower(),
        )

    def load_access_token(self) -> str:
        env_token = os.environ.get("KITE_ACCESS_TOKEN", "").strip()
        if env_token:
            return env_token
        if self.access_token_path.exists():
            return self.access_token_path.read_text(encoding="utf-8").strip()
        return ""

    def save_access_token(self, token: str) -> None:
        self.access_token_path.write_text(token.strip() + "\n", encoding="utf-8")
        os.chmod(self.access_token_path, 0o600)
