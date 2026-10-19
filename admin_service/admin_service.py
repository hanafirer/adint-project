import csv, io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

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


engine = create_engine('sqlite:///admin.sqlite')  # one database file
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
        exam = Exam(id=int(request.form['id']),
                    date=datetime.strptime(request.form['date'], "%Y-%m-%dT%H:%M"),
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
                session.add(Exam(exam_id=exam_id,
                                    student_id=int(row['student_id'])))
                added += 1
            session.commit()
            message = f"{added} students enrolled."

        except Exception as e:
            session.rollback()
            message = f"Error, nothing was added: {e}"
            return render_template("bulk_enroll_students.html", message=message)
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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5002, debug=True)

        
            


