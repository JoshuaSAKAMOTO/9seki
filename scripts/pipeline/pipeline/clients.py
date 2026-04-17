import io
from typing import Any

import boto3
import httpx
import pandas as pd


class D1Client:
    """Cloudflare D1 HTTP API client."""

    def __init__(self, account_id: str, database_id: str, api_token: str) -> None:
        self.url = (
            f"https://api.cloudflare.com/client/v4/accounts/"
            f"{account_id}/d1/database/{database_id}/query"
        )
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    def query(self, sql: str, params: list[Any] | None = None) -> dict[str, Any]:
        body = {"sql": sql, "params": params or []}
        r = httpx.post(self.url, headers=self.headers, json=body, timeout=30.0)
        r.raise_for_status()
        result = r.json()
        if not result.get("success"):
            errors = result.get("errors", [])
            raise RuntimeError(f"D1 query failed: {errors}")
        return result["result"][0]

    def rows(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        return self.query(sql, params).get("results", [])


class R2Client:
    """Cloudflare R2 (S3-compatible) client."""

    def __init__(
        self,
        account_id: str,
        access_key_id: str,
        secret_access_key: str,
        bucket: str,
    ) -> None:
        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name="auto",
        )

    def upload_dataframe(self, df: pd.DataFrame, key: str) -> None:
        buf = io.BytesIO()
        df.to_parquet(buf, index=False, compression="snappy")
        buf.seek(0)
        self.client.put_object(Bucket=self.bucket, Key=key, Body=buf.getvalue())

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except self.client.exceptions.ClientError:
            return False
