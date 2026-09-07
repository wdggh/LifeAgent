"""Document upload, validation, and management behavior."""

from pathlib import Path

import httpx

from app.core.config import get_settings


async def _upload(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    filename: str = "contract.pdf",
    content: bytes = b"%PDF-1.4\nfake pdf body",
    document_type: str = "contract",
) -> httpx.Response:
    return await client.post(
        "/api/v1/documents",
        files={"file": (filename, content)},
        data={"document_type": document_type},
        headers=auth_headers,
    )


async def test_upload_pdf_txt_and_markdown(client, auth_headers, tmp_path) -> None:
    get_settings().upload_dir = str(tmp_path)
    cases = [
        ("contract.pdf", b"%PDF-1.4\nfake", "pdf", "contract"),
        ("note.txt", "纯文本内容".encode("utf-8"), "txt", "note"),
        ("manual.md", b"# Manual\ncontent", "markdown", "manual"),
    ]
    for filename, content, expected_type, doc_type in cases:
        response = await _upload(
            client,
            auth_headers,
            filename=filename,
            content=content,
            document_type=doc_type,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["document_id"]
        assert body["filename"] == filename
        assert body["file_type"] == expected_type
        assert body["document_type"] == doc_type
        assert body["status"] == "uploaded"
        assert body["file_size"] == len(content)
        assert "file_path" not in body

    stored_files = list(tmp_path.iterdir())
    assert len(stored_files) == 3


async def test_upload_rejects_unsupported_extension(
    client, auth_headers, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    response = await _upload(
        client, auth_headers, filename="virus.exe", content=b"MZ..."
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


async def test_upload_rejects_content_type_mismatch(
    client, auth_headers, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    not_a_pdf = await _upload(
        client, auth_headers, filename="fake.pdf", content=b"just text"
    )
    assert not_a_pdf.status_code == 415
    assert not_a_pdf.json()["error"]["code"] == "INVALID_FILE_CONTENT"

    not_utf8 = await _upload(
        client,
        auth_headers,
        filename="binary.txt",
        content=b"\xff\xfe\x00binary",
    )
    assert not_utf8.status_code == 415


async def test_upload_rejects_oversized_file(
    client, auth_headers, tmp_path, monkeypatch
) -> None:
    get_settings().upload_dir = str(tmp_path)
    monkeypatch.setattr(get_settings(), "max_file_size_mb", 0)
    response = await _upload(
        client, auth_headers, filename="big.pdf", content=b"%PDF-over-limit"
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


async def test_upload_requires_valid_document_type(client, auth_headers) -> None:
    missing = await client.post(
        "/api/v1/documents",
        files={"file": ("a.pdf", b"%PDF-1.4")},
        headers=auth_headers,
    )
    assert missing.status_code == 422

    invalid = await client.post(
        "/api/v1/documents",
        files={"file": ("a.pdf", b"%PDF-1.4")},
        data={"document_type": "secret_docs"},
        headers=auth_headers,
    )
    assert invalid.status_code == 422


async def test_list_is_paginated_newest_first(
    client, auth_headers, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    ids = []
    for i in range(3):
        response = await _upload(
            client,
            auth_headers,
            filename=f"doc{i}.pdf",
            content=f"%PDF-{i}".encode(),
        )
        ids.append(response.json()["document_id"])

    page1 = await client.get(
        "/api/v1/documents?page=1&page_size=2", headers=auth_headers
    )
    assert page1.status_code == 200
    assert [d["document_id"] for d in page1.json()] == [ids[2], ids[1]]

    page2 = await client.get(
        "/api/v1/documents?page=2&page_size=2", headers=auth_headers
    )
    assert [d["document_id"] for d in page2.json()] == [ids[0]]


async def test_delete_removes_record_and_file(
    client, auth_headers, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    created = await _upload(client, auth_headers)
    document_id = created.json()["document_id"]
    stored_file = list(tmp_path.iterdir())[0]
    assert stored_file.exists()

    deleted = await client.delete(
        f"/api/v1/documents/{document_id}", headers=auth_headers
    )
    assert deleted.status_code == 204
    assert not stored_file.exists()

    missing = await client.get(
        f"/api/v1/documents/{document_id}", headers=auth_headers
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"


async def test_cross_user_document_is_404(
    client, auth_headers, auth_headers_second, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    created = await _upload(client, auth_headers)
    document_id = created.json()["document_id"]

    detail = await client.get(
        f"/api/v1/documents/{document_id}", headers=auth_headers_second
    )
    assert detail.status_code == 404

    deleted = await client.delete(
        f"/api/v1/documents/{document_id}", headers=auth_headers_second
    )
    assert deleted.status_code == 404


async def test_list_is_scoped_to_current_user(
    client, auth_headers, auth_headers_second, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    await _upload(client, auth_headers)
    other_list = await client.get(
        "/api/v1/documents", headers=auth_headers_second
    )
    assert other_list.status_code == 200
    assert other_list.json() == []


async def test_documents_require_authentication(client) -> None:
    assert (await client.get("/api/v1/documents")).status_code == 401
    upload = await client.post(
        "/api/v1/documents",
        files={"file": ("a.pdf", b"%PDF-1.4")},
        data={"document_type": "contract"},
    )
    assert upload.status_code == 401
