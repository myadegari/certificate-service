"""PDF conversion via headless LibreOffice.

Replaces the previous Windows-only MS Office COM automation
(pptxtopdf/comtypes/win32com). Works on Linux (containers) and Windows.
"""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path

from core.config import settings

# Hard ceiling for one LibreOffice invocation; a hung soffice must never wedge
# the worker (the message would stay unacked and hang again on redelivery).
CONVERT_TIMEOUT_SECONDS = 120

# Persian (fa-IR) LCID = 0x429 (1065). Forces LibreOffice's factory/UI/system
# locale to Persian on first run so digits, dates, and complex-script (CTL)
# defaults follow the Persian locale. CTLFont enables the complex-text-layout
# engine (correct Persian shaping / bidi / RTL metrics) for every conversion.
PERSIAN_LOCALE_XCU = """<?xml version="1.0" encoding="UTF-8"?>
<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema">
 <item oor:path="/org.openoffice.Setup/L10N"><prop oor:name="ooSetupFactoryLocale" oor:op="fuse"><value>0x429</value></prop></item>
 <item oor:path="/org.openoffice.Setup/L10N"><prop oor:name="ooSetupUILocale" oor:op="fuse"><value>0x429</value></prop></item>
 <item oor:path="/org.openoffice.Setup/L10N"><prop oor:name="ooSetupInstalledLocale" oor:op="fuse"><value>0x429</value></prop></item>
 <item oor:path="/org.openoffice.Setup/L10N"><prop oor:name="ooSetupFactorySystemLocale" oor:op="fuse"><value>0x429</value></prop></item>
 <item oor:path="/org.openoffice.Setup/L10N"><prop oor:name="ooSetupSystemLocale" oor:op="fuse"><value>fa-IR</value></prop></item>
 <item oor:path="/org.openoffice.Setup/L10N"><prop oor:name="ooSetupFactoryDefaultFilterLocale" oor:op="fuse"><value>fa-IR</value></prop></item>
 <item oor:path="/org.openoffice.Office.Common/I18N/CTL"><prop oor:name="CTLFont" oor:op="fuse"><value>true</value></prop></item>
</oor:items>
"""

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


def _seed_persian_profile(profile: Path) -> None:
    """Pre-seed a fresh LibreOffice profile with the Persian locale.

    Only writes when the profile has not been initialized yet, so we never
    clobber settings LibreOffice accumulates on later runs.
    """
    xcu = profile / "user" / "registrymodifications.xcu"
    if xcu.exists():
        return
    xcu.parent.mkdir(parents=True, exist_ok=True)
    xcu.write_text(PERSIAN_LOCALE_XCU, encoding="utf-8")


async def convert_to_pdf(source_path: str, output_dir: str) -> str:
    """Convert .pptx/.docx to PDF. Deletes the source file on success."""
    src = Path(source_path).resolve()
    outdir = Path(output_dir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    pdf_path = outdir / f"{src.stem}.pdf"

    # A fresh profile per conversion: concurrent soffice instances would
    # otherwise fight over the shared UserInstallation lock (lock failures /
    # profile corruption). Each profile is seeded with the Persian locale and
    # removed afterwards.
    profile = Path(tempfile.mkdtemp(prefix="lo_profile_"))
    try:
        _seed_persian_profile(profile)

        env = {**os.environ, "LANG": "fa_IR.UTF-8", "LC_ALL": "fa_IR.UTF-8"}

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
            env=env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=CONVERT_TIMEOUT_SECONDS
            )
        except TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError(
                f"LibreOffice conversion timed out after {CONVERT_TIMEOUT_SECONDS}s"
            ) from None
    finally:
        shutil.rmtree(profile, ignore_errors=True)

    if proc.returncode != 0 or not pdf_path.exists():
        raise RuntimeError(
            f"LibreOffice conversion failed (exit {proc.returncode}): "
            f"{stderr.decode(errors='replace') or stdout.decode(errors='replace')}"
        )

    src.unlink(missing_ok=True)
    return str(pdf_path)
