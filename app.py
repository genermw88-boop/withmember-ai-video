import streamlit as st
import google.generativeai as genai
import time
import json
import os
import requests
from openai import OpenAI

# 1. 시스템 설정 및 API 인증
st.set_page_config(page_title="위드멤버 AI 영상 센터", layout="wide")

try:
    # Secrets에서 키 불러오기
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    ELEVENLABS_API_KEY = st.secrets.get("ELEVENLABS_API_KEY", "")
    st.sidebar.success("✅ 위드멤버 엔진 인증 완료")
except Exception as e:
    st.sidebar.error("❌ Secrets 설정을 확인해주세요 (GEMINI_API_KEY 등)")

# 2. 프롬프트 설정 (위드멤버 전용 로직)
SYSTEM_PROMPT = """
당신은 마케팅 대행사 '위드멤버'의 AI 전략가입니다. 
영상을 보고 사장님의 진심이 담긴 **친근한 존댓말**로 다음 패키지를 만드세요.

1. IG_Empathy (인스타): 공감형, POV, 감성적 키워드 중심.
2. YT_Info (유튜브): 정보성, 신뢰감, 매장 장점 및 팩트 중심.

반드시 아래 JSON 형식으로만 답변하세요:
{
  "ig": {"script": "대본내용", "title": "제목", "tags": "#태그", "comment": "고정댓글"},
  "yt": {"script": "대본내용", "title": "제목", "tags": "#태그", "comment": "고정댓글"}
}
"""

# 3. 일레븐랩스 목소리 생성 함수
def generate_narration(text, voice_id="ko-KR-Standard-A"):
    if not ELEVENLABS_API_KEY:
        return None
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
    }
    response = requests.post(url, json=data, headers=headers)
    return response.content if response.status_code == 200 else None

# 4. 앱 UI
st.title("🚀 위드멤버 AI 영상 일괄 처리 스튜디오")
st.write("최대 10개의 영상을 한 번에 업로드하고 마케팅 패키지를 만드세요.")

uploaded_files = st.file_uploader("영상을 선택하세요 (최대 10개)", type=['mp4', 'mov'], accept_multiple_files=True)

if 'results' not in st.session_state:
    st.session_state.results = {}

if uploaded_files:
    if st.button("🔥 모든 영상 일괄 처리 시작"):
        status_area = st.empty()
        progress_bar = st.progress(0)
        
        for idx, file in enumerate(uploaded_files):
            status_area.info(f"⏳ ({idx+1}/{len(uploaded_files)}) {file.name} 분석 중...")
            
            # 파일 임시 저장
            with open("temp.mp4", "wb") as f:
                f.write(file.getbuffer())
            
            try:
                # [핵심] Gemini 1.5 Flash 사용 및 대기 로직
                video_file = genai.upload_file(path="temp.mp4")
                
                # 파일이 'ACTIVE' 상태가 될 때까지 대기 (404 에러 방지 핵심)
                while video_file.state.name == "PROCESSING":
                    time.sleep(2)
                    video_file = genai.get_file(video_file.name)
                
                # 모델 호출 (가장 안정적인 모델명 사용)
                model = genai.GenerativeModel(model_name="gemini-1.5-flash")
                response = model.generate_content([SYSTEM_PROMPT, video_file])
                
                # 결과 파싱
                result_text = response.text.replace('```json', '').replace('```', '').strip()
                st.session_state.results[file.name] = json.loads(result_text)
                
            except Exception as e:
                st.error(f"❌ {file.name} 처리 중 오류: {str(e)}")
            
            progress_bar.progress((idx + 1) / len(uploaded_files))
        
        status_area.success("✅ 모든 영상 처리가 완료되었습니다!")
        st.balloons()

# 5. 결과 출력
if st.session_state.results:
    st.divider()
    for name, res in st.session_state.results.items():
        with st.expander(f"🎬 {name} 결과 확인", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📸 인스타 (공감형)")
                st.info(res['ig']['script'])
                if st.button(f"🔊 목소리 듣기 (인스타) - {name}"):
                    audio = generate_narration(res['ig']['script'])
                    if audio: st.audio(audio)
            with c2:
                st.subheader("📺 유튜브 (정보성)")
                st.success(res['yt']['script'])
                if st.button(f"🔊 목소리 듣기 (유튜브) - {name}"):
                    audio = generate_narration(res['yt']['script'])
                    if audio: st.audio(audio)
