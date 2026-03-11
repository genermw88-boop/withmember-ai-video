import streamlit as st
import google.generativeai as genai
import time
import json
import os
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
import moviepy.video.fx.all as vfx

# 1. 시스템 설정 및 API 인증
st.set_page_config(page_title="위드멤버 AI 영상 센터", layout="wide")

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    ELEVENLABS_API_KEY = st.secrets.get("ELEVENLABS_API_KEY", "")
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    st.sidebar.error("❌ Secrets에 API 키를 등록해주세요!")

# 2. 마케팅 기획 프롬프트 (15초, 유머/재미 추가)
SYSTEM_PROMPT = """
당신은 대한민국 1타 숏폼 마케터입니다. 영상을 보고 **무조건 15초~18초 분량 (말하기 속도 기준 약 60~70자)**의 대본을 쓰세요.
딱딱한 설명은 버리고, 요즘 릴스/쇼츠 트렌드에 맞게 **아주 재밌고, 톡톡 튀고, 시선을 끄는 멘트**를 쓰세요.

1. IG_Empathy (인스타): 감성적이면서도 위트 있는 1인칭 시점. (예: "아니, 사장님 이렇게 퍼주시면 남는 거 있어요?!")
2. YT_Info (유튜브): 팩트를 짚어주되 지루하지 않은 속도감 있는 리뷰톤.

반드시 아래 JSON 형식으로만 답변하세요:
{
  "ig": {"script": "15초 분량의 재밌는 대본", "title": "제목", "tags": "#태그", "comment": "고정댓글"},
  "yt": {"script": "15초 분량의 팩트체크 대본", "title": "제목", "tags": "#태그", "comment": "고정댓글"}
}
"""

# 3. 일레븐랩스 음성 생성
def generate_audio(text, output_path):
    if not ELEVENLABS_API_KEY:
        return False
    # 목소리 ID (원하시는 ID로 나중에 변경하세요)
    url = "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM" 
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
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return True
    return False

# 4. 🔥 핵심: 영상 + 목소리 자동 합성 엔진
def create_final_video(video_path, audio_path, output_path):
    try:
        vid = VideoFileClip(video_path)
        aud = AudioFileClip(audio_path)
        
        # 원본 영상이 목소리보다 짧으면 목소리 길이에 맞춰 반복(Loop)
        if vid.duration < aud.duration:
            vid = vid.fx(vfx.loop, duration=aud.duration)
        else:
            # 원본 영상이 더 길면 목소리 길이에 맞춰서 컷(Cut)
            vid = vid.subclip(0, aud.duration)
            
        # 영상에 AI 목소리 입히기
        final_vid = vid.set_audio(aud)
        
        # 최종 렌더링 (빠른 속도를 위해 preset 설정)
        final_vid.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
        
        # 메모리 정리
        vid.close()
        aud.close()
        final_vid.close()
        return True
    except Exception as e:
        st.error(f"영상 합성 중 에러: {str(e)}")
        return False

# 5. 앱 메인 화면
st.title("🚀 위드멤버 AI 영상 일괄 제작 스튜디오")
st.info("기획부터 대본, 목소리 녹음, 최종 영상 편집까지 한 번에 끝냅니다.")

uploaded_files = st.file_uploader("영상을 업로드하세요 (초기 테스트는 1~2개 권장)", type=['mp4', 'mov'], accept_multiple_files=True)

if uploaded_files:
    if st.button(f"🎬 총 {len(uploaded_files)}개 자동 영상 제작 시작"):
        progress_bar = st.progress(0)
        status_area = st.empty()
        
        for idx, file in enumerate(uploaded_files):
            file_name = file.name
            base_name = file_name.split('.')[0]
            status_area.info(f"⏳ ({idx+1}/{len(uploaded_files)}) '{file_name}' AI 분석 및 편집 중...")
            
            # 원본 영상 임시 저장
            raw_video_path = f"raw_{file_name}"
            with open(raw_video_path, "wb") as f:
                f.write(file.getbuffer())
            
            try:
                # [1단계: AI 분석 및 기획]
                video_part = genai.upload_file(path=raw_video_path)
                while video_part.state.name == "PROCESSING":
                    time.sleep(3)
                    video_part = genai.get_file(video_part.name)
                
                model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
                response = model.generate_content([SYSTEM_PROMPT, video_part])
                clean_json = response.text.replace('```json', '').replace('```', '').strip()
                res_data = json.loads(clean_json)
                
                # [2단계: 플랫폼별 음성 생성 및 영상 합성]
                for platform, key in [("인스타", "ig"), ("유튜브", "yt")]:
                    audio_path = f"audio_{key}_{base_name}.mp3"
                    final_video_path = f"final_{key}_{base_name}.mp4"
                    
                    # 목소리 생성
                    if generate_audio(res_data[key]['script'], audio_path):
                        # 영상 합성
                        create_final_video(raw_video_path, audio_path, final_video_path)
                        
                        # 화면에 완성된 결과 띄우기
                        with st.expander(f"✨ [{platform}] 완성본: {file_name}", expanded=True):
                            st.write(f"**📝 기획안:** {res_data[key]['title']}")
                            st.info(f"대본: {res_data[key]['script']}")
                            
                            # 완성된 영상 플레이어 및 다운로드 버튼
                            if os.path.exists(final_video_path):
                                st.video(final_video_path)
                                with open(final_video_path, "rb") as v_file:
                                    st.download_button(
                                        label=f"⬇️ [{platform}] 완성 영상 다운로드",
                                        data=v_file,
                                        file_name=final_video_path,
                                        mime="video/mp4"
                                    )
                                    
            except Exception as e:
                st.error(f"❌ '{file_name}' 처리 중 에러: {str(e)}")
            
            progress_bar.progress((idx + 1) / len(uploaded_files))
            
        status_area.success("✅ 모든 영상 기획 및 제작이 완료되었습니다!")
        st.balloons()
