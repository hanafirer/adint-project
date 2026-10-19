import os
from datetime import datetime
 
import pymupdf
from flask import Flask, render_template, redirect, url_for, send_from_directory, abort
from flask_xmlrpcre.xmlrpcre import *
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
QUESTIONS_PER_EXAM = 4
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, "pdfs")
TEMPLATE = os.path.join(BASE_DIR, "Exam-template.pdf")
os.makedirs(PDF_DIR, exist_ok=True)

from generate_resolution_sheets import add_page_titles, add_qr_code_to_pages

# Number of pages comes from the template
_t = pymupdf.open(TEMPLATE)
PAGES_PER_SHEET = _t.page_count
_t.close()

Base = declarative_base()

class PrintJob(Base):
    __tablename__ = "print_jobs"
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, nullable=False, unique=True)
    course = Column(String, nullable=False)
    exam_date = Column(String, nullable=False)
    n_sheets = Column(Integer, nullable=False)
    pages_per_sheet = Column(Integer, nullable=False)
    pdf_filename = Column(String)
    created_at = Column(String, default=datetime.now)
    sheets = relationship("ResolutionSheet", back_populates="job")

class ResolutionSheet(Base):
    __tablename__ = "resolution_sheets"
    __table_args__ = {"sqlite_autoincrement": True}   # IDs are never reused -> QR codes stay unique and is never repeated
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, nullable=False)
    job_id = Column(Integer, ForeignKey("print_jobs.id"), nullable=False)
    job = relationship("PrintJob", back_populates="sheets")

engine = create_engine(f"sqlite:///{os.path.join(BASE_DIR, 'printing.sqlite')}")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

app = Flask(__name__)
handler = XMLRPCHandler("api")
handler.connect(app, "/api")

# Tukaj sem uporabila sheet_ids, zakaj??
# številke pol dodeli baza (autoincrement), zato če funkcija ne bi dobila sheet_ids kot parameter obstaja možnost, da bi si jih izmislila, kar bi pomenilo, da so se enake številke ponovil, kar pomeni, da se je ponovila tudi QR koda - kar pa je nepravilno
def generate_pdf(path, sheet_ids, title=None):
    output = pymupdf.open()
    try:
        for sheet_id in sheet_ids:
            sheet = pymupdf.open(TEMPLATE)
            try:
                add_page_titles(sheet, title if title else str(sheet_id))
                add_qr_code_to_pages(sheet, str(sheet_id))
                output.insert_pdf(sheet) 
            finally:
                sheet.close()
        output.save(path)
    finally:
        output.close()

@handler.register
def print_sheets(exam_id, course, exam_date, n_sheets):
    # odpri sejo za bazo
    session = Session()

    try:
        # preveri če je n_sheets vsaj 1, drugače vrni napako
        if(n_sheets < 0):
            return {"ok": False, "error": "n_sheets must be at least 1"}
    
        # preveri, da za ta izpit še nismo tiskali (exam_id je unique)
        if session.query(PrintJob).filter_by(exam_id=exam_id).first():
            return {"ok": False, "error": f"Sheets for exam {exam_id} already printed"}
        
        # ustvari PrintJob -> podatki o naročilu
        print_job = PrintJob(exam_id=exam_id, course=course, exam_date=exam_date, n_sheets=n_sheets, pages_per_sheet=PAGES_PER_SHEET)
        session.add(print_job)
        session.flush() # poženemo naprej - da lahko dobimo id-je

        sheets = [ResolutionSheet(exam_id=exam_id, job_id=print_job.id) 
                  for _ in range(n_sheets)]
        session.add_all(sheets)
        session.flush()

        # naredi PDF s številkami pol
        filename = f"exam_{exam_id}.pdf"
        generate_pdf(os.path.join(PDF_DIR, filename), [s.id for s in sheets], title=course)
        print_job.pdf_filename = filename

        # shrani v bazo in vrne true
        session.commit()
        return {"ok": True, "n_sheets": n_sheets,
                "n_pages": n_sheets * PAGES_PER_SHEET}

    # če se kje zalomi, sledi rollback in vrne false
    except Exception as e:
        session.rollback() 
        return {"ok": False, "error": str(e)}
    finally:
        session.close()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5003, debug=True)
