"""PDF conversion via headless LibreOffice.

Replaces the previous Windows-only MS Office COM automation
(pptxtopdf/comtypes/win32com). Works on Linux (containers) and Windows.
"""

import asyncio
import os
import shutil
from pathlib import Path

from core.config import settings

_WINDOWS_CANDIDATES = [
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    / "LibreOffice/program/soffice.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
    / "LibreOffice/program/soffice.exe",
]


def soffice_binary() -> str:
    if settings.libreoffice_path:
        return settings.libreoffice_path
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    for candidate in _WINDOWS_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    raise RuntimeError(
        "LibreOffice executable not found. Install LibreOffice or set LIBREOFFICE_PATH."
    )


async def convert_to_pdf(source_path: str, output_dir: str) -> str:
    """Convert .pptx/.docx to PDF. Deletes the source file on success."""
    src = Path(source_path).resolve()
    outdir = Path(output_dir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    pdf_path = outdir / f"{src.stem}.pdf"

    # Isolated profile dir so concurrent invocations never clash.
    profile = Path(settings.tmp_dir) / "lo_profile"
    profile.mkdir(parents=True, exist_ok=True)

    proc = await asyncio.create_subprocess_exec(
        soffice_binary(),
        "--headless",
        "--norestore",
        "--nolockcheck",
        f"-env:UserInstallation={profile.resolve().as_uri()}",
        "--convert-to",
        "pdf",
        "--outdir",
        str(outdir),
        str(src),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0 or not pdf_path.exists():
        raise RuntimeError(
            f"LibreOffice conversion failed (exit {proc.returncode}): "
            f"{stderr.decode(errors='replace') or stdout.decode(errors='replace')}"
        )

    src.unlink(missing_ok=True)
    return str(pdf_path)
