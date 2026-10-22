import base64
import io
import requests
import streamlit as st
from sarvamai import SarvamAI
from deep_translator import GoogleTranslator, MyMemoryTranslator
from gtts import gTTS

st.set_page_config(
    page_title="Gujarati Mitra",
    page_icon="🌼",
    layout="centered"
)

# Custom Styling
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #f5f7ff 0%, #ffffff 65%);
}
.block-container {
    max-width: 760px;
    padding-top: 2rem;
}
.hero {
    text-align: center;
    padding: 1rem 0;
}
.hero h1 {
    color: #273c75;
    font-size: 2.5rem;
}
.stButton > button {
    border-radius: 12px;
    min-height: 3rem;
    font-weight: 600;
}
</style>
<div class="hero">
    <h1>🌼 ગુજરાતી મિત્ર</h1>
    <p>Multi-Engine English-to-Gujarati Voice & Text Tool for STEM TLMs</p>
</div>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.title("⚙️ Engine & API Settings")
st.sidebar.info(
    "💡 **Resilient Multi-Engine Pipeline:**\n\n"
    "1. **Bhashini (MeitY)** (if configured)\n"
    "2. **Sarvam AI** (if key provided)\n"
    "3. **Free Open-Source Fallback** (Google / MyMemory)\n\n"
    "If primary quotas expire, the app automatically switches to backup engines!"
)

custom_sarvam_key = st.sidebar.text_input(
    "Sarvam API Key (Optional):",
    type="password",
    help="Enter key or leave blank for automatic fallback."
)

with st.sidebar.expander("🏛️ Bhashini API Configuration (Optional)"):
    bhashini_user_id = st.text_input("Bhashini User ID", type="password")
    bhashini_api_key = st.text_input("Bhashini API Key", type="password")
    bhashini_pipeline_id = st.text_input("Pipeline ID", value="64392e20e3204922a8627883")

def get_sarvam_client():
    key = custom_sarvam_key.strip() if custom_sarvam_key.strip() else st.secrets.get("SARVAM_API_KEY", "")
    if key:
        try:
            return SarvamAI(api_subscription_key=key)
        except Exception:
            return None
    return None

def translate_bhashini(text, user_id, api_key, pipeline_id):
    """Translates text using Bhashini's ULCA API pipeline."""
    url = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
    headers = {
        "Content-Type": "application/json",
        "userID": user_id,
        "ulcaApiKey": api_key
    }
    payload = {
        "pipelineTasks": [
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": "en",
                        "targetLanguage": "gu"
                    },
                    "serviceId": "ai4bharat/indictrans-v2-all-gpu--tda"
                }
            }
        ],
        "inputData": {
            "input": [{"source": text}]
        }
    }
    response = requests.post(url, headers=headers, json=payload, timeout=5)
    if response.status_code == 200:
        data = response.json()
        return data["pipelineResponse"][0]["output"][0]["target"]
    raise Exception(f"Bhashini API Error: {response.status_code}")

def translate_text(text):
    """
    Priority 1: Bhashini API (if credentials entered)
    Priority 2: Sarvam AI (Mayura:v1)
    Priority 3: Google Translate
    Priority 4: MyMemory (Rate-limit backup)
    """
    # 1. Try Bhashini
    u_id = bhashini_user_id.strip() or st.secrets.get("BHASHINI_USER_ID", "")
    a_key = bhashini_api_key.strip() or st.secrets.get("BHASHINI_API_KEY", "")
    p_id = bhashini_pipeline_id.strip() or st.secrets.get("BHASHINI_PIPELINE_ID", "")

    if u_id and a_key:
        try:
            translated = translate_bhashini(text, u_id, a_key, p_id)
            return translated, "Bhashini (MeitY)"
        except Exception:
            st.toast("Bhashini quota/credentials issue. Switching to Sarvam AI...", icon="⚠️")

    # 2. Try Sarvam AI
    client = get_sarvam_client()
    if client:
        try:
            response = client.text.translate(
                input=text,
                source_language_code="en-IN",
                target_language_code="gu-IN",
                model="mayura:v1"
            )
            return response.translated_text, "Sarvam AI (Mayura)"
        except Exception:
            st.toast("Sarvam AI quota reached. Switching to free fallback...", icon="⚠️")

    # 3. Fallback: Google Translate
    try:
        translated = GoogleTranslator(src='en', dest='gu').translate(text)
        return translated, "Free Fallback (Google)"
    except Exception:
        # 4. Fallback: MyMemory
        try:
            translated = MyMemoryTranslator(source='en-IN', target='gu-IN').translate(text)
            return translated, "Free Fallback (MyMemory)"
        except Exception:
            return "Translation temporarily unavailable. Please try again later.", "Error"

