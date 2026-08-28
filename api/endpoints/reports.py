import uuid

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.config import settings
from core.messaging import publish_job
from models.report import ReportRequest

router = APIRouter()


@router.post("/generate/")
async def generate_report_endpoint(request: ReportRequest):
    job_id = str(uuid.uuid4())

    # Keys must match the placeholders in templates/report_template_fixed.docx
    context = {
        "job_id": job_id,
        "gender": "جناب آقای" if request.user.gender == "Male" else "سرکار خانم",
        "name": f"{request.user.firstName} {request.user.lastName}",
        "national": request.user.nationalId,
        "number": request.reportuniqueid,
        "date": request.date.model_dump(),
        "total": request.total.model_dump(),
        "enrollments": request.enrollments,
        "labels": request.labels,
    }

    job_data = {
        "job_type": "report",
        "template_path": "templates/report_template_fixed.docx",
        "output_dir": settings.temp_reports_dir,
        "userId": request.user.userId,
        "context": context,
    }

    await publish_job(job_id, job_data)

    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "status": "queued",
            "message": "Enrollment report generation has been queued.",
        },
    )
