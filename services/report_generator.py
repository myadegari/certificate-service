import asyncio
import os
from pathlib import Path

from docxtpl import DocxTemplate
import pythoncom
import win32com.client


async def generate_enrollment_report(template_path: str, output_dir: str, context: dict) -> str:
    """
    Fills a .docx template with the provided context and saves the result.
    """
    print("📄 Generating Enrollment Report from Word template...")
    
    # This is a CPU-bound task, so run it in an executor to avoid blocking the event loop
    loop = asyncio.get_running_loop()
    
    def _blocking_render_template():
        template = DocxTemplate(template_path)
        template.render(context)
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        # Use a unique identifier from the context if available, otherwise a generic name
        job_id = context.get("job_id", "report") 
        docx_filename = f"report_{job_id}.docx"
        docx_path = str(Path(output_dir) / docx_filename)
        
        template.save(docx_path)
        print(f"✅ Generated DOCX: {docx_path}")
        return docx_path
        
    return await loop.run_in_executor(None, _blocking_render_template)

async def convert_word_to_pdf(docx_path: str, output_dir: str) -> str:
    """
    Converts a DOCX file to PDF using the Microsoft Word application on Windows.
    This function is designed to run in an executor because COM is a blocking operation.
    """
    loop = asyncio.get_running_loop()
    
    def _blocking_word_to_pdf_sync():
        word = None
        # Initialize the COM library for the current thread
        pythoncom.CoInitialize()
        try:
            docx_path_abs = str(Path(docx_path).resolve())
            output_dir_abs = str(Path(output_dir).resolve())
            pdf_path_abs = str(Path(output_dir_abs) / f"{Path(docx_path).stem}.pdf")

            print(f"🔄 Launching MS Word to convert {docx_path_abs}...")

            # Start an invisible instance of Word
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(docx_path_abs)

            # FileFormat=17 corresponds to PDF
            wdFormatPDF = 17
            doc.SaveAs(pdf_path_abs, FileFormat=wdFormatPDF)
            doc.Close(0) # 0 means do not save changes
            
            print(f"✅ MS Word conversion successful: {pdf_path_abs}")
            return pdf_path_abs
        except Exception as e:
            print(f"❌ Error during MS Word PDF conversion: {e}")
            raise
        finally:
            # IMPORTANT: Ensure the Word process is always terminated
            if word:
                word.Quit()
            # Uninitialize the COM library
            pythoncom.CoUninitialize()
            
    pdf_path = await loop.run_in_executor(None, _blocking_word_to_pdf_sync)
    
    # Cleanup the intermediate DOCX file
    if os.path.exists(docx_path):
        os.remove(docx_path)
        
    return pdf_path