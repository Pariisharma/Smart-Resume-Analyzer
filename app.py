from flask import Flask, render_template, request, session, redirect, url_for, flash
from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
import PyPDF2
from docx import Document
from google import genai
import os
import re
from skills import skills_list
from jobs_data import jobs
from dotenv import load_dotenv
load_dotenv()

# ================= ATS CONFIG =================

required_sections = [
    "education",
    "experience",
    "skills",
    "projects",
    "certifications",
    "summary"
]

# ================= APP SETUP =================

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")  # Change in production

# ================= GOOGLE OAUTH =================

oauth = OAuth(app)

app.config['GOOGLE_CLIENT_ID'] = os.getenv("GOOGLE_CLIENT_ID")
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv("GOOGLE_CLIENT_SECRET")

google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# ================= LOGIN SETUP =================

bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = None

# Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ================= FAKE DATABASE =================

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(150))
    password = db.Column(db.String(200))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= AUTH ROUTES =================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Passwords do not match!", "register_error")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists!", "register_error")
            return redirect(url_for("register"))

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        new_user = User(username=username, name=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("home"))

        flash("Invalid username or password.", "login_error")
        return render_template("login.html")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ================= GOOGLE LOGIN =================

@app.route("/google-login")
def google_login():
    redirect_uri = url_for('auth_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route("/auth/callback")
def auth_callback():
    token = google.authorize_access_token()

    user_info = token.get("userinfo")

    if not user_info:
        user_info = google.get("userinfo").json()

    email = user_info["email"]
    full_name = user_info.get("name", "")

    first_name = full_name.split(" ")[0] if full_name else "User"

    existing_user = User.query.filter_by(username=email).first()

    if not existing_user:
        new_user = User(username=email, name=first_name)
        db.session.add(new_user)
        db.session.commit()
        existing_user = new_user

    login_user(existing_user)
    return redirect(url_for("home"))

   

# ================= MAIN ROUTES =================

@app.route("/")
def root():
    return redirect(url_for("login"))

@app.route("/home")
@login_required
def home():
    return render_template("index.html", username=current_user.name)

@app.route("/upload", methods=["POST"])
@login_required
def upload():

    if "resume" not in request.files:
        return "No file uploaded", 400

    file = request.files["resume"]
    if file.filename == '':
        return "No selected file", 400

    # ===== Extract Text =====
    try:
        filename = file.filename.lower()

        if filename.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(file)
            text = "".join([page.extract_text() or "" for page in pdf_reader.pages])

        elif filename.endswith(".docx"):
            doc = Document(file)
            text = "\n".join([para.text for para in doc.paragraphs])

        else:
            return "Unsupported file format. Please upload PDF or DOCX.", 400

    except Exception:
        return "Error processing file", 500

    text_lower = text.lower()
    # ===== ATS SECTION DETECTION =====

    found_sections = []
    missing_sections = []

    for section in required_sections:
        if re.search(r'\b' + re.escape(section) + r'\b', text_lower):
            found_sections.append(section)
        else:
            missing_sections.append(section)

    truncated_text = text[:3000]

    # ===== AI Analysis =====
    prompt = f"""
    Analyze the following resume.

    STRENGTHS:
    - Short bullet point

    WEAKNESSES:
    - Short bullet point

    IMPROVEMENTS:
    - Short bullet point

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
    except Exception:
        ai_feedback = "AI feedback currently unavailable."

    # ===== SKILL EXTRACTION =====
    found_skills = []

    for skill in skills_list:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.append(skill)

    # ===== ATS KEYWORD DENSITY =====
    total_words = len(text_lower.split())
    keyword_density = (len(found_skills) / total_words) * 100

    # ===== ATS SCORE CALCULATION =====
    section_score = (len(found_sections) / len(required_sections)) * 100
    density_score = keyword_density

    ats_score = round((section_score * 0.5) + (density_score * 0.5), 2)

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
        ai_feedback=ai_feedback,
        ats_score=ats_score,
        found_sections=found_sections,
        missing_sections=missing_sections,
        keyword_density=round(keyword_density, 2)
    )

with app.app_context():
    db.create_all()

# ================= RUN =================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)