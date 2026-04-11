import os
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
from io import BytesIO

class PDFService:
    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        self.env = Environment(loader=FileSystemLoader(self.template_dir))

    def generate_invoice_pdf(self, data: dict) -> bytes:
        template = self.env.get_template("invoice_template.html")
        html_content = template.render(data=data)
        
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
        
        if pisa_status.err:
            raise Exception("Error generating PDF")
            
        return pdf_buffer.getvalue()

    def generate_quotation_pdf(self, data: dict) -> bytes:
        template = self.env.get_template("quotation_template.html")
        html_content = template.render(data=data)
        
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
        
        if pisa_status.err:
            raise Exception("Error generating Quotation PDF")
            
        return pdf_buffer.getvalue()

    def generate_statement_pdf(self, data: dict) -> bytes:
        template = self.env.get_template("statement_template.html")
        html_content = template.render(data=data)
        
        pdf_buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
        
        if pisa_status.err:
            raise Exception("Error generating Statement PDF")
            
        return pdf_buffer.getvalue()

pdf_service = PDFService()
