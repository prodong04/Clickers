from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from subprocess import run, PIPE
import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/run-report/")
def run_report(
    start_date: str = Form(...),
    end_date: str = Form(...),
    user_tendency: str = Form(...),
    email: str = Form(...)
):
    # 1️⃣ subprocess 실행
    result = run(
        ["python", "test_agent.py", start_date, end_date, user_tendency, email],
        stdout=PIPE,
        stderr=PIPE,
        text=True,
    )

    if result.returncode != 0:
        return {"status": "error", "detail": result.stderr}

    # 2️⃣ 결과 이메일로 전송
    send_email(email, result.stdout)

    return {"status": "success", "message": "이메일 전송 완료"}

def send_email(to_email, body):
    msg = MIMEText(body)
    msg["Subject"] = "📊 AI 기반 포트폴리오 추천 리포트"
    msg["From"] = os.getenv("EMAIL_HOST_USER")
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.getenv("EMAIL_HOST_USER"), os.getenv("EMAIL_HOST_PASSWORD"))
        server.send_message(msg)
