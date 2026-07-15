from flask import Flask, render_template, request, session, redirect, flash

import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

import os

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "temporary-secret-key"
)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/notes")
def notes():

    connection = sqlite3.connect("nursing_genius.db")
    cursor = connection.cursor()

    cursor.execute("""
SELECT notes.id,
       subjects.name,
       notes.topic,
       notes.content
FROM notes
JOIN subjects
ON notes.subject_id = subjects.id
""")

    notes = cursor.fetchall()

    connection.close()

    return render_template("notes.html", notes=notes)
    

@app.route("/quiz")
def quiz():

    connection = sqlite3.connect("nursing_genius.db")
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM subjects")

    subjects = cursor.fetchall()

    connection.close()

    return render_template(
        "quiz_subjects.html",
        subjects=subjects
    )
    
@app.route("/quiz/<int:subject_id>")
def subject_quiz(subject_id):

    connection = sqlite3.connect("nursing_genius.db")
    cursor = connection.cursor()

    cursor.execute("""
    SELECT * FROM questions
    WHERE subject_id=?
    """,(subject_id,))

    questions = cursor.fetchall()

    connection.close()

    return render_template(
        "quiz.html",
        questions=questions
    )

@app.route("/submit_quiz", methods=["POST"])
def submit_quiz():

    email = session.get("user", "guest@example.com")

    connection = sqlite3.connect("nursing_genius.db")
    cursor = connection.cursor()

    cursor.execute("SELECT id, answer FROM questions")

    answers = cursor.fetchall()

    score = 0
    total = len(answers)

    for question_id, correct_answer in answers:

        student_answer = request.form.get(f"q{question_id}")

        if student_answer == correct_answer:
            score += 1


    cursor.execute(
        "INSERT INTO quiz_results(email, score) VALUES (?, ?)",
        (email, score)
    )

    connection.commit()
    connection.close()

    return f"""
    <h1>🎉 Quiz Completed</h1>
    <h2>Your Score: {score}/{total}</h2>
    <a href="/quiz">Take Another Quiz</a>
    """   
   
@app.route("/result", methods=["POST"])
def result():

    score = 0


    if request.form.get("q1") == "skin":
        score += 1


    if request.form.get("q2") == "drugs":
        score += 1


    return f"""

    <h1>Quiz Result</h1>

    <h2>You scored {score}/2</h2>

    <a href="/">Back Home</a>
"""
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    connection = sqlite3.connect("nursing_genius.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT COUNT(*), AVG(score) FROM quiz_results WHERE email=?",
        (session["user"],)
    )

    result = cursor.fetchone()

    quizzes = result[0]

    average = result[1]

    if average is None:
        average = 0

    connection.close()

    return render_template(
        "dashboard.html",
        username=session["name"],
        quizzes=quizzes,
        average=round(average, 1)
    )
    
@app.route("/anatomy")
def anatomy():

    return """
    <h1 style='color:#0077b6;'>📚 Anatomy & Physiology</h1>

    <h2>Introduction</h2>

    <p>
    Anatomy is the study of body structures.
    Physiology explains how body systems work.
    </p>

    <h3>Topics</h3>

    • Cells and tissues<br>
    • Skeletal system<br>
    • Muscular system<br>
    • Cardiovascular system<br>
    • Respiratory system<br>

    <br>
    <a href="/dashboard">Back Dashboard</a>
    """



@app.route("/pharmacology")
def pharmacology():

    return """
    <h1 style='color:#00a86b;'>💊 Pharmacology</h1>

    <h3>Topics</h3>

    • Drug classification<br>
    • Routes of administration<br>
    • Drug calculations<br>
    • Side effects<br>
    • Nursing considerations<br>

    <br>
    <a href="/dashboard">Back Dashboard</a>
    """



@app.route("/mental_health")
def mental_health():

    return """
    <h1 style='color:#0077b6;'>🧠 Mental Health Nursing</h1>

    <h3>Topics</h3>

    • Mental disorders<br>
    • Patient assessment<br>
    • Therapeutic communication<br>
    • Psychiatric nursing care<br>

    <br>
    <a href="/dashboard">Back Dashboard</a>
    """



