## INFRA
데모 시연을 위한 인프라 코드를 모아둔 폴더입니다.

streamlit (front) + fastapi (backend) 로 구성되어 있습니다.

### 환경세팅
1. 가상환경 설치
```
conda create infra
conda activate infra
pip install -r requirements.txt
```

2. env 세팅
```
(1) 이메일 발신자 (email address)
(2) 해당 계정에서 앱비밀번호(16자리) 발급받아 작성
```

3. 코드 실행
```
# backend 실행
uvicorn backend.main:app --reload 

# frontend 실행
streamlit run frontend/main.py
```

4. 주의사항
```
데모용 인프라 설정이므로 모델(에이전트) 실행 파일과 서버, 그리고 프론트는 모두 한 로컬 서버에서 돌아가야합니다.
만약 클라우드 혹은 다른 서버를 사용하게 될 경우, public ip 그리고 port 등의 추가 설정이 필요합니다.
```

