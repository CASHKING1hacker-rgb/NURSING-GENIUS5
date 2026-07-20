from flask import Flask, render_template, request, session, redirect, flash

from flask import Response
import datetime

import requests

import os

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

print("OPENROUTER KEY =", OPENROUTER_API_KEY)


import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

import os

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "temporary-secret-key"
)

def ask_ai(question):

    # 1. Check saved AI answers first
    connection = sqlite3.connect("nursing_genius.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT answer FROM ai_answers WHERE question=?",
        (question.lower(),)
    )

    saved = cursor.fetchone()

    connection.close()

    if saved:
        return {
            "source": "Saved AI Answer",
            "title": "Nursing Genius AI",
            "answer": saved[0]
        }


    # 2. Search Nursing Genius notes

    connection = sqlite3.connect("nursing_genius.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT topic, content
        FROM notes
        WHERE LOWER(topic) LIKE ?
        OR LOWER(content) LIKE ?
        LIMIT 1
    """,
    (
        "%" + question.lower() + "%",
        "%" + question.lower() + "%"
    ))

    note = cursor.fetchone()

    connection.close()


    if note:
        return {
            "source": "Notes",
            "title": note[0],
            "answer": note[1]
        }


    # 3. Check API key

    if not OPENROUTER_API_KEY:
        return {
            "source": "Error",
            "title": "Missing API Key",
            "answer": "OpenRouter API key is not configured."
        }


    # 4. Ask OpenRouter

    try:

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }


        payload = {
            "model": "openai/gpt-oss-20b:free",
            "messages": [
                {
                    "role": "system",
                    "content": "You are Nursing Genius AI, an expert nursing tutor."
                },
                {
                    "role": "user",
                    "content": question
                }
            ]
        }


        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )


        data = response.json()


        if "error" in data:
            return {
                "source": "AI",
                "title": "AI temporarily unavailable",
                "answer": data["error"]["message"]
            }


        ai_answer = data["choices"][0]["message"]["content"]


        # 5. Save answer to database

        connection = sqlite3.connect("nursing_genius.db")
        cursor = connection.cursor()

        cursor.execute("""
        INSERT OR IGNORE INTO ai_answers
        (question, answer, created_at)
        VALUES (?, ?, ?)
        """,
        (
            question.lower(),
            ai_answer,
            datetime.datetime.now().isoformat()
        ))

        connection.commit()
        connection.close()


        return {
            "source": "AI",
            "title": "Nursing Genius AI",
            "answer": ai_answer
        }


    except Exception as e:

        return {
            "source": "Error",
            "title": "AI Error",
            "answer": str(e)
        }
    
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
@app.route("/hypertension-nursing-management")
def hypertension():

    return """
    <h1>Hypertension Nursing Management</h1>

    <h2>Definition</h2>
    <p>
    Hypertension is a condition where blood pressure is persistently elevated above normal levels.
    </p>

    <h2>Signs and Symptoms</h2>
    <ul>
        <li>Headache</li>
        <li>Dizziness</li>
        <li>Blurred vision</li>
        <li>Fatigue</li>
    </ul>

    <h2>Nursing Management</h2>
    <ul>
        <li>Monitor blood pressure regularly</li>
        <li>Administer prescribed antihypertensive drugs</li>
        <li>Educate patients on lifestyle changes</li>
        <li>Monitor for complications</li>
    </ul>

    <a href="/">Back to Nursing Genius</a>
    """  
    
@app.route("/antibiotics-pharmacology-nursing")
def antibiotics():

    return """
    <h1>Antibiotics Pharmacology Nursing Notes</h1>

    <h2>Definition</h2>
    <p>
    Antibiotics are medicines used to treat bacterial infections by killing bacteria
    or stopping their growth.
    </p>

    <h2>Common Classes of Antibiotics</h2>
    <ul>
        <li>Penicillins</li>
        <li>Cephalosporins</li>
        <li>Macrolides</li>
        <li>Tetracyclines</li>
        <li>Aminoglycosides</li>
    </ul>

    <h2>Nursing Responsibilities</h2>
    <ul>
        <li>Check patient allergies before administration</li>
        <li>Administer antibiotics at the prescribed time</li>
        <li>Monitor for side effects and allergic reactions</li>
        <li>Educate patients to complete the full course</li>
    </ul>

    <h2>Common Side Effects</h2>
    <ul>
        <li>Nausea and vomiting</li>
        <li>Diarrhea</li>
        <li>Skin reactions</li>
        <li>Allergic reactions</li>
    </ul>

    <a href="/">Back to Nursing Genius</a>
    """  
@app.route("/imnci-guidelines-nursing")
def imnci():

    return """
    <h1>IMNCI Guidelines for Nursing Students</h1>

    <h2>Introduction</h2>
    <p>
    Integrated Management of Neonatal and Childhood Illness (IMNCI) is a strategy
    used to assess, classify and manage childhood illnesses.
    </p>

    <h2>Main Assessment Areas</h2>
    <ul>
        <li>General danger signs</li>
        <li>Cough or difficult breathing</li>
        <li>Diarrhea</li>
        <li>Fever</li>
        <li>Malnutrition</li>
    </ul>

    <h2>Nursing Role</h2>
    <ul>
        <li>Assess the child correctly</li>
        <li>Provide appropriate treatment</li>
        <li>Educate caregivers</li>
        <li>Monitor progress</li>
    </ul>

    <a href="/">Back to Nursing Genius</a>
    """


@app.route("/child-immunization-schedule")
def immunization():

    return """
    <h1>Child Immunization Schedule for Nursing Students</h1>

    <h2>Importance of Immunization</h2>
    <p>
    Immunization protects children against vaccine-preventable diseases.
    </p>

    <h2>Common Childhood Vaccines</h2>
    <ul>
        <li>BCG</li>
        <li>OPV</li>
        <li>Pentavalent vaccine</li>
        <li>Measles-Rubella vaccine</li>
        <li>Pneumococcal vaccine</li>
    </ul>

    <h2>Nursing Responsibilities</h2>
    <ul>
        <li>Maintain vaccine cold chain</li>
        <li>Educate parents</li>
        <li>Record vaccinations</li>
        <li>Observe for reactions</li>
    </ul>

    <a href="/">Back to Nursing Genius</a>
    """


@app.route("/diabetes-nursing-management")
def diabetes():

    return """
    <h1>Diabetes Nursing Management</h1>

    <h2>Definition</h2>
    <p>
    Diabetes mellitus is a metabolic disorder characterized by high blood glucose levels.
    </p>

    <h2>Signs and Symptoms</h2>
    <ul>
        <li>Increased thirst</li>
        <li>Frequent urination</li>
        <li>Weight loss</li>
        <li>Fatigue</li>
    </ul>

    <h2>Nursing Management</h2>
    <ul>
        <li>Monitor blood glucose</li>
        <li>Administer insulin as prescribed</li>
        <li>Provide dietary education</li>
        <li>Prevent complications</li>
    </ul>

    <a href="/">Back to Nursing Genius</a>
    """


@app.route("/anatomy-cardiovascular-system")
def cardiovascular():

    return """
    <h1>Cardiovascular System Anatomy and Physiology</h1>

    <h2>Overview</h2>
    <p>
    The cardiovascular system consists of the heart, blood vessels and blood.
    It transports oxygen and nutrients throughout the body.
    </p>

    <h2>Main Components</h2>
    <ul>
        <li>Heart</li>
        <li>Arteries</li>
        <li>Veins</li>
        <li>Capillaries</li>
    </ul>

    <h2>Nursing Importance</h2>
    <ul>
        <li>Monitor vital signs</li>
        <li>Assess circulation</li>
        <li>Recognize cardiovascular emergencies</li>
    </ul>

    <a href="/">Back to Nursing Genius</a>
    """


@app.route("/pediatric-emergencies-nursing")
def pediatric_emergencies():

    return """
    <h1>Pediatric Emergencies Nursing Notes</h1>

    <h2>Common Emergencies</h2>
    <ul>
        <li>Severe dehydration</li>
        <li>Respiratory distress</li>
        <li>Seizures</li>
        <li>Severe infections</li>
    </ul>

    <h2>Nursing Management</h2>
    <ul>
        <li>Rapid assessment</li>
        <li>Maintain airway and breathing</li>
        <li>Monitor vital signs</li>
        <li>Provide emergency treatment</li>
    </ul>

    <a href="/">Back to Nursing Genius</a>
    """  
@app.route("/page/<slug>")
def seo_page(slug):

    connection = sqlite3.connect("nursing_genius.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT title, content FROM seo_pages WHERE slug=?",
        (slug,)
    )

    page = cursor.fetchone()

    connection.close()

    if page:
        return render_template(
            "seo_page.html",
            page=page
        )

    return "Page not found" 
         
@app.route("/add_seo_page", methods=["GET","POST"])
def add_seo_page():

    if session.get("role") != "admin":
        return "Access Denied!"

    connection = sqlite3.connect("nursing_genius.db")
    cursor = connection.cursor()

    if request.method == "POST":

        title = request.form["title"]
        slug = request.form["slug"]
        content = request.form["content"]

        cursor.execute("""
        INSERT INTO seo_pages(title,slug,content)
        VALUES(?,?,?)
        """,
        (title,slug,content))

        connection.commit()
        connection.close()

        return "SEO Page Created Successfully"

    connection.close()

    return """
    <form method="POST">

    Title:
    <input name="title"><br>

    Slug:
    <input name="slug"><br>

    Content:
    <textarea name="content"></textarea><br>

    <button>
    Create Page
    </button>

    </form>
    """
@app.route("/sitemap.xml")
def sitemap():

    pages = [

        "/",
        "/notes",
        "/quiz",
        "/subjects",
        "/register",

        "/hypertension-nursing-management",
        "/antibiotics-pharmacology-nursing",
        "/imnci-guidelines-nursing",
        "/child-immunization-schedule",
        "/diabetes-nursing-management",
        "/anatomy-cardiovascular-system",
        "/pediatric-emergencies-nursing"
    ]

    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    today = datetime.date.today().isoformat()

    for page in pages:
        xml.append(f"""
<url>
    <loc>https://nursing-genius5.onrender.com{page}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
</url>
""")

    xml.append("</urlset>")

    return Response(
        "\n".join(xml),
        mimetype="application/xml"
    )
    
@app.route("/ai", methods=["GET", "POST"])
def ai():

    answer = ""

    if request.method == "POST":

        question = request.form["question"]

        result = ask_ai(question)

        answer = f"""
        <h2>{result['title']}</h2>
        <p>{result['answer']}</p>
        <small>Source: {result['source']}</small>
        """

    return render_template(
        "ai.html",
        answer=answer
        )
@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/search")
def search():

    keyword = request.args.get("q", "")

    connection = sqlite3.connect("nursing_genius.db")
    cursor = connection.cursor()

    cursor.execute("""
    SELECT topic, content
    FROM notes
    WHERE topic LIKE ?
       OR content LIKE ?
    """, (
        "%" + keyword + "%",
        "%" + keyword + "%"
    ))

    results = cursor.fetchall()

    connection.close()

    return render_template(
        "search.html",
        keyword=keyword,
        results=results
    )


@app.route("/profile")
def profile():

    if "user" not in session:
        return redirect("/login")

    connection = sqlite3.connect("nursing_genius.db")
    cursor = connection.cursor()

    cursor.execute("""
    SELECT fullname,
           email,
           profile_picture,
           xp,
           streak,
           badges
    FROM users
    WHERE email=?
    """, (session["user"],))

    user = cursor.fetchone()
    print(user)

    connection.close()

    return render_template(
        "profile.html",
        user=user
    )
        
              
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)