import streamlit as st
import google.generativeai as genai
import time
import json
import os
import requests

# 1. 페이지 설정 및 보안 인증
st.set_page_config(page_title="위드멤버 AI 영상 센터", layout="wide")

try:
    # Secrets에서 키 자동 로드
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    ELEVENLABS_API_KEY = st.secrets["ELEVENLABS_API_KEY"]
    
    # Gemini 설정
    genai.configure(api_key=GEMINI_API_KEY)
    st.sidebar.success("✅ 위드멤버 시스템 권한 인증 완료")
except Exception as e:
    st.sidebar.error("❌ Secrets에 API 키를 등록해주세요! (GEMINI_API_KEY, ELEVENLABS_API_KEY)")

# 2. 마케팅 기획 프롬프트 (위드멤버 전용)
SYSTEM_PROMPT = """
당신은 대한민국 최고의 마케팅 대행사 '위드멤버'의 AI 전략가입니다.
영상을 분석하여 사장님의 진심이 담긴 **친근한 존댓말**로 다음 패키지를 만드세요.

1. IG_Empathy (인스타): 공감형, 1인칭 POV, 감성적 단어 사용. (예: "고생한 나에게 주는 선물")
2. YT_Info (유튜브): 정보성, 신뢰감, 매장의 강점과 팩트 중심. (예: "1++ 등급 한우의 비결")

반드시 아래 JSON 형식으로만 답변하세요 (다른 설명은 생략하세요):
{
  "ig": {"script": "대본내용", "title": "제목", "tags": "#태그1 #태그2", "comment": "고정댓글"},
  "yt": {"script": "대본내용", "title": "제목", "tags": "#태그1 #태그2", "comment": "고정댓글"}
}
"""

# 3. 일레븐랩스 목소리 생성 엔진
def generate_audio(text, file_name):
    # 인스타/유튜브 성격에 맞춰 목소리를 선택할 수 있습니다.
    # ko-KR-Standard-A (여성), ko-KR-Standard-B (남성) 등 ID 사용 가능
    url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM" # Bella 목소리 예시
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        with open(file_name, 'wb') as f:
            f.write(response.content)
        return True
    return False

# 4. 앱 메인 화면
st.title("🚀 위드멤버 AI 영상 일괄 처리 스튜디오")
st.info("촬영하신 영상을 최대 10개까지 한꺼번에 분석하고 마케팅 패키지를 생성합니다.")

uploaded_files = st.file_uploader("영상 파일을 업로드하세요 (최대 10개)", type=['mp4', 'mov'], accept_multiple_files=True)

# 결과 저장을 위한 상태 관리
if 'all_results' not in st.session_state:
    st.session_state.all_results = {}

if uploaded_files:
    if st.button(f"🔥 총 {len(uploaded_files)}개 영상 일괄 처리 시작"):
        progress_bar = st.progress(0)
        status_area = st.empty()
        
        for idx, file in enumerate(uploaded_files):
            file_name = file.name
            status_area.info(f"⏳ ({idx+1}/{len(uploaded_files)}) '{file_name}' 영상 요리 중...")
            
            # 임시 파일 저장
            with open("temp.mp4", "wb") as f:
                f.write(file.getbuffer())
            
            try:
                # [핵심] Gemini 업로드 및 대기 (404/NotFound 방지 로직)
                video_part = genai.upload_file(path="temp.mp4")
                
                # 영상 처리 대기 루프
                while video_part.state.name == "PROCESSING":
                    time.sleep(3)
                    video_part = genai.get_file(video_part.name)
                
                # [핵심] 모델 호출 (Tier 1 사용자를 위한 안정적 호출)
                model = genai.GenerativeModel(model_name="gemini-1.5-flash")
                response = model.generate_content([SYSTEM_PROMPT, video_part])
                
                # JSON 파싱
                clean_json = response.text.replace('```json', '').replace('```', '').strip()
                st.session_state.all_results[file_name] = json.loads(clean_json)
                
            except Exception as e:
                st.error(f"❌ '{file_name}' 처리 중 에러: {str(e)}")
            
            progress_bar.progress((idx + 1) / len(uploaded_files))
            
        status_area.success("✅ 모든 영상 처리가 완료되었습니다!")
        st.balloons()

# 5. 결과물 대시보드 출력
if st.session_state.all_results:
    st.divider()
    st.header("📂 마케팅 패키지 결과물")
    
    for file_name, res in st.session_state.all_results.items():
        with st.expander(f"🎬 {file_name} - 플랫폼별 기획안 보기", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📸 인스타 (공감/감성)")
                st.write(f"**제목:** {res['ig']['title']}")
                st.info(res['ig']['script'])
                st.caption(f"태그: {res['ig']['tags']}")
                
                if st.button(f"🔊 목소리 듣기 (인스타) - {file_name}"):
                    audio_fn = f"audio_ig_{file_name}.mp3"
                    if generate_audio(res['ig']['script'], audio_fn):
                        st.audio(audio_fn)
            
            with col2:
                st.subheader("📺 유튜브 (정보/신뢰)")
                st.write(f"**제목:** {res['yt']['title']}")
                st.success(res['yt']['script'])
                st.caption(f"태그: {res['yt']['tags']}")
                
                if st.button(f"🔊 목소리 듣기 (유튜브) - {file_name}"):
                    audio_fn = f"audio_yt_{file_name}.mp3"
                    if generate_audio(res['yt']['script'], audio_fn):
                        st.audio(audio_fn)
