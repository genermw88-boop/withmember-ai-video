import streamlit as st
import google.generativeai as genai
import time
import json
import os
import requests
from moviepy.editor import VideoFileClip, AudioFileClip
import moviepy.video.fx.all as vfx

# 1. 시스템 설정
st.set_page_config(page_title="위드멤버 AI 영상 센터", layout="wide")

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    ELEVENLABS_API_KEY = st.secrets.get("ELEVENLABS_API_KEY", "")
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    st.sidebar.error("❌ Secrets에 API 키를 등록해주세요!")

# 2. 사이드바 (마케팅 브리프)
st.sidebar.header("📝 마케팅 브리프")
store_name = st.sidebar.text_input("상호명 (예: 동경생고기)", "")
main_menu = st.sidebar.text_input("주력 메뉴 (예: 1++ 한우 특수부위)", "")
key_point = st.sidebar.text_area("강조할 포인트 (예: 단체 회식 환영)", "")

# 3. 프롬프트 생성 함수
def get_system_prompt(store, menu, point):
    store_text = store if store else "해당 매장"
    menu_text = menu if menu else "주요 상품"
    point_text = f"강조할 내용: {point}" if point else "특징을 잘 살려서 설명"
    
    return f"""
당신은 대한민국 1타 숏폼 마케터입니다. 영상을 보고 **무조건 15초 분량(약 60자)**의 대본을 쓰세요.
딱딱한 설명은 버리고, 요즘 트렌드에 맞게 재밌고 톡톡 튀는 멘트를 쓰세요.

[🎯 핵심 정보] 상호명: {store_text} / 주력 메뉴: {menu_text} / {point_text}

1. IG_Empathy (인스타): 위트 있는 1인칭 시점.
2. YT_Info (유튜브): 지루하지 않은 속도감 있는 리뷰톤.

반드시 아래 JSON 형식으로만 답변하세요:
{{
  "ig": {{"script": "15초 대본", "title": "제목", "tags": "#태그", "comment": "댓글"}},
  "yt": {{"script": "15초 대본", "title": "제목", "tags": "#태그", "comment": "댓글"}}
}}
"""

# 4. 일레븐랩스 음성 생성 (에러 출력 추가)
def generate_audio(text, output_path):
    if not ELEVENLABS_API_KEY:
        st.error("🔑 일레븐랩스 API 키가 없습니다.")
        return False
    url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM"
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY}
    data = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}}
    
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return True
    else:
        # 몰래 넘어가지 않고 에러 내용을 화면에 띄웁니다!
        st.error(f"❌ 일레븐랩스 에러: {response.text}")
        return False

# 5. 영상 합성 엔진
def create_final_video(video_path, audio_path, output_path):
    try:
        vid = VideoFileClip(video_path)
        aud = AudioFileClip(audio_path)
        if vid.duration < aud.duration:
            vid = vid.fx(vfx.loop, duration=aud.duration)
        else:
            vid = vid.subclip(0, aud.duration)
        final_vid = vid.set_audio(aud)
        final_vid.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
        vid.close()
        aud.close()
        final_vid.close()
        return True
    except Exception as e:
        st.error(f"❌ 합성 에러: {str(e)}")
        return False

# 6. 메인 화면
st.title("🚀 위드멤버 맞춤형 영상 제작 스튜디오")

uploaded_files = st.file_uploader("영상을 업로드하세요 (1개 권장)", type=['mp4', 'mov'], accept_multiple_files=True)

if uploaded_files:
    if st.button("🎬 맞춤형 영상 제작 시작"):
        final_prompt = get_system_prompt(store_name, main_menu, key_point)
        progress_bar = st.progress(0)
        status_area = st.empty()
        
        for idx, file in enumerate(uploaded_files):
            file_name = file.name
            base_name = file_name.split('.')[0]
            status_area.info(f"⏳ '{file_name}' 분석 중...")
            
            raw_video_path = f"raw_{file_name}"
            with open(raw_video_path, "wb") as f:
                f.write(file.getbuffer())
            
            try:
                # 1. AI 대본 기획
                video_part = genai.upload_file(path=raw_video_path)
                while video_part.state.name == "PROCESSING":
                    time.sleep(3)
                    video_part = genai.get_file(video_part.name)
                
                model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
                response = model.generate_content([final_prompt, video_part])
                res_data = json.loads(response.text.replace('```json', '').replace('```', '').strip())
                
                # 2. 결과 출력 (대본 무조건 먼저 출력)
                for platform, key in [("인스타", "ig"), ("유튜브", "yt")]:
                    with st.expander(f"✨ [{platform}] 기획안 및 영상: {file_name}", expanded=True):
                        st.write(f"**📝 {res_data[key]['title']}**")
                        st.info(res_data[key]['script'])
                        
                        audio_path = f"audio_{key}_{base_name}.mp3"
                        final_video_path = f"final_{key}_{base_name}.mp4"
                        
                        # 음성 및 영상 생성 시도
                        with st.spinner(f"[{platform}] 목소리 및 영상 합성 중..."):
                            if generate_audio(res_data[key]['script'], audio_path):
                                if create_final_video(raw_video_path, audio_path, final_video_path):
                                    if os.path.exists(final_video_path):
                                        st.video(final_video_path)
                                        with open(final_video_path, "rb") as v_file:
                                            st.download_button("⬇️ 영상 다운로드", v_file, file_name=final_video_path, mime="video/mp4")
                                
            except Exception as e:
                st.error(f"❌ '{file_name}' 에러: {str(e)}")
            
            progress_bar.progress((idx + 1) / len(uploaded_files))
            
        status_area.success("✅ 작업이 완료되었습니다!")
