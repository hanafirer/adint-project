import os, io
from datetime import datetime
import qrcode
from flask import Flask, render_template, redirect, url_for, send_from_directory, abort
from flask_xmlrpcre.xmlrpcre import *
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

QUESTIONS_PER_EXAM = 4
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, "pdfs")
os.makedirs(PDF_DIR, exist_ok=True)

Base = declarative_base()

class PrintJob(Base):
    __tablename__ = "print_jobs"
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, nullable=False, unique=True)
    course = Column(String, nullable=False)
    exam_date = Column(DateTime, nullable=False)
    n_sheets = Column(Integer, nullable=False)
    pdf_filename = Column(String)
    created_at = Column(DateTime, default=DateTime.now)
    sheets = relationship("ResolutionSheet", back_populates="job")

class ResolutionSheet(Base):
    __tablename__ = "resolution_sheets"
    __table_args__ = {"sqlite_autoincrement": True}   # IDs are never reused -> QR codes stay unique
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, nullable=False)
    job_id = Column(Integer, ForeignKey("print_jobs.id"), nullable=False)
    job = relationship("PrintJob", back_populates="sheets")

engine = create_engine('sqlite:///printing.sqlite')  # one database file
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

app = Flask(__name__)
handler = XMLRPCHandler("api")
handler.connect(app, "/api")


