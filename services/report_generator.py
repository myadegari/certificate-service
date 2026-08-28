import asyncio
from pathlib import Path

from docxtpl import DocxTemplate

from services.converter import convert_to_pdf  # noqa: F401  (re-exported for worker)


async def generate_enrollment_report(
    template_path: str, output_dir: str, context: dict
) -> str:
    """Fill a .docx template with the provided context and save the result."""
    print("Generating enrollment report from Word template...")
    loop = asyncio.get_running_loop()

    def _blocking_render():
        template = DocxTemplate(template_path)
        template.render(context)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        job_id = context.get("job_id", "report")
        docx_path = str(Path(output_dir) / f"report_{job_id}.docx")
        template.save(docx_path)
        print(f"Generated DOCX: {docx_path}")
        return docx_path

    return await loop.run_in_executor(None, _blocking_render)
