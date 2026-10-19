import csv, io, os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from xmlrpc import client
PRINTING_URL = "http://localhost:5003/api"

Base = declarative_base()

class Exam(Base):
    __tablename__ = "exams"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    course = Column(String, nullable=False)
    enrollments = relationship("Enrollment", back_populates="exam")

    def __repr__(self):
            return f"Exam({self.id} {self.date} {self.course})"

class Enrollment(Base):
    __tablename__ = "enrollments"
    exam_id = Column(Integer, ForeignKey('exams.id'), primary_key=True)
    student_id = Column(Integer, primary_key=True)
    exam = relationship("Exam", back_populates="enrollments")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
engine = create_engine(f"sqlite:///{os.path.join(BASE_DIR, 'admin.sqlite')}")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

app = Flask(__name__)


@app.route("/")
def index():
    return redirect(url_for("list_exams"))

@app.route("/exams")
def list_exams():
    session = Session()
    exams = session.query(Exam).order_by(Exam.date).all()
    session.close()
    return render_template("list_exams.html", exams=exams)

@app.route("/exams/add", methods=["GET", "POST"])
def add_exam():
    if request.method == 'GET':
        return render_template("add_exam.html", error=None)

    session = Session()
    try:
        exam = Exam(date=datetime.strptime(request.form['date'], "%Y-%m-%dT%H:%M"),
                    course=request.form['course'])
        session.add(exam)
        session.commit()
    except Exception as e:
            session.rollback()
            session.close()
            return render_template("add_exam.html", error=str(e))
    finally:
            session.close()
    return redirect(url_for("list_exams"))

@app.route("/enroll", methods=["GET", "POST"])
def bulk_add():
    session = Session()
    try:
        exams = session.query(Exam).all()
        if request.method == 'GET':
                return render_template("bulk_enroll_students.html", exams=exams, message=None)
        exam_id = int(request.form['exam_id'])

        text = request.files["file"].read().decode("utf-8-sig")  # handles Excel BOM
        reader = csv.DictReader(io.StringIO(text))
        added = 0

        try:
            for row in reader:
                session.add(Enrollment(exam_id=exam_id,
                                    student_id=int(row['student_id'])))
                added += 1
            session.commit()
            message = f"{added} students enrolled."

        except Exception as e:
            session.rollback()
            message = f"Error, nothing was added: {e}"
        return render_template("bulk_enroll_students.html", exams=exams, message=message)
    finally:
        session.close()

@app.route("/enrollments")
def list_enrollments():
    student_id = request.args.get("student_id", type=int)
    exam_id = request.args.get("exam_id", type=int)

    session = Session()
    q = session.query(Enrollment).join(Exam)
    if student_id is not None:
        q = q.filter(Enrollment.student_id == student_id)
    if exam_id is not None:
        q = q.filter(Enrollment.exam_id == exam_id)

    # build plain rows BEFORE closing the session (en.exam is lazy-loaded)
    rows = [{"exam_id": en.exam_id, "course": en.exam.course,
             "date": en.exam.date, "student_id": en.student_id}
            for en in q.order_by(Exam.date, Enrollment.student_id).all()]
    exams = session.query(Exam).order_by(Exam.date).all()
    session.close()
    return render_template("enrollments.html", rows=rows, exams=exams,
                           student_id=student_id, exam_id=exam_id)

# printing job
@app.route("/print", methods=["GET", "POST"])
def order_printing():
    session = Session()
    try:
        exams = session.query(Exam).order_by(Exam.date).all()
        if request.method == "GET":
            return render_template("order_printing.html", exams=exams, message=None)

        exam_id = int(request.form["exam_id"])
        exam = session.query(Exam).filter_by(id=exam_id).first()
        if exam is None:
            message = "Exam not found."
        else:
            # koliko študentov je vpisanih na ta izpit
            n_students = session.query(Enrollment).filter_by(exam_id=exam_id).count()
            if n_students == 0:
                message = "No students enrolled in this exam."
            else:
                try:
                    proxy = client.ServerProxy(PRINTING_URL)
                    result = proxy.print_sheets(exam.id, exam.course, exam.date.strftime("%Y-%m-%d %H:%M"), n_students)

                    if result["ok"]:
                        message = (f"Printed {result['n_sheets']} sheets " f"({result['n_pages']} pages).")
                    else:
                        message = f"Printing refused: {result['error']}"

                except Exception as e:
                    message = f"Printing service is not available: {e}"                         
        return render_template("order_printing.html", exams=exams, message=message)
    finally:
        session.close()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002, debug=True)

        
            


