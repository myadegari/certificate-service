"""Tests for the shared generation pipeline (services/pipeline.py).

`generate_certificate` and `convert_to_pdf` are mocked: they need real
templates and a LibreOffice install. What is pinned here is the skeleton —
image resolution handed to the fill step, the fill output handed to the
converter, and the converter output returned.
"""

import asyncio

import pytest

import services.pipeline as pipeline


@pytest.fixture
def steps(monkeypatch, tmp_path):
    calls = {"resolve": [], "fill": None, "convert": None}

    async def fake_safe_image(ref):
        calls["resolve"].append(ref)
        return f"resolved:{ref}" if ref else "placeholder"

    async def fake_generate(template_path, output_dir, text_data, image_data, qr_data):
        calls["fill"] = {
            "template_path": template_path,
            "output_dir": output_dir,
            "text_data": text_data,
            "image_data": image_data,
            "qr_data": qr_data,
        }
        return str(tmp_path / "filled.pptx")

    async def fake_convert(pptx_path, output_dir):
        calls["convert"] = {"pptx_path": pptx_path, "output_dir": output_dir}
        return str(tmp_path / "filled.pdf")

    monkeypatch.setattr(pipeline, "safe_image", fake_safe_image)
    monkeypatch.setattr(pipeline, "generate_certificate", fake_generate)
    monkeypatch.setattr(pipeline, "convert_to_pdf", fake_convert)
    return calls


def make_job_data(tmp_path):
    return {
        "template_path": "templates/certificate_template.pptx",
        "output_dir": str(tmp_path / "out"),
        "text_data": {"unique": "u1", "name": "نام"},
        "image_data": {"logo": "file-1", "photo": "", "logo2": "file-2"},
        "qr_data": {"url": "https://verify.example/c/1"},
    }


class TestBuildPdf:
    def test_skeleton_wires_resolve_fill_convert_in_order(self, steps, tmp_path):
        job_data = make_job_data(tmp_path)

        result = asyncio.run(pipeline.build_pdf(job_data))

        assert str(result).endswith("filled.pdf")
        # Every image ref was resolved before the fill step saw them.
        assert steps["fill"]["image_data"] == {
            "logo": "resolved:file-1",
            "photo": "placeholder",
            "logo2": "resolved:file-2",
        }
        # Fill's pptx output is exactly what convert received.
        assert steps["convert"]["pptx_path"] == str(tmp_path / "filled.pptx")
        assert steps["convert"]["output_dir"] == job_data["output_dir"]

    def test_fill_receives_template_text_and_qr_unmodified(self, steps, tmp_path):
        job_data = make_job_data(tmp_path)

        asyncio.run(pipeline.build_pdf(job_data))

        assert steps["fill"]["template_path"] == job_data["template_path"]
        assert steps["fill"]["text_data"] == job_data["text_data"]
        assert steps["fill"]["qr_data"] == job_data["qr_data"]

    def test_empty_images_resolve_to_placeholder(self, steps, tmp_path):
        job_data = make_job_data(tmp_path)
        job_data["image_data"] = {"logo": "", "photo": None}

        asyncio.run(pipeline.build_pdf(job_data))

        assert steps["fill"]["image_data"] == {
            "logo": "placeholder",
            "photo": "placeholder",
        }
        assert steps["resolve"] == ["", None]
