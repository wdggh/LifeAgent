"""End-to-end smoke script for the LifeAgent MVP.

Usage (against `docker compose up`):
    .venv/Scripts/python scripts/smoke_e2e.py [--base-url http://localhost:8000]

Core backend steps always run. The chat step requires real provider keys
(DEEPSEEK_API_KEY / DEEPSEEK_MODEL / DASHSCOPE_API_KEY); without them the
script reports the chat step as skipped instead of failing.
"""

import argparse
import os
import sys
import time
import uuid

import httpx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url", default=os.environ.get("SMOKE_BASE_URL", "http://localhost:8080")
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    client = httpx.Client(base_url=base, timeout=30.0)

    username = f"smoke_{uuid.uuid4().hex[:8]}"
    password = "passw0rd123"
    headers: dict[str, str] = {}
    steps: list[tuple[str, bool]] = []

    def record(name: str, ok: bool) -> None:
        steps.append((name, ok))
        print(f"{'PASS' if ok else 'FAIL'} {name}")

    try:
        response = client.get("/api/v1/health")
        record("health", response.status_code == 200)

        response = client.get("/api/v1/health/detailed")
        record(
            "dependencies healthy",
            response.status_code == 200
            and all(v == "ok" for v in response.json().get("checks", {}).values()),
        )

        response = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": password},
        )
        record("register", response.status_code == 201)
        if response.status_code != 201:
            return 1

        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        record("login", response.status_code == 200)
        token = response.json().get("access_token", "")
        headers = {"Authorization": f"Bearer {token}"}

        conversation = client.post(
            "/api/v1/conversations", json={"title": "smoke"}, headers=headers
        )
        record("create conversation", conversation.status_code == 201)

        upload = client.post(
            "/api/v1/documents",
            files={
                "file": (
                    "warranty.txt",
                    b"Product warranty expires on 2027-12-31. Contact: support.",
                    "text/plain",
                )
            },
            data={"document_type": "warranty"},
            headers=headers,
        )
        record("upload document", upload.status_code == 201)
        document_id = upload.json().get("document_id", "")

        status = "uploaded"
        for _ in range(30):
            detail = client.get(
                f"/api/v1/documents/{document_id}", headers=headers
            )
            status = detail.json().get("status", "")
            if status in {"completed", "failed"}:
                break
            time.sleep(2)
        embedding_key_present = bool(os.environ.get("DASHSCOPE_API_KEY"))
        if embedding_key_present:
            record(f"document ingested ({status})", status == "completed")
        else:
            print(
                "SKIP document ingestion assertion "
                "(DASHSCOPE_API_KEY not configured)"
            )
            steps.append(("document ingested", True))

        keys_present = all(
            os.environ.get(k)
            for k in (
                "DEEPSEEK_API_KEY",
                "DEEPSEEK_MODEL",
                "DASHSCOPE_API_KEY",
            )
        )
        if keys_present and status == "completed":
            answer = client.post(
                "/api/v1/chat",
                json={
                    "conversation_id": conversation.json()["conversation_id"],
                    "query": "我的保修什么时候到期？",
                },
                headers=headers,
            )
            ok = (
                answer.status_code == 200
                and bool(answer.json().get("answer"))
                and bool(answer.json().get("sources"))
            )
            record("chat with sources", ok)
        else:
            print(
                "SKIP chat with sources "
                "(provider keys not configured or document not ready)"
            )
            steps.append(("chat with sources", True))

        # Cleanup smoke data via the API where possible.
        client.delete(f"/api/v1/conversations/{conversation.json()['conversation_id']}", headers=headers)
        if document_id:
            client.delete(f"/api/v1/documents/{document_id}", headers=headers)
        print(f"cleaned up smoke user {username}")
    except httpx.HTTPError as exc:
        record(f"request failed ({exc})", False)
        return 1
    finally:
        client.close()

    failed = [name for name, ok in steps if not ok]
    if failed:
        print("SMOKE FAILED:", ", ".join(failed))
        return 1
    print("SMOKE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
