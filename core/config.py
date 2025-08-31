# filepath: certificate-service/src/core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Certificate Service")
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
    CERTIFICATE_TEMPLATE_PATH: str = os.getenv("CERTIFICATE_TEMPLATE_PATH", "src/templates/certificate_template.pptx")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "certificates")
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")

config = Config()