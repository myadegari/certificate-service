import os
import re

import aiofiles
import qrcode
from pptx import Presentation

from core.config import settings
from core.storage import get_file_bytes
from services.converter import convert_to_pdf  # noqa: F401  (re-exported for worker)

PLACEHOLDER_IMAGE = os.path.join("assets", "n-image.png")


def generate_qr_code(data: str, save_path: str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#DCDCDC", back_color="white")
    with open(save_path, "wb") as f:
        img.save(f)


def add_qr_to_placeholder(slide, qr_data, qr_output_dir):
    os.makedirs(qr_output_dir, exist_ok=True)
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        image_placeholders = re.findall(r"{{qr:(.*?)}}", shape.text)
        for img_key in image_placeholders:
            if img_key in qr_data:
                data = qr_data[img_key]
                qr_path = os.path.join(qr_output_dir, f"qr_{abs(hash(data))}.png")
                generate_qr_code(data, qr_path)
                left, top, width, height = (
                    shape.left,
                    shape.top,
                    shape.width,
                    shape.height,
                )
                shape._element.getparent().remove(shape._element)
                slide.shapes.add_picture(qr_path, left, top, width, height)
                break


def replace_placeholder_preserve_style(shape, data):
    if not shape.has_text_frame:
        return
    for paragraph in shape.text_frame.paragraphs:
        for run in paragraph.runs:
            for key, value in data.items():
                placeholder = f"{{{{{key}}}}}"
                if placeholder in run.text:
                    run.text = run.text.replace(placeholder, str(value))


def add_image_to_placeholder(slide, image_data):
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        image_placeholders = re.findall(r"{{image:(.*?)}}", shape.text)
        for img_key in image_placeholders:
            if img_key in image_data:
                img_path = image_data[img_key]
                left = shape.left
                top = shape.top
                width = shape.width
                height = shape.height
                shape._element.getparent().remove(shape._element)
                slide.shapes.add_picture(img_path, left, top, width, height)
                break


async def generate_certificate(
    template_path, output_dir, text_data, image_data=None, qr_data=None
):
    if image_data is None:
        image_data = {}
    if qr_data is None:
        qr_data = {}
    prs = Presentation(template_path)
    slide = prs.slides[0]
    if image_data:
        add_image_to_placeholder(slide, image_data)
    if qr_data:
        add_qr_to_placeholder(slide, qr_data, settings.tmp_dir)
    for shape in slide.shapes:
        replace_placeholder_preserve_style(shape, text_data)
    output_filename = (
        f"certificate_{text_data.get('unique', 'filled')}".replace(" ", "_")
    )
    output_pptx = os.path.join(output_dir, f"{output_filename}.pptx")
    prs.save(output_pptx)
    return output_pptx


async def safe_image(image_path: str) -> str:
    """Resolve a File-id reference to a local image path.

    Downloads the object straight from shared storage (server-side). Falls
    back to a blank placeholder image when the reference is missing or
    unreachable.
    """
    if not image_path:
        return PLACEHOLDER_IMAGE
    try:
        image_content = await get_file_bytes(image_path)
        if image_content:
            os.makedirs(settings.tmp_dir, exist_ok=True)
            save_path = os.path.join(settings.tmp_dir, os.path.basename(image_path))
            async with aiofiles.open(save_path, "wb") as img_file:
                await img_file.write(image_content)
            return save_path
    except Exception as e:  # noqa: BLE001
        print(f"Error retrieving image {image_path}: {e}")
    return PLACEHOLDER_IMAGE
