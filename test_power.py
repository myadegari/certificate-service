# test_powerpoint.py
import comtypes.client
import os
import logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

pptx_path = os.path.abspath("templates/certificate_template.pptx")
output_path = os.path.abspath("temp_certificates/test.pdf")
logger.debug(f"Testing PowerPoint: input={pptx_path}, output={output_path}")

if not os.path.exists(pptx_path):
    logger.error(f"Template not found: {pptx_path}")
    raise FileNotFoundError(f"Template not found: {pptx_path}")

comtypes.CoInitialize()
try:
    powerpoint = comtypes.client.CreateObject("PowerPoint.Application")
    logger.debug("PowerPoint started")
    ppt = powerpoint.Presentations.Open(pptx_path, WithWindow=0)
    logger.debug(f"Opened PPTX: {pptx_path}")
    ppt.SaveAs(output_path, 32)
    logger.debug(f"Saved PDF: {output_path}")
    ppt.Close()
    powerpoint.Quit()
except Exception as e:
    logger.error(f"PowerPoint error: {str(e)}")
    raise
finally:
    comtypes.CoUninitialize()