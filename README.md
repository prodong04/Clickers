# 🌟 Clickers / Click Us 🌟

# 𝔸𝕝𝕡𝕙𝕒 𝔸𝕘𝕖𝕟𝕥
![Demo](https://github.com/user-attachments/assets/84b6e9e3-458e-46b0-b8b4-63d34ef9d284)

---

## 📌 Introduction

Clickers is an infrastructure code for demonstration purposes, consisting of **Streamlit (Frontend)** and **FastAPI (Backend)**.

---

## 🚀 Quick Start

### ✅ Environment Setup (Python 3.10 / Conda Environment)

1. **Create and activate Conda virtual environment**

```bash
conda create -n infra python=3.10
conda activate infra
pip install -r requirements.txt
```

2. **Set environment variables (.env file)**

```plaintext
EMAIL_ADDRESS=your_email@gmail.com
APP_PASSWORD=your_16_digit_app_password
```

3. **Place the configuration file (config/config.yaml)**

---

### 🔥 How to Run

#### Run Backend (FastAPI)

```bash
uvicorn backend.main:app --reload
```

The FastAPI server will run at [http://127.0.0.1:8000](http://127.0.0.1:8000) by default.

#### Run Frontend (Streamlit)

```bash
streamlit run frontend/main.py
```

The Streamlit server will run at [http://localhost:8501](http://localhost:8501) by default.

---

### ⚠️ Notes

This project is set up for demonstration purposes, so the model (agent), server, and frontend must all be run on the same local server.

If you want to use a cloud or another server, you need to configure the Public IP and ports accordingly.

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

The requirements.txt file includes all the packages used in the project.

---
## 🌟 Contributors

This project is part of the Yonsei University X Upstage Agent Hackathon Team "Clickers."  

Here are the contributors to this project. Thank you all! 💪🚀

| GitHub ID                                 | Role             |
| --------------------------------------- | ----------------- |
| [Kim Bodam](https://github.com/qhdamm)   |  |
| [Jeong Hoesu](https://github.com/Hoesu)  |  |
| [Choe Suhyun](https://github.com/imsuviiix)|  |
| [Lim Chaerim](https://github.com/C-limlim)|  |
| [Lee Dongryeol](https://github.com/prodong04)|  |

