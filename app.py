import base64
import io
import streamlit as st
from sarvamai import SarvamAI
from deep_translator import GoogleTranslator, MyMemoryTranslator
from gtts import gTTS

st.set_page_config(
    page_title="Gujarati Mitra",
    page_icon="🌼",
    layout="centered"
)

# Custom UI Styling
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
    <p>Your English-to-Gujarati voice & text translator for STEM TLMs</p>
</div>
""", unsafe_allow_html=True)

# Sidebar Configuration with Clear Instructions
st.sidebar.title("⚙️ API Settings")
st.sidebar.info(
    "💡 **How this works:**\n\n"
    "This app uses Sarvam AI as its primary engine for Gujarati translation and speech.\n\n"
    "If you have a Sarvam API key, enter it below. If left blank or if credits expire, "
    "the app automatically switches to free open-source fallbacks!"
)

custom_key = st.sidebar.text_input(
    "Enter Sarvam API Key (Optional):",
    type="password",
    help="Leave blank to use default secrets or free backup engines."
)

def get_sarvam_client():
    """Fetches the Sarvam client using sidebar key or default Streamlit secrets."""
    key = custom_key.strip() if custom_key.strip() else st.secrets.get("SARVAM_API_KEY", "")
    if key:
        try:
            return SarvamAI(api_subscription_key=key)
        except Exception:
            return None
    return None

def translate_text(text):
    """
    Primary: Sarvam AI (Mayura:v1)
    Fallback 1: Google Translate
    Fallback 2: MyMemory (if Google hits rate limits)
    """
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
            st.toast("Sarvam AI quota reached or invalid key. Switching to free open-source fallback.", icon="⚠️")
    
    # Fallback 1: Google Translate
    try:
        translated = GoogleTranslator(src='en', dest='gu').translate(text)
        return translated, "Free Fallback (Google)"
    except Exception:
        # Fallback 2: MyMemory Translator
        try:
            translated = MyMemoryTranslator(source='en-IN', target='gu-IN').translate(text)
            return translated, "Free Fallback (MyMemory)"
        except Exception:
            return "Translation temporarily busy. Please try again in a few moments.", "Error"

def speak_gujarati(text):
    """Attempts Sarvam AI TTS first, falls back to free gTTS."""
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
            st.toast("Sarvam TTS quota reached. Switching to gTTS audio.", icon="⚠️")
    
    # Fallback: Free gTTS
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
        with st.spinner("Translating into Gujarati..."):
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
                st.error("Sarvam STT failed. Check your API credits or enter a valid API key in the sidebar.")
        else:
            st.error("A valid Sarvam API key is required for voice-to-text input. Use text input for free fallback mode.")

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

st.caption("Powered by Sarvam AI · Made with ❤️ for Gujarati STEM Education")
