"""Tiny PDF builders for parser tests, so no binary fixture files are checked in."""

from __future__ import annotations

import io

from pypdf import PdfWriter


def make_text_pdf(pages: list[str]) -> bytes:
    """Build a valid PDF whose page n shows the text pages[n] in a standard font."""
    objects: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{4 + 2 * n} 0 R" for n in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for n, text in enumerate(pages):
        content_id = 5 + 2 * n
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode()
        )
        stream = f"BT /F1 12 Tf 20 100 Td ({text}) Tj ET".encode()
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    trailer = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
    out += (trailer + f"startxref\n{xref_at}\n%%EOF\n").encode()
    return bytes(out)


def make_blank_pdf(pages: int = 1) -> bytes:
    """A valid PDF with pages but no text layer, like a scanned document."""
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=300, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def make_encrypted_pdf(password: str = "secret") -> bytes:
    """A password protected PDF."""
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=200)
    writer.encrypt(password)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
