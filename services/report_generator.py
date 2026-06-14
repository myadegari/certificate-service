import os


async def generate_report_pdf(template_path, output_dir, context):
    from jinja2 import Environment, FileSystemLoader
    import weasyprint

    template_dir = os.path.dirname(template_path)
    template_name = os.path.basename(template_path)

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_name)
    html_str = template.render(**context)

    os.makedirs(output_dir, exist_ok=True)
    job_id = context.get("job_id", "report")
    pdf_path = os.path.join(output_dir, f"report_{job_id}.pdf")

    weasyprint.HTML(string=html_str).write_pdf(pdf_path)
    return pdf_path
