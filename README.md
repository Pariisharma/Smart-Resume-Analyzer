# 🧠 Smart Resume Analyzer with ATS Simulation

An AI-powered Resume Analysis Web Application built using Flask that simulates an Applicant Tracking System (ATS) and provides job-matching insights.

---

## 🌐 Live Demo

https://smart-resume-analyzer-lt6s.onrender.com

## 🚀 Features

- 🔐 User Authentication (Manual + Google OAuth)
- 📄 Resume Upload (PDF & DOCX Support)
- 🤖 AI-Based Resume Feedback (Gemini API)
- 📊 ATS Score Simulation
- 🧩 Resume Section Detection
- 🎯 Skill Extraction Engine
- 💼 Job Recommendation System
- 🌙 Dark / Light Mode UI
- 📈 Animated Score Visualization

---

## 🏗️ Tech Stack

**Backend**
- Flask
- Flask-Login
- Flask-Bcrypt
- Flask-SQLAlchemy

**Frontend**
- HTML5
- CSS3 (Glassmorphism UI)
- Bootstrap 5
- JavaScript

**AI & Parsing**
- Google Gemini API
- PyPDF2 (PDF parsing)
- python-docx (DOCX parsing)
- Regex-based NLP

---

## 🧮 How ATS Score Works

The ATS score is calculated based on:

- Resume Section Detection (Education, Experience, Skills, etc.)
- Technical Skill Matching
- Keyword Presence & Density

The final score represents how optimized the resume is for automated screening systems.

---

## ⚠️ Note

This project simulates ATS behavior for educational purposes.  
It does not replicate proprietary enterprise ATS systems like Workday or Taleo.

---

## 🔧 Installation

```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt