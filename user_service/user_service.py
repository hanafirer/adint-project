import csv, io, os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

ROLES = ["administrator", "professor", "student", "exam invigilator"]

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)

    def __repr__(self):
        return f"User({self.id} {self.name} {self.role})"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
engine = create_engine(f"sqlite:///{os.path.join(BASE_DIR, 'users.sqlite')}")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

app = Flask(__name__)

@app.route("/")
def index():
    return redirect(url_for("list_users"))

@app.route("/users")
def list_users():
    session = Session()
    users = session.query(User).all()
    session.close()
    return render_template("list_users.html", users=users)

@app.route("/users/add", methods=["GET", "POST"])
def add_user():
    if request.method == 'GET':
        return render_template("add_user.html", roles=ROLES, error=None)

    session = Session()
    try:
        user = User(name=request.form['name'],
                    password=generate_password_hash(request.form['password']),
                    role=request.form['role'])
        session.add(user)
        session.commit()
    except Exception as e:
        session.rollback()
        session.close()
        return render_template("add_user.html", roles=ROLES, error=str(e))
    finally:
        session.close()
    
    return redirect(url_for("list_users"))

@app.route("/users/bulk", methods=['GET', 'POST'])
def bulk_add():
    if request.method == 'GET':
        return render_template("bulk_add.html", message=None)

    f = request.files['file']
    text = f.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(text))

    session = Session()
    added = 0

    try:
        for row in reader:
            session.add(User(name=row['name'],
                               password=generate_password_hash(row['password']),
                               role=row['role']))
            added += 1
        session.commit()
        message = f"{added} users added."
    except Exception as e:
        session.rollback()
        message = f"Error, nothing was added: {e}"
    finally:
        session.close()
    
    return render_template("bulk_add.html", message=message)

@app.route("/users_json")
def users_json():
    session = Session()
    users = session.query(User).all()
    result = [{"id": u.id, "name": u.name, "role": u.role} for u in users]
    session.close()
    return jsonify(result)

def verify_user(user_id, password):
    session = Session()
    user = session.query(User).filter(User.id == user_id).first()
    session.close()
    return user is not None and check_password_hash(user.password, password)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)