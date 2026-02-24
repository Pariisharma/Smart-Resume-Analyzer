from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import PyPDF2
from google import genai
import os
import re
from skills import skills_list
from jobs_data import jobs

# ================= APP SETUP =================

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change this in production

bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ================= FAKE DATABASE (Temporary) =================

users = {}

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

# ================= AUTH ROUTES =================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in [u.username for u in users.values()]:
            flash("Username already exists!")
            return redirect(url_for("register"))

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        user = User(id=str(len(users)+1), username=username, password=hashed_password)
        users[user.id] = user

        flash("Account created successfully! Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        for user in users.values():
            if user.username == username and bcrypt.check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for("home"))

        flash("Invalid username or password.")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ================= MAIN ROUTES =================

@app.route("/")
@login_required
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
@login_required
def upload():

    if "resume" not in request.files:
        return "No file uploaded", 400

    file = request.files["resume"]
    if file.filename == '':
        return "No selected file", 400

    # ===== Extract Text from PDF =====
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = "".join([page.extract_text() or "" for page in pdf_reader.pages])
    except Exception as e:
        print(f"PDF Error: {e}")
        return "Error processing PDF file", 500

    text_lower = text.lower()
    truncated_text = text[:3000]

    # ===== AI Analysis =====
    prompt = f"""
    Analyze the following resume.

    IMPORTANT:
    Respond ONLY in this exact format.
    Do not add extra explanations.

    STRENGTHS:
    - Short bullet point
    - Short bullet point

    WEAKNESSES:
    - Short bullet point
    - Short bullet point

    IMPROVEMENTS:
    - Short bullet point
    - Short bullet point

    Keep points clear, concise, and professional.

    Resume:
    {truncated_text}
    """

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt,
            config={"temperature": 0.4}
        )
        ai_feedback = response.text
    except Exception as e:
        print("Gemini Error:", e)
        ai_feedback = "AI feedback currently unavailable."

    # ===== Skill Extraction =====
    found_skills = []
    for skill in skills_list:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.append(skill)

    # ===== Job Matching =====
    job_results = []

    for job, required_skills in jobs.items():
        matched_skills = set(found_skills).intersection(set(required_skills))
        match_percentage = (len(matched_skills) / len(required_skills)) * 100 if required_skills else 0

        job_results.append({
            "job": job,
            "match": round(match_percentage, 2),
            "matched_skills": list(matched_skills),
            "missing_skills": list(set(required_skills) - set(found_skills))
        })

    job_results.sort(key=lambda x: x["match"], reverse=True)
    recommended_job = job_results[0] if job_results else None
    overall_score = recommended_job['match'] if recommended_job else 0

    return render_template(
        "result.html",
        skills=found_skills,
        jobs=job_results,
        overall_score=overall_score,
        recommended_job=recommended_job,
        ai_feedback=ai_feedback
    )

# ================= RUN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)