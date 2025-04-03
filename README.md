# 🌟 Clickers / Click Us 🌟

# 𝔸𝕝𝕡𝕙𝕒 𝔸𝕘𝕖𝕟𝕥
![화면 기록 2025-04-04 오전 4 26 58](https://github.com/user-attachments/assets/84b6e9e3-458e-46b0-b8b4-63d34ef9d284)


---

## 📌 Introduction

Clickers는 데모 시연을 위한 인프라 코드로, **Streamlit (Frontend)** 와 **FastAPI (Backend)** 로 구성되어 있습니다.

---

## 🚀 Quick Start

### ✅ 환경 세팅 (Python 3.10 / Conda 환경)

1. **Conda 가상환경 설치 및 활성화**

```bash
conda create -n infra python=3.10
conda activate infra
pip install -r requirements.txt
```

2. **환경 변수 설정 (.env 파일 생성)**

```plaintext
EMAIL_ADDRESS=your_email@gmail.com
APP_PASSWORD=your_16_digit_app_password
```

3. **설정 파일 배치 (config/config.yaml)**

---

### 🔥 실행 방법

#### Backend 실행하기 (FastAPI)

```bash
uvicorn backend.main:app --reload
```

FastAPI 서버가 실행되며 기본적으로 [http://127.0.0.1:8000](http://127.0.0.1:8000) 에서 동작합니다.

#### Frontend 실행하기 (Streamlit)

```bash
streamlit run frontend/main.py
```

Streamlit 서버가 실행되며 기본적으로 [http://localhost:8501](http://localhost:8501) 에서 동작합니다.

---

### ⚠️ 주의사항

이 프로젝트는 데모용 인프라 설정이므로, 모델(에이전트) 실행 파일과 서버, 프론트엔드는 모두 동일한 로컬 서버에서 실행되어야 합니다.

클라우드 또는 다른 서버를 사용하려면 Public IP 및 포트 설정이 필요합니다.

---

## 📁 Directory Structure

```
.
├── config
│   ├── config.yaml
│   └── config_loader.py
├── requirements.txt
├── .env
```

---

## 📜 Requirements

```bash
pip install -r requirements.txt
```

requirements.txt 파일에는 프로젝트에서 사용하는 모든 패키지가 포함되어 있습니다.

---



