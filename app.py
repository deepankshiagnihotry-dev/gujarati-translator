
import base64
import streamlit as st
from sarvamai import SarvamAI

st.set_page_config(
    page_title="Gujarati Mitra",
    page_icon="🌼",
    layout="centered"
)

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
    <p>Your English-to-Gujarati voice translator</p>
</div>
""", unsafe_allow_html=True)


def get_client():
    return SarvamAI(
        api_subscription_key=st.secrets["SARVAM_API_KEY"]
    )


def translate_text(text):
    client = get_client()
    response = client.text.translate(
        input=text,
        source_language_code="en-IN",
        target_language_code="gu-IN",
        model="mayura:v1"
    )
    return response.translated_text


def speak_gujarati(text):
    client = get_client()
    response = client.text_to_speech.convert(
        text=text,
        model="bulbul:v3",
        language_code="gu-IN",
        speaker="ritu"
    )
    return base64.b64decode("".join(response.audios))


def save_translation(english, gujarati):
    st.session_state.translation = gujarati
    st.session_state.english_text = english
    st.session_state.history.insert(
        0, (english, gujarati)
    )
    st.session_state.history = st.session_state.history[:5]


if "history" not in st.session_state:
    st.session_state.history = []

if "english_text" not in st.session_state:
    st.session_state.english_text = ""

if "translation" not in st.session_state:
    st.session_state.translation = ""

st.markdown("### ✍️ Type or 🎙️ speak in English")

typed_text = st.text_area(
    "English text",
    placeholder="For example: How are you today?",
    height=120,
    max_chars=1000
)

if st.button("🌐 Translate typed text", type="primary",
             use_container_width=True):
    if not typed_text.strip():
        st.warning("Please enter some English text.")
    else:
        try:
            with st.spinner("Translating with Sarvam AI..."):
                result = translate_text(typed_text.strip())
            save_translation(typed_text.strip(), result)
            st.rerun()
        except Exception:
            st.error(
                "Translation failed. Check your API key, "
                "Sarvam account limits, and try again."
            )

st.markdown("---")
st.markdown("### 🎙️ Speak English")

st.caption(
    "Tap the microphone, allow browser access if asked, "
    "speak your sentence, and stop recording."
)

recording = st.audio_input("Record English speech")

if recording is not None:
    st.audio(recording)

    if st.button("🎧 Transcribe and translate",
                  use_container_width=True):
        try:
            with st.spinner("Recognizing your speech..."):
                client = get_client()
                transcript = client.speech_to_text.transcribe(
                    file=recording,
                    model="saaras:v3",
                    language_code="en-IN"
                )
                english = transcript.transcript.strip()

            if not english:
                st.warning("No speech was recognized. Please try again.")
            else:
                with st.spinner("Translating into Gujarati..."):
                    gujarati = translate_text(english)

                save_translation(english, gujarati)
                st.rerun()

        except Exception:
            st.error(
                "Voice translation failed. Try a clear, short recording. "
                "Check your API key and Sarvam account limits."
            )

if st.session_state.translation:
    st.markdown("---")
    st.markdown("### 📝 English")
    st.write(st.session_state.english_text)

    st.markdown("### ગુજરાતી અનુવાદ")
    st.text_area(
        "Gujarati translation",
        value=st.session_state.translation,
        height=130,
        key="gujarati_result"
    )

    if st.button("🔊 Listen to Gujarati",
                 use_container_width=True):
        try:
            with st.spinner("Creating Gujarati speech..."):
                audio_bytes = speak_gujarati(
                    st.session_state.translation
                )
            st.audio(audio_bytes, format="audio/wav")
        except Exception:
            st.error(
                "Voice generation failed. Check your API key "
                "and Sarvam account limits."
            )

if st.session_state.history:
    st.markdown("---")
    with st.expander("🕘 Recent translations"):
        for english, gujarati in st.session_state.history:
            st.markdown(f"**English:** {english}")
            st.markdown(f"**ગુજરાતી:** {gujarati}")
            st.divider()

st.caption("Powered by Sarvam AI · Made with ❤️ for Gujarati")
