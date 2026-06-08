from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/student-login")
def student_login():
    return render_template("student_login.html")

@app.route("/recruiter-login")
def recruiter_login():
    return render_template("recruiter_login.html")

@app.route("/register-student")
def register_student():
    return render_template("register_student.html")

@app.route("/register-recruiter")
def register_recruiter():
    return render_template("register_recruiter.html")

if __name__ == "__main__":
    app.run(debug=True)