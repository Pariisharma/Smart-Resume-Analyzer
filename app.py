from flask import Flask, render_template, request, session, redirect, url_for, flash
from authlib.integrations.flask_client import OAuth
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import PyPDF2
from google import genai
import os
import re
from skills import skills_list
from jobs_data import jobs
from dotenv import load_dotenv
load_dotenv()

# ================= APP SETUP =================

app = Flask(__name__)
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

# Gemini Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ================= FAKE DATABASE =================

users = {}

class User(UserMixin):
    def __init__(self, id, username, name=None, password=None):
        self.id = id
        self.username = username
        self.name = name
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

    # Extract first name
    first_name = full_name.split(" ")[0] if full_name else "User"

    existing_user = None
    for user in users.values():
        if user.username == email:
            existing_user = user

    if not existing_user:
        user = User(
            id=str(len(users)+1),
            username=email,
            name=first_name
        )
        users[user.id] = user
        existing_user = user

    login_user(existing_user)

    return redirect(url_for("home"))
   

# ================= MAIN ROUTES =================

@app.route("/")
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
        pdf_reader = PyPDF2.PdfReader(file)
        text = "".join([page.extract_text() or "" for page in pdf_reader.pages])
    except Exception:
        return "Error processing PDF file", 500

    text_lower = text.lower()
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