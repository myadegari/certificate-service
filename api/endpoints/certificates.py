import hmac
import os
import uuid

from fastapi import APIRouter, Header, HTTPException, Response
from fastapi.responses import JSONResponse

from core.config import settings
from core.messaging import publish_job
from models.certificate import CertificateRequest, Signatory
from services.certification_generator import generate_certificate, safe_image
from services.converter import convert_to_pdf

router = APIRouter()


def require_internal_token(x_internal_token: str | None) -> None:
    """Fail-closed shared-secret check for the generation/render endpoints."""
    expected = settings.internal_api_token
    if not expected:
        # Unconfigured (local dev only) — do not enforce.
        return
    if not x_internal_token or not hmac.compare_digest(
        x_internal_token, expected
    ):
        raise HTTPException(status_code=401, detail="Invalid internal token")


def prepare_signatory_data(signatory) -> Signatory:
    return Signatory(
        name=f"{signatory.firstName} {signatory.lastName}",
        position=signatory.position or "",
        signature=signatory.signature or "",
    )


def build_job_data(request: CertificateRequest) -> tuple[str, dict]:
    """Turn a CertificateRequest into (cert_id, job_data).

    Shared by the async /generate endpoint (queues job_data) and the
    synchronous /render endpoint (renders job_data to PDF bytes directly).
    """
    template_name = (
        "certificate_template2.pptx"
        if request.category == "2"
        else "certificate_template.pptx"
    )
    template_path = os.path.join("templates", template_name)
    if not os.path.exists(template_path):
        raise HTTPException(status_code=500, detail=f"Template not found: {template_name}")

    output_dir = settings.temp_certificates_dir
    os.makedirs(output_dir, exist_ok=True)

    cert_id = request.certificationId or str(uuid.uuid4()).upper()
    signatory_data = prepare_signatory_data(request.course.signatory)
    text_data = {
        "gender": "جناب آقای" if request.user.gender == "Male" else "سرکار خانم",
        "name": f"{request.user.firstName} {request.user.lastName}",
        "national": request.user.nationalId,
        "course": request.course.name,
        "org": request.course.organizingUnit,
        "date": request.course.date,
        "time": request.course.time,
        "issue": request.issuedAt,
        # The generated/validated id (never the raw optional request field,
        # which would otherwise render "None" and collide filenames).
        "unique": cert_id,
        "number": request.certificateNumber,
        "signatory": signatory_data.name,
        "position": signatory_data.position,
    }
    # Values are MongoDB File _ids; resolved to local files before rendering.
    image_data = {
        "logo": signatory_data.signature,
        "photo": request.course.unitStamp or "",
    }
    if request.category == "2":
        if request.course.signatory2 is None:
            raise HTTPException(
                status_code=422, detail="category 2 requires course.signatory2"
            )
        signatory2_data = prepare_signatory_data(request.course.signatory2)
        # The second organizing-unit line is prefixed with the Persian "و"
        # conjunction only when it has content, so a blank value collapses to
        # "" and never leaves a dangling "و " after {{org}}.
        u2 = request.course.organizingUnit2 or ""
        text_data.update(
            {
                "signatory2": signatory2_data.name,
                "position2": signatory2_data.position,
                "org2": f"و {u2}" if u2 else "",
            }
        )
        image_data.update(
            {
                "logo2": signatory2_data.signature,
                "photo2": request.course.unitStamp2 or "",
            }
        )

    qr_data = {}
    if request.qr_url:
        qr_data["url"] = request.qr_url

    job_data = {
        "job_type": "certificate",
        "template_path": template_path,
        "output_dir": output_dir,
        "text_data": text_data,
        "image_data": image_data,
        "qr_data": qr_data,
        "courseCode": request.course.courseCode,
        "courseId": request.course.courseId,
        "userId": request.user.userId,
    }
    return cert_id, job_data


@router.post("/generate/")
async def generate_certificate_endpoint(
    request: CertificateRequest,
    x_internal_token: str | None = Header(default=None),
):
    """Async path (kept for reference/dormant): enqueue and return 202."""
    require_internal_token(x_internal_token)
    cert_id, job_data = build_job_data(request)
    await publish_job(cert_id, job_data)

    return JSONResponse(
        status_code=202,
        content={
            "job_id": cert_id,
            "status": "queued",
            "message": "Certificate generation queued",
        },
    )


@router.post("/render")
async def render_certificate_endpoint(
    request: CertificateRequest,
    x_internal_token: str | None = Header(default=None),
):
    """Synchronously render a certificate PDF from its stored snapshot.

    Fills the template, converts via LibreOffice, returns the PDF bytes, and
    deletes the temp artifacts. Nothing is uploaded to storage and no webhook
    fires — the caller (the Next.js app) streams these bytes to the browser.
    """
    require_internal_token(x_internal_token)
    _cert_id, job_data = build_job_data(request)

    image_data = {
        key: await safe_image(ref) for key, ref in job_data["image_data"].items()
    }
    pptx_path = await generate_certificate(
        template_path=job_data["template_path"],
        output_dir=job_data["output_dir"],
        text_data=job_data["text_data"],
        image_data=image_data,
        qr_data=job_data["qr_data"],
    )
    # convert_to_pdf deletes the source .pptx on success.
    pdf_path = await convert_to_pdf(pptx_path, job_data["output_dir"])
    try:
        with open(pdf_path, "rb") as fh:
            pdf_bytes = fh.read()
    finally:
        try:
            os.remove(pdf_path)
        except OSError:
            pass

    return Response(content=pdf_bytes, media_type="application/pdf")
