from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from subprocess import run, PIPE
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
import os
from dotenv import load_dotenv
from test_agent import process_investment

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
    

    html_file_paths = process_investment(start_date, end_date, user_tendency)
    send_email(email, html_file_paths)

    return {"status": "success", "message": "이메일 전송 완료"}

def send_email(to_email, html_file_paths):
    # print(body)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "📊 알파에이전트가 보낸 포트폴리오 추천 리포트가 도착했어요!!"
    msg["From"] = os.getenv("EMAIL_HOST_USER")
    msg["To"] = to_email
    msg.attach(MIMEText("📩 첨부된 리포트 파일을 확인해주세요!", "plain"))
    
    for path in html_file_paths:
        file_path = Path(path)
        if not file_path.exists():
            print(f"❗파일 없음: {file_path}")
            continue

        with open(file_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{file_path.name}"'
            )
            msg.attach(part)
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(os.getenv("EMAIL_HOST_USER"), os.getenv("EMAIL_HOST_PASSWORD"))
            server.send_message(msg)
    except Exception as e:
        print(f"Error sending email: {e}")
        pass