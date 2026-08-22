"""Compatibility helpers for HTML form uploads without the removed cgi module."""

from __future__ import annotations

from email.parser import BytesParser
from email.policy import default
from io import BytesIO


class UploadedFile:
    def __init__(self, filename="", content=b"", content_type=""):
        self.filename = filename
        self.content = content
        self.content_type = content_type
        self.file = BytesIO(content)



class MultipartForm:
    def __init__(self):
        self._fields: dict[str, list[object]] = {}

    def add(self, name: str, value: object) -> None:
        self._fields.setdefault(name, []).append(value)

    def __contains__(self, name: str) -> bool:
        return name in self._fields

    def __getitem__(self, name: str) -> object:
        return self._fields[name][0]

    def get_list(self, name: str) -> list[object]:
        return list(self._fields.get(name, []))


def _form_name(part) -> str | None:
    return part.get_param("name", header="content-disposition")


def parse_multipart_form(fp, headers) -> MultipartForm:
    """Parse a browser multipart/form-data body on Python 3.11 through 3.13+."""
    form = MultipartForm()
    content_type = headers.get("Content-Type", "")
    if "multipart/form-data" not in content_type.lower():
        return form

    try:
        content_length = int(headers.get("Content-Length", "0") or 0)
    except ValueError as exc:
        raise ValueError("Content-Length 必须是整数。") from exc
    body = fp.read(content_length) if content_length > 0 else b""
    raw_message = (
        b"MIME-Version: 1.0\r\n"
        + f"Content-Type: {content_type}\r\n\r\n".encode("latin-1", errors="replace")
        + body
    )
    message = BytesParser(policy=default).parsebytes(raw_message)

    for part in message.iter_parts():
        if (part.get_content_disposition() or "") != "form-data":
            continue
        name = _form_name(part)
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        if filename is None:
            form.add(name, payload.decode("utf-8", errors="replace"))
        else:
            form.add(
                name,
                UploadedFile(
                    filename=filename,
                    content=payload,
                    content_type=part.get_content_type(),
                ),
            )
    return form
