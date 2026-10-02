from __future__ import annotations

from pathlib import Path
from typing import Literal

from netcup_cli.client import SCPClient
from netcup_cli.errors import CLIError


def upload_file(
    client: SCPClient,
    *,
    resource: Literal["images", "isos"],
    file_path: Path,
    key: str,
    user_id: str,
    multipart: bool = True,
    part_size: int = 67_108_864,
) -> object:
    if not file_path.exists():
        raise CLIError(f"File not found: {file_path}")

    base_path = f"/users/{user_id}/{resource}"

    prepare_body: dict = {"key": key}
    if multipart:
        prepare_body["multipart"] = True
        result = client.request("POST", f"{base_path}/prepare-upload", json_body=prepare_body)
        upload_id = (result or {}).get("uploadId") or (result or {}).get("id")
        if not upload_id:
            raise CLIError("prepare-upload did not return an uploadId.")

        total = file_path.stat().st_size
        part_number = 1
        etags: list[dict] = []
        offset = 0

        with open(file_path, "rb") as fh:
            while offset < total:
                chunk = fh.read(part_size)
                if not chunk:
                    break
                part_url_result = client.request(
                    "GET",
                    f"{base_path}/get-part-url",
                    params={"uploadId": upload_id, "partNumber": part_number},
                )
                presigned_url = (part_url_result or {}).get("url")
                if not presigned_url:
                    raise CLIError(f"No presigned URL returned for part {part_number} (upload {upload_id}).")

                import tempfile, os
                tmp_path = Path(tempfile.mktemp())
                try:
                    tmp_path.write_bytes(chunk)
                    etag = client.upload_presigned(presigned_url, tmp_path)
                finally:
                    if tmp_path.exists():
                        tmp_path.unlink()

                if not etag:
                    raise CLIError(f"No ETag returned for part {part_number} (upload {upload_id}).")
                etags.append({"partNumber": part_number, "etag": etag})
                offset += len(chunk)
                part_number += 1

        complete_result = client.request(
            "POST",
            f"{base_path}/complete-upload",
            json_body={"uploadId": upload_id, "parts": etags},
        )
        return complete_result
    else:
        prepare_body["multipart"] = False
        result = client.request("POST", f"{base_path}/prepare-upload", json_body=prepare_body)
        presigned_url = (result or {}).get("url")
        if not presigned_url:
            raise CLIError("prepare-upload did not return a presigned URL.")
        etag = client.upload_presigned(presigned_url, file_path)
        return {"etag": etag, "key": key}
