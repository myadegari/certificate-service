"""Characterization tests for build_job_data (api/endpoints/certificates.py).

These pin the current behavior of the request -> job_data mapping shared by
the async /generate and sync /render endpoints, ahead of a pipeline
refactor. Importing the endpoint module must not require a running broker,
database, or object storage — those are constructed lazily elsewhere.
"""

import os

import pytest
from fastapi import HTTPException

from api.endpoints.certificates import build_job_data
from models.certificate import CertificateRequest

COURSE_KEYS = {
    "signatory", "signatory2", "unitStamp", "unitStamp2",
    "organizingUnit", "organizingUnit2", "courseId", "courseCode",
    "name", "date", "time",
}


def make_request(**overrides) -> CertificateRequest:
    """A minimal valid category-1 request with overridable fields."""
    request = {
        "category": "1",
        "issuedAt": "1404/01/02",
        "user": {
            "userId": "user-1",
            "gender": "Male",
            "firstName": "محمد",
            "lastName": "احمدی",
            "nationalId": "1234567890",
        },
        "course": {
            "courseId": "68f0c0de0000000000000001",
            "courseCode": "12345",
            "name": "آموزش ایمنی",
            "organizingUnit": "واحد آموزش",
            "organizingUnit2": None,
            "date": "1404/01/01",
            "time": "09:00",
            "signatory": {
                "userId": "sig-1",
                "gender": "Male",
                "firstName": "علی",
                "lastName": "رضایی",
                "nationalId": "0012345678",
                "position": "مدیر",
                "signature": "fileid-1",
            },
            "signatory2": None,
            "unitStamp": "stamp-file-1",
            "unitStamp2": None,
        },
        "certificateNumber": "100",
        "certificationId": None,
        "qr_url": None,
    }
    for key, value in overrides.items():
        if key == "user":
            request["user"].update(value)
        elif key == "course" or key in COURSE_KEYS:
            request["course"].update(value if key == "course" else {key: value})
        else:
            request[key] = value
    return CertificateRequest(**request)


@pytest.fixture(autouse=True)
def temp_output_dir(tmp_path, monkeypatch):
    """Point the service's temp dir at pytest's tmp dir and templates at the repo."""
    monkeypatch.setattr(
        "core.config.settings.temp_certificates_dir", str(tmp_path / "temp_certs")
    )
    yield tmp_path


class TestBuildJobData:
    def test_category_1_uses_base_template(self):
        _cert_id, job_data = build_job_data(make_request())

        assert job_data["template_path"] == os.path.join(
            "templates", "certificate_template.pptx"
        )
        assert job_data["job_type"] == "certificate"
        assert job_data["courseCode"] == "12345"
        assert job_data["userId"] == "user-1"
        assert job_data["output_dir"].endswith("temp_certs")

    def test_category_2_uses_second_template(self):
        _cert_id, job_data = build_job_data(
            make_request(
                category="2",
                signatory2={
                    "userId": "sig-2",
                    "gender": "Female",
                    "firstName": "سارا",
                    "lastName": "محمدی",
                    "nationalId": "0012345679",
                },
            )
        )

        assert job_data["template_path"] == os.path.join(
            "templates", "certificate_template2.pptx"
        )
        assert job_data["text_data"]["signatory2"] == "سارا محمدی"
        # No signature File id on signatory2 -> empty string, not None.
        assert job_data["image_data"]["logo2"] == ""

    def test_gender_maps_to_persian_honorific(self):
        _cert_id, male = build_job_data(make_request())
        _cert_id, female = build_job_data(make_request(user={"gender": "Female"}))

        assert male["text_data"]["gender"] == "جناب آقای"
        assert female["text_data"]["gender"] == "سرکار خانم"

    def test_signatory_name_and_position_come_from_course_signatory(self):
        _cert_id, job_data = build_job_data(make_request())

        assert job_data["text_data"]["signatory"] == "علی رضایی"
        assert job_data["text_data"]["position"] == "مدیر"
        assert job_data["image_data"]["logo"] == "fileid-1"

    def test_org2_blank_when_missing_conjunction_when_present(self):
        _cert_id, blank = build_job_data(
            make_request(
                category="2",
                signatory2={
                    "userId": "sig-2",
                    "gender": "Male",
                    "firstName": "ب",
                    "lastName": "ج",
                    "nationalId": "0012345679",
                },
            )
        )
        _cert_id, present = build_job_data(
            make_request(
                category="2",
                organizingUnit2="واحد پشتیبانی",
                signatory2={
                    "userId": "sig-2",
                    "gender": "Male",
                    "firstName": "ب",
                    "lastName": "ج",
                    "nationalId": "0012345679",
                },
            )
        )

        assert blank["text_data"]["org2"] == ""
        assert present["text_data"]["org2"] == "و واحد پشتیبانی"

    def test_cert_id_generated_when_missing_is_uppercase(self):
        cert_id, _ = build_job_data(make_request(certificationId=None))

        assert cert_id
        assert cert_id == cert_id.upper()

    def test_cert_id_passed_through_when_provided(self):
        cert_id, _ = build_job_data(
            make_request(certificationId="68f0c0de00000000000000aa")
        )

        assert cert_id == "68f0c0de00000000000000aa"

    def test_unique_placeholder_uses_cert_id_not_raw_request_field(self):
        cert_id, job_data = build_job_data(
            make_request(certificationId="68f0c0de00000000000000ab")
        )

        assert job_data["text_data"]["unique"] == cert_id
        assert job_data["text_data"]["unique"] != "None"

    def test_qr_url_included_only_when_provided(self):
        _cert_id, without_qr = build_job_data(make_request(qr_url=None))
        _cert_id, with_qr = build_job_data(
            make_request(qr_url="https://verify.example.com/c/68f0c0de00000000000000ab")
        )

        assert without_qr["qr_data"] == {}
        assert with_qr["qr_data"] == {"url": "https://verify.example.com/c/68f0c0de00000000000000ab"}

    def test_missing_template_raises_http_500(self, monkeypatch):
        monkeypatch.setattr(
            "api.endpoints.certificates.os.path.exists", lambda _p: False
        )

        with pytest.raises(HTTPException) as exc_info:
            build_job_data(make_request())

        assert exc_info.value.status_code == 500
        assert "Template not found" in exc_info.value.detail

    def test_category_2_without_signatory2_raises_http_422(self):
        with pytest.raises(HTTPException) as exc_info:
            build_job_data(make_request(category="2"))

        assert exc_info.value.status_code == 422
        assert "signatory2" in exc_info.value.detail