def speak_gujarati(text):
    """Attempts Sarvam AI TTS first, falls back to gTTS."""
    client = get_sarvam_client()
    if client:
        try:
            response = client.text_to_speech.convert(
                text=text,
                model="bulbul:v3",
                language_code="gu-IN",
                speaker="ritu"
            )
            return base64.b64decode("".join(response.audios)), "audio/wav"
        except Exception:
            st.toast("Sarvam TTS quota reached. Switching to gTTS.", icon="⚠️")

    # Free Fallback: gTTS
    tts = gTTS(text=text, lang='gu')
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)
    return audio_fp.getvalue(), "audio/mp3"

def save_translation(english, gujarati, engine):
    st.session_state.translation = gujarati
    st.session_state.english_text = english
    st.session_state.engine_used = engine
    st.session_state.history.insert(0, (english, gujarati, engine))
    st.session_state.history = st.session_state.history[:5]

# Initialize Session State
if "history" not in st.session_state:
    st.session_state.history = []
if "english_text" not in st.session_state:
    st.session_state.english_text = ""
if "translation" not in st.session_state:
    st.session_state.translation = ""
if "engine_used" not in st.session_state:
    st.session_state.engine_used = ""

# --- Text Input Section ---
st.markdown("### ✍️ Type in English")

typed_text = st.text_area(
    "English text",
    placeholder="For example: Gravity pulls objects toward the Earth's center.",
    height=120,
    max_chars=1000
)

if st.button("🌐 Translate typed text", type="primary", use_container_width=True):
    if not typed_text.strip():
        st.warning("Please enter some English text.")
    else:
        with st.spinner("Translating..."):
            result, engine = translate_text(typed_text.strip())
            save_translation(typed_text.strip(), result, engine)
            st.rerun()

st.markdown("---")

# --- Speech Input Section ---
st.markdown("### 🎙️ Speak English")
st.caption("Tap the microphone, speak your STEM sentence, and stop recording.")

recording = st.audio_input("Record English speech")

if recording is not None:
    st.audio(recording)
    if st.button("🎧 Transcribe and translate", use_container_width=True):
        client = get_sarvam_client()
        if client:
            try:
                with st.spinner("Recognizing speech via Sarvam Saaras..."):
                    transcript = client.speech_to_text.transcribe(
                        file=recording,
                        model="saaras:v3",
                        language_code="en-IN"
                    )
                    english = transcript.transcript.strip()

                if english:
                    with st.spinner("Translating..."):
                        gujarati, engine = translate_text(english)
                        save_translation(english, gujarati, engine)
                        st.rerun()
                else:
                    st.warning("No speech recognized. Please try recording again.")
            except Exception:
                st.error("Sarvam STT failed. Check your API credits.")
        else:
            st.error("Sarvam API key required for speech recognition. Use text input for free fallback mode.")

# --- Output Section ---
if st.session_state.translation:
    st.markdown("---")
    st.markdown("### 📝 English")
    st.write(st.session_state.english_text)

    st.markdown(f"### ગુજરાતી અનુવાદ *(Engine: {st.session_state.engine_used})*")
    st.text_area(
        "Gujarati translation",
        value=st.session_state.translation,
        height=130,
        key="gujarati_result"
    )

    if st.button("🔊 Listen to Gujarati", use_container_width=True):
        with st.spinner("Generating Gujarati speech..."):
            audio_bytes, audio_format = speak_gujarati(st.session_state.translation)
            st.audio(audio_bytes, format=audio_format)

# --- History Section ---
if st.session_state.history:
    st.markdown("---")
    with st.expander("Recent translations"):
        for english, gujarati, engine in st.session_state.history:
            st.markdown(f"**English:** {english}")
            st.markdown(f"**ગુજરાતી:** {gujarati} *(via {engine})*")
            st.divider()

st.caption("Multi-Engine Indic Architecture · Built for Gujarati STEM Education")