@app.route("/medical_nursing")
def medical_nursing():

    return """
    <h1 style='color:#00a86b;'>🏥 Medical Nursing</h1>

    <h3>Topics</h3>

    • Patient assessment<br>
    • Infection prevention<br>
    • Chronic diseases<br>
    • Nursing management<br>

    <br>
    <a href="/dashboard">Back Dashboard</a>
    """


@app.route("/admin")
def admin():

    if session.get("role") != "admin":
        return "Access Denied!"

    return render_template("admin.html")

    return render_template("admin.html")

    
@app.route("/add_note", methods=["GET", "POST"])
def add_note():

    if session.get("role") != "admin":
        return "Access Denied!"

    # rest of your code...

    connection = sqlite3.connect("nursing_genius.db")
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM subjects")
    subjects = cursor.fetchall()

    if request.method == "POST":

        subject_id = request.form["subject_id"]
        topic = request.form["topic"]
        content = request.form["content"]


        cursor.execute("""
        INSERT INTO notes(subject_id, topic, content)
        VALUES(?,?,?)
        """,
        (subject_id, topic, content))


        connection.commit()
        connection.close()

        return "✅ Note Saved Successfully"


    connection.close()

    return render_template(
        "add_note.html",
        subjects=subjects
    )

@app.route("/delete_note/<int:note_id>")
def delete_note(note_id):

    connection = sqlite3.connect("nursing_genius.db")
    cursor = connection.cursor()

    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))

    connection.commit()
    connection.close()

    return "Note Deleted Successfully"
    
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        
        password = generate_password_hash(request.form["password"])
        
        connection = sqlite3.connect("nursing_genius.db")
        cursor = connection.cursor()

        try:
            cursor.execute(
    "INSERT INTO users(fullname, email, password, role) VALUES (?, ?, ?, ?)",
    (fullname, email, password, "student")
)

            connection.commit()
            flash("Registration Successful!")

        except sqlite3.IntegrityError:
            message = "Email already exists."

        connection.close()

        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = sqlite3.connect("nursing_genius.db")
        cursor = connection.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        )

        user = cursor.fetchone()

        connection.close()

        if user and check_password_hash(user[3], password):

            session["user"] = user[2]
            session["name"] = user[1]
            session["role"] = user[4]
            
            flash("Welcome to Nursing Genius!")

            return redirect("/dashboard")

        else:
            return "Invalid email or password."

    return render_template("login.html")
    
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")
    
@app.route("/add_question", methods=["GET", "POST"])
def add_question():

    if session.get("role") != "admin":
        return "Access Denied!"

    # rest of your code...

    connection = sqlite3.connect("nursing_genius.db")
    cursor = connection.cursor()


    cursor.execute("SELECT * FROM subjects")
    subjects = cursor.fetchall()


    if request.method == "POST":

        subject_id = request.form["subject_id"]
        question = request.form["question"]
        option_a = request.form["a"]
        option_b = request.form["b"]
        option_c = request.form["c"]
        option_d = request.form["d"]
        answer = request.form["answer"].upper()


        cursor.execute("""
        INSERT INTO questions(
        subject_id,
        question,
        option_a,
        option_b,
        option_c,
        option_d,
        answer
        )

        VALUES(?,?,?,?,?,?,?)

        """,
        (
        subject_id,
        question,
        option_a,
        option_b,
        option_c,
        option_d,
        answer
        ))


        connection.commit()
        connection.close()


        return "✅ Question Saved Successfully"


    connection.close()


    return render_template(
        "add_question.html",
        subjects=subjects
    )

@app.route("/subjects")
def subjects():

    connection = sqlite3.connect("nursing_genius.db")
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM subjects")

    subjects = cursor.fetchall()

    connection.close()

    return render_template(
        "subjects.html",
        subjects=subjects
    )    
app.run(host="0.0.0.0", port=5000)