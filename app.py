import streamlit as st
import google.generativeai as genai
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip
from openai import OpenAI
import json
import os
from prompts import SYSTEM_PROMPT

# API 키 설정
os.environ["OPENAI_API_KEY"] = st.sidebar.text_input("OpenAI API Key", type="password")
genai.configure(api_key=st.sidebar.text_input("Gemini API Key", type="password"))

client = OpenAI()

def make_video(base_video_path, script, subtitles, output_name):
    """실제 영상을 편집하고 자막/나레이션을 입히는 함수"""
    video = VideoFileClip(base_video_path)
    
    # 1. TTS 생성 (OpenAI 사용)
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy", # 인스타/유튜브별로 다르게 설정 가능
        input=script
    )
    response.stream_to_file("temp_audio.mp3")
    audio = AudioFileClip("temp_audio.mp3")
    
    # 2. 자막 합성 (MoviePy) - 간단한 버전
    # 실제 구현 시 타이밍 조절 로직이 추가되어야 함
    txt_clip = TextClip(subtitles[0], fontsize=50, color='white', font='Arial-Bold')
    txt_clip = txt_clip.set_pos('center').set_duration(video.duration)
    
    final_video = video.set_audio(audio)
    result = CompositeVideoClip([final_video, txt_clip])
    result.write_videofile(output_name, fps=24)
    return output_name

st.title("🚀 위드멤버 AI 영상 자동화 스튜디오")
st.write("촬영하신 영상을 업로드하면 플랫폼별 맞춤 영상을 생성합니다.")

uploaded_file = st.file_uploader("영상을 업로드하세요", type=['mp4', 'mov'])

if uploaded_file:
    with open("temp_input.mp4", "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.video("temp_input.mp4")

    if st.button("✨ 인스타/유튜브 패키지 동시 생성 시작"):
        with st.spinner("AI가 영상을 분석하고 기획 중입니다..."):
            # 1. Gemini 영상 분석
            model = genai.GenerativeModel('gemini-1.5-pro')
            video_part = genai.upload_file(path="temp_input.mp4")
            res = model.generate_content([SYSTEM_PROMPT, video_part])
            data = json.loads(res.text)

            # 2. 결과물 출력 (메타데이터)
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📸 인스타 공감형")
                st.write(f"**제목:** {data['ig']['title']}")
                st.write(f"**태그:** {data['ig']['tags']}")
                st.info(data['ig']['script'])
                # make_video 호출 및 다운로드 버튼 추가 가능
                
            with col2:
                st.subheader("📺 유튜브 정보성")
                st.write(f"**제목:** {data['yt']['title']}")
                st.write(f"**태그:** {data['yt']['tags']}")
                st.success(data['yt']['script'])

st.divider()
st.caption("© 2026 WithMember AI Studio. All rights reserved.")