import streamlit as st
import google.generativeai as genai
import time
import json
import os
from prompts import SYSTEM_PROMPT

# 1. API 키 자동 로드 (보안 및 편의성)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    st.sidebar.success("✅ 위드멤버 시스템 권한 인증 완료")
except:
    st.sidebar.error("❌ Streamlit Secrets에 GEMINI_API_KEY를 등록해주세요!")

st.set_page_config(page_title="위드멤버 AI 영상 센터", layout="wide")
st.title("🚀 위드멤버 AI 영상 일괄 처리 스튜디오")
st.write("최대 10개의 영상을 한 번에 업로드하고 패키지를 생성하세요.")

# 2. 다중 파일 업로드 (최대 10개)
uploaded_files = st.file_uploader(
    "촬영하신 영상을 선택하세요 (최대 10개)", 
    type=['mp4', 'mov'], 
    accept_multiple_files=True
)

# 결과 저장을 위한 세션 상태 초기화
if 'all_results' not in st.session_state:
    st.session_state.all_results = {}

if uploaded_files:
    if len(uploaded_files) > 10:
        st.warning("⚠️ 한 번에 최대 10개까지만 업로드 가능합니다. 앞의 10개만 처리합니다.")
        uploaded_files = uploaded_files[:10]

    # [일괄 처리 시작 버튼]
    if st.button("🔥 모든 영상 일괄 처리 시작"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, uploaded_file in enumerate(uploaded_files):
            file_name = uploaded_file.name
            status_text.text(f"⏳ ({idx+1}/{len(uploaded_files)}) {file_name} 처리 중...")
            
            # 파일 임시 저장
            temp_path = f"temp_{file_name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            try:
                # [핵심] Gemini 업로드 및 상태 확인 루프 (NotFound 에러 방지)
                video_part = genai.upload_file(path=temp_path)
                while video_part.state.name == "PROCESSING":
                    time.sleep(3) # 3초 대기
                    video_part = genai.get_file(video_part.name)
                
                if video_part.state.name == "FAILED":
                    st.error(f"❌ {file_name} 분석 실패")
                    continue

                # AI 분석 실행
                model = genai.GenerativeModel('gemini-1.5-flash')
                res = model.generate_content([SYSTEM_PROMPT, video_part])
                
                # JSON 파싱 및 저장
                clean_res = res.text.replace('```json', '').replace('```', '').strip()
                st.session_state.all_results[file_name] = json.loads(clean_res)
                
            except Exception as e:
                st.error(f"❌ {file_name} 처리 중 오류: {str(e)}")
            
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path) # 임시 파일 삭제
            
            # 프로그레스 바 업데이트
            progress_bar.progress((idx + 1) / len(uploaded_files))
        
        status_text.text("✅ 모든 영상 처리가 완료되었습니다!")
        st.balloons()

# 3. 결과물 화면 출력 (탭 형식으로 깔끔하게)
if st.session_state.all_results:
    st.divider()
    st.header("📂 생성된 마케팅 패키지 리스트")
    
    for file_name, result in st.session_state.all_results.items():
        with st.expander(f"🎬 {file_name} 결과 보기", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📸 인스타 공감형")
                st.write(f"**제목:** {result['ig']['title']}")
                st.info(f"**대본:**\n{result['ig']['script']}")
                st.code(f"태그: {result['ig']['tags']}\n댓글: {result['ig']['comment']}", language="text")
            with col2:
                st.subheader("📺 유튜브 정보성")
                st.write(f"**제목:** {result['yt']['title']}")
                st.success(f"**대본:**\n{result['yt']['script']}")
                st.code(f"태그: {result['yt']['tags']}\n댓글: {result['yt']['comment']}", language="text")

