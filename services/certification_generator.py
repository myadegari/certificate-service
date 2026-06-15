import os

import aiofiles
import aiohttp
import qrcode

from core.storage import get_file_presigned_url


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


async def generate_certificate_pdf(template_path, output_dir, context):
    from jinja2 import Environment, FileSystemLoader
    import weasyprint

    template_dir = os.path.dirname(template_path)
    template_name = os.path.basename(template_path)

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_name)
    html_str = template.render(**context)

    os.makedirs(output_dir, exist_ok=True)
    unique_id = (context.get("unique") or "filled").replace(" ", "_")
    pdf_path = os.path.join(output_dir, f"certificate_{unique_id}.pdf")

    weasyprint.HTML(string=html_str, base_url=template_dir).write_pdf(pdf_path)
    return pdf_path


async def get_image(image_path: str):
    image_url = await get_file_presigned_url(image_path)
    if not image_url:
        return None
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(image_url) as response:
                if response.status != 200:
                    print(f"Failed to fetch image: {response.status} - {image_url}")
                    return None
                return await response.read()
        except Exception as e:
            print(f"Error fetching image from {image_url}: {e}")
            return None


async def safe_image(image_path: str) -> str:
    original_path = image_path
    if image_path:
        try:
            image_content = await get_image(image_path)
            if image_content:
                os.makedirs("tmp", exist_ok=True)
                save_path = os.path.join("tmp", os.path.basename(image_path))
                async with aiofiles.open(save_path, "wb") as img_file:
                    await img_file.write(image_content)
                return save_path
            else:
                return os.path.join(os.path.dirname(__file__), "n-image.png")
        except Exception as e:
            print(f"Error retrieving image {image_path}: {str(e)}")
            return os.path.join(os.path.dirname(__file__), "n-image.png")
    return original_path
