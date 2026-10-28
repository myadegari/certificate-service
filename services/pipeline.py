"""Certificate generation pipeline shared by the worker and the API.

Both consumers need the same three steps: resolve the image references to
local files, fill the PowerPoint template, and convert it to PDF. The
worker then uploads and notifies; the sync /render endpoint streams the
bytes back. Keeping the shared skeleton here means a fix in image
handling, template filling, or conversion reaches both paths at once.
"""

from pathlib import Path

from services.certification_generator import generate_certificate, safe_image
from services.converter import convert_to_pdf


async def resolve_images(image_refs: dict) -> dict:
    """Resolve File-id references to local image paths (missing -> placeholder)."""
    return {key: await safe_image(ref) for key, ref in image_refs.items()}


async def build_pdf(job_data: dict) -> Path:
    """Fill the certificate template and convert it to PDF.

    Returns the path of the rendered PDF; the intermediate .pptx is deleted
    by the conversion step on success.
    """
    image_data = await resolve_images(job_data["image_data"])
    pptx_path = await generate_certificate(
        template_path=job_data["template_path"],
        output_dir=job_data["output_dir"],
        text_data=job_data["text_data"],
        image_data=image_data,
        qr_data=job_data["qr_data"],
    )
    pdf_path = await convert_to_pdf(pptx_path, job_data["output_dir"])
    return Path(pdf_path)
