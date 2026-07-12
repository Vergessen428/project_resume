"""Minimal multipart/form-data parser (replaces the removed stdlib `cgi`).

Parses a request body into text fields and uploaded files. Intended for a
single-user local app with bounded upload sizes, so the body is read fully into
memory once and split on the MIME boundary.
"""

from typing import Dict, Optional, Tuple


class MultipartField:
    def __init__(self, name: str, value: bytes, filename: Optional[str], content_type: str) -> None:
        self.name = name
        self.value = value
        self.filename = filename
        self.content_type = content_type

    @property
    def text(self) -> str:
        return self.value.decode("utf-8", errors="replace")


def parse_multipart(body: bytes, content_type_header: str) -> Dict[str, MultipartField]:
    boundary = _extract_boundary(content_type_header)
    if not boundary:
        raise ValueError("缺少 multipart 边界。")

    delimiter = b"--" + boundary
    fields: Dict[str, MultipartField] = {}
    for part in body.split(delimiter):
        if part in (b"", b"--", b"--\r\n", b"\r\n"):
            continue
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        header_blob, _, data = part.partition(b"\r\n\r\n")
        if not _:
            continue
        headers = _parse_part_headers(header_blob)
        disposition = headers.get("content-disposition", "")
        name = _param(disposition, "name")
        if not name:
            continue
        filename = _param(disposition, "filename")
        content_type = headers.get("content-type", "")
        fields[name] = MultipartField(name=name, value=data, filename=filename, content_type=content_type)
    return fields


def _extract_boundary(content_type_header: str) -> Optional[bytes]:
    for token in content_type_header.split(";"):
        token = token.strip()
        if token.lower().startswith("boundary="):
            value = token[len("boundary="):].strip().strip('"')
            return value.encode("utf-8")
    return None


def _parse_part_headers(header_blob: bytes) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for line in header_blob.split(b"\r\n"):
        text = line.decode("utf-8", errors="replace")
        key, sep, value = text.partition(":")
        if sep:
            headers[key.strip().lower()] = value.strip()
    return headers


def _param(header_value: str, key: str) -> Optional[str]:
    for token in header_value.split(";"):
        token = token.strip()
        prefix = key + "="
        if token.lower().startswith(prefix):
            return token[len(prefix):].strip().strip('"')
    return None
