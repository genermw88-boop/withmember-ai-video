import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="위드멤버 API 진단기")
st.title("🔍 위드멤버 구글 API 키 진단기")

try:
    # Secrets에서 키를 가져옵니다.
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    st.success("✅ API 키 연결 성공! 구글 서버에서 사용 가능한 모델을 불러옵니다...")
    
    # 사용 가능한 모델 목록을 가져와서 출력합니다.
    st.write("### 📌 현재 API 키로 사용 가능한 모델 목록:")
    
    models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            models.append(m.name)
            
    if models:
        for model_name in models:
            st.code(model_name)
    else:
        st.error("사용 가능한 generateContent 모델이 없습니다.")

except Exception as e:
    st.error(f"❌ 에러 발생: {str(e)}")
