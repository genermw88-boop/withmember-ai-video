import streamlit as st
import google.generativeai as genai
import time
import json
import os
from prompts import SYSTEM_PROMPT

# 1. API 키 자동 로드 (Secrets 활용)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # OpenAI 키 등도 필요시 여기에 세팅
    st.sidebar.success("✅ 위드멤버 시스템 권한 인증 완료")
except:
    st.sidebar.error("❌ API 키를 Secrets에 등록해주세요!")

st.title("🚀 위드멤버 AI 영상 자동화 스튜디오")

# 2. 다중 업로드 가능하게 변경 (accept_multiple_files=True)
uploaded_files = st.file_uploader("촬영하신 영상을 모두 선택하세요", type=['mp4', 'mov'], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        st.write(f"🎞️ 파일 분석 중: {uploaded_file.name}")
        
        with open("temp_input.mp4", "wb") as f:
            f.write(uploaded_file.getbuffer())

        if st.button(f"✨ {uploaded_file.name} 패키지 생성 시작"):
            with st.spinner("AI가 영상을 요리 중입니다. 잠시만 기다려주세요..."):
                # [핵심] Gemini에 영상 업로드
                video_part = genai.upload_file(path="temp_input.mp4")
                
                # [핵심] 영상이 준비될 때까지 대기 (NotFound 에러 방지)
                while video_part.state.name == "PROCESSING":
                    time.sleep(2)
                    video_part = genai.get_file(video_part.name)
                
                if video_part.state.name == "FAILED":
                    st.error("영상 분석에 실패했습니다.")
                    continue

                # 분석 시작
                model = genai.GenerativeModel('gemini-1.5-pro')
                res = model.generate_content([SYSTEM_PROMPT, video_part])
                
                # 결과 출력 (JSON 파싱)
                try:
                    data = json.loads(res.text.replace('```json', '').replace('```', ''))
                    st.success(f"✅ {uploaded_file.name} 분석 완료!")
                    # (여기에 결과 화면 구성 코드 넣기)
                except:
                    st.write(res.text) # JSON 형식이 아닐 경우 대비
