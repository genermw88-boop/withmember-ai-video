import streamlit as st
import google.generativeai as genai
import time
import json
import os
import requests
import gc 

# ==========================================
# 🔥 자막 에러(ANTIALIAS) 영구 해결 백신
import PIL
from PIL import Image
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'Resampling', Image).LANCZOS
# ==========================================

from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
import moviepy.video.fx.all as vfx

st.set_page_config(page_title="위드멤버 개별 맞춤 영상 스튜디오", layout="wide")

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    ELEVENLABS_API_KEY = st.secrets.get("ELEVENLABS_API_KEY", "")
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    st.sidebar.error("❌ Secrets에 API 키를 등록해주세요!")

# ==========================================
# 💡 코드를 고칠 필요 없이, 화면에서 성우 ID를 입력받습니다!
st.sidebar.header("⚙️ 스튜디오 설정")
user_voice_id = st.sidebar.text_input("🎙️ 성우 Voice ID를 붙여넣으세요", "")
st.sidebar.caption("일레븐랩스에서 복사한 영문+숫자 아이디를 입력하세요.")
st.sidebar.divider()
# ==========================================

def get_system_prompt(store, menu, point):
    store_text = store if store else "해당 매장"
    menu_text = menu if menu else "주요 상품"
    point_text = f"강조할 내용: {point}" if point else "특징을 잘 살려서 설명"
    return f"""
당신은 대한민국 1타 숏폼 마케터입니다. 영상을 보고 **무조건 15초 분량(약 60자)**의 대본을 쓰세요.
[🎯 핵심 정보] 상호명: {store_text} / 주력 메뉴: {menu_text} / {point_text}
반드시 아래 JSON 형식으로만 답변하세요:
{{
  "ig": {{"script": "15초 대본", "title": "제목", "tags": "#태그", "comment": "댓글"}},
  "yt": {{"script": "15초 대본", "title": "제목", "tags": "#태그", "comment": "댓글"}}
}}
"""

def generate_audio(text, output_path, voice_id):
    if not ELEVENLABS_API_KEY:
        st.error("🔑 일레븐랩스 API 키가 없습니다.")
        return False
        
    if not voice_id:
        st.error("👈 왼쪽 설정창에 일레븐랩스 성우 ID를 입력해주세요!")
        return False
        
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY}
    data = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.8}}
    
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        return True
    else:
        st.error(f"❌ 일레븐랩스 에러: {response.text}")
        return False

def create_final_video(video_path, audio_path, script_text, output_path):
    try:
        vid = VideoFileClip(video_path)
        if vid.w > 720:
            vid = vid.resize(width=720)
            
        aud = AudioFileClip(audio_path)
        
        if vid.duration < aud.duration:
            vid = vid.fx(vfx.loop, duration=aud.duration)
        else:
            vid = vid.subclip(0, aud.duration)
            
        font_path = "font.ttf" if os.path.exists("font.ttf") else "Arial"
        
        txt_clip = TextClip(
            script_text, 
            font=font_path, 
            fontsize=35, 
            color='white', 
            bg_color='rgba(0,0,0,0.5)', 
            method='caption',
            size=(vid.w * 0.9, None)
        )
        txt_clip = txt_clip.set_position(('center', 'bottom')).set_duration(aud.duration).margin(bottom=30, opacity=0)
        
        final_vid = CompositeVideoClip([vid, txt_clip])
        final_vid = final_vid.set_audio(aud)
        
        final_vid.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", threads=1, logger=None)
        
        vid.close()
        aud.close()
        final_vid.close()
        gc.collect() 
        return True
    except Exception as e:
        st.error(f"❌ 합성 에러: {str(e)}")
        return False

st.title("🚀 위드멤버 개별 맞춤 영상 스튜디오")

uploaded_files = st.file_uploader("영상을 여러 개 업로드하세요 (최대 10개)", type=['mp4', 'mov'], accept_multiple_files=True)

if uploaded_files:
    st.divider()
    st.subheader("📝 영상별 세부 기획 입력")
    
    user_inputs = {}
    for file in uploaded_files:
        with st.expander(f"📌 '{file.name}' 지시사항", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                s_name = st.text_input("상호명", key=f"name_{file.name}")
                s_menu = st.text_input("주력 메뉴", key=f"menu_{file.name}")
            with col2:
                s_point = st.text_area("강조할 포인트", key=f"point_{file.name}")
            user_inputs[file.name] = {"store": s_name, "menu": s_menu, "point": s_point}
            
    st.divider()

    if st.button(f"🎬 총 {len(uploaded_files)}개 영상 일괄 제작 시작"):
        progress_bar = st.progress(0)
        status_area = st.empty()
        
        for idx, file in enumerate(uploaded_files):
            file_name = file.name
            base_name = file_name.split('.')[0]
            status_area.info(f"⏳ ({idx+1}/{len(uploaded_files)}) '{file_name}' 작업 중...")
            
            raw_video_path = f"raw_{file_name}"
            with open(raw_video_path, "wb") as f:
                f.write(file.getbuffer())
            
            try:
                video_part = genai.upload_file(path=raw_video_path)
                while video_part.state.name == "PROCESSING":
                    time.sleep(3)
                    video_part = genai.get_file(video_part.name)
                
                my_input = user_inputs[file_name]
                final_prompt = get_system_prompt(my_input["store"], my_input["menu"], my_input["point"])
                
                model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
                response = model.generate_content([final_prompt, video_part])
                res_data = json.loads(response.text.replace('```json', '').replace('```', '').strip())
                
                for platform, key in [("인스타", "ig"), ("유튜브", "yt")]:
                    with st.expander(f"✨ [{platform}] 완성본: {file_name}", expanded=True):
                        st.write(f"**📝 {res_data[key]['title']}**")
                        st.info(res_data[key]['script'])
                        
                        audio_path = f"audio_{key}_{base_name}.mp3"
                        final_video_path = f"final_{key}_{base_name}.mp4"
                        
                        with st.spinner(f"[{platform}] 자막 및 목소리 렌더링 중..."):
                            # 🔥 이제 사용자가 화면에 입력한 아이디를 가져다 씁니다!
                            if generate_audio(res_data[key]['script'], audio_path, user_voice_id):
                                if create_final_video(raw_video_path, audio_path, res_data[key]['script'], final_video_path):
                                    if os.path.exists(final_video_path):
                                        st.video(final_video_path)
                                        with open(final_video_path, "rb") as v_file:
                                            st.download_button("⬇️ 완성본 다운로드", v_file, file_name=final_video_path, mime="video/mp4")
                                
            except Exception as e:
                st.error(f"❌ '{file_name}' 에러: {str(e)}")
            
            progress_bar.progress((idx + 1) / len(uploaded_files))
            
        status_area.success("✅ 모든 맞춤형 영상 제작이 완료되었습니다!")
