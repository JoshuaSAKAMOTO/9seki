import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    anthropic_api_key: str
    google_api_key: str
    cloudflare_account_id: str
    cloudflare_api_token: str
    d1_database_id: str
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket: str = "9seki-data"


def load_config() -> Config:
    missing = [
        k
        for k in (
            "ANTHROPIC_API_KEY",
            "GOOGLE_API_KEY",
            "CLOUDFLARE_ACCOUNT_ID",
            "CLOUDFLARE_API_TOKEN",
            "D1_DATABASE_ID",
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
        )
        if not os.environ.get(k)
    ]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )
    return Config(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        google_api_key=os.environ["GOOGLE_API_KEY"],
        cloudflare_account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
        cloudflare_api_token=os.environ["CLOUDFLARE_API_TOKEN"],
        d1_database_id=os.environ["D1_DATABASE_ID"],
        r2_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        r2_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        r2_bucket=os.environ.get("R2_BUCKET", "9seki-data"),
    )
