import streamlit as st
import datetime
import time
import requests

# 세션 상태 초기화
if "reset_token" not in st.session_state:
    st.session_state["reset_token"] = 0
if "show_modal" not in st.session_state:
    st.session_state["show_modal"] = False

# 세션 키 만들기
tendency_key = f"user_tendency_{st.session_state['reset_token']}"
email_key = f"user_email_{st.session_state['reset_token']}"

# 스타일
st.markdown("""
<style>
.modal {
    position: fixed;
    top: 0; left: 0;
    width: 100vw; height: 100vh;
    background: rgba(0, 0, 0, 0.85);
    z-index: 9999;
    display: flex;
    justify-content: center;
    align-items: center;
}
.modal-box {
    background: #fff;
    padding: 3rem;
    border-radius: 1rem;
    box-shadow: 0 20px 50px rgba(0,0,0,0.3);
    text-align: center;
    max-width: 90%;
    font-family: 'Segoe UI', sans-serif;
}
.modal-box h1 {
    color: #2e7d32;
    font-size: 2rem;
    margin-bottom: 1rem;
}
.modal-box p {
    color: #333;
    font-size: 1.1rem;
    margin-bottom: 1rem;
}
.modal-box small {
    display: block;
    margin-top: 1.5rem;
    font-size: 0.9rem;
    color: #888;
}
</style>
""", unsafe_allow_html=True)

# 메인 화면
st.title("📊 AI 기반 포트폴리오 추천 서비스")

user_tendency = st.text_input(
    "투자 성향을 작성해주세요!",
    placeholder="예: 테슬라 50% 하락? 추가 매수 시즌이다!!!",
    key=tendency_key
)

user_email = st.text_input(
    "이메일을 입력해주세요",
    placeholder="example@email.com",
    key=email_key
)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("시작하는 날짜", value=datetime.date.today())
with col2:
    end_date = st.date_input("끝나는 날짜", value=datetime.date.today())

if st.button("포트폴리오 추천 보고서 요청하기"):
    if not st.session_state[tendency_key] or not st.session_state[email_key]:
        st.warning("투자 성향과 이메일을 모두 입력해주세요.")
    elif start_date > end_date:
        st.warning("끝 기간은 시작 기간보다 이후여야 합니다.")
    else:
        with st.spinner("알파 에이전트에게 연락하는 중..."):
            time.sleep(2.5)
        with st.spinner(f"{start_date} ~ {end_date} 기간의 리포트 작성 요청 중..."):
            time.sleep(2.5)
        st.session_state["show_modal"] = True
        
        payload = {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "user_tendency": st.session_state[tendency_key],
            "email": st.session_state[email_key],
        }
        
        try:
            response = requests.post("http://127.0.0.1:8000/run-report/", data=payload)
        except Exception as e:
            print(e)
            pass
        
        st.rerun()

# 모달 출력
if st.session_state["show_modal"]:
    st.session_state["show_modal"] = False

    st.markdown(
        """
        <div class="modal">
            <div class="modal-box">
                <h1>🎉 리포트 요청 완료!</h1>
                <p>완성되는 순간 이메일로 전송 예정 ✨📩</p>
                <small>5초 후 새로고침돼요! 먄약 사라지지 않으면 F5클릭💡</small>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    time.sleep(5)

    # ✅ 입력값 초기화 = reset_token 증가해서 다른 key로 유도
    st.session_state["reset_token"] += 1
    st.rerun()
