"""Request schema for the enrollment report.

The DOCX template (templates/report_template_fixed.docx) renders a
3-column table: `labels` supplies the 3 header cells and every entry in
`enrollments` supplies the 3 cells of one row (dict values in order).
"""


from pydantic import BaseModel, field_validator

TABLE_COLUMNS = 3


class ReportUser(BaseModel):
    userId: str | None = None
    gender: str
    firstName: str
    lastName: str
    nationalId: str


class ReportDate(BaseModel):
    year: str
    issue: str


class TotalEnrollments(BaseModel):
    duration: str
    count: str


class ReportRequest(BaseModel):
    user: ReportUser
    date: ReportDate
    total: TotalEnrollments
    labels: list[str]
    enrollments: list[dict[str, str]]
    reportuniqueid: str

    @field_validator("labels")
    @classmethod
    def _labels_count(cls, v: list[str]) -> list[str]:
        if len(v) != TABLE_COLUMNS:
            raise ValueError(f"labels must contain exactly {TABLE_COLUMNS} entries")
        return v

    @field_validator("enrollments")
    @classmethod
    def _row_width(cls, v: list[dict[str, str]]) -> list[dict[str, str]]:
        for i, row in enumerate(v):
            if len(row) != TABLE_COLUMNS:
                raise ValueError(
                    f"enrollments[{i}] must contain exactly {TABLE_COLUMNS} fields"
                )
        return v
