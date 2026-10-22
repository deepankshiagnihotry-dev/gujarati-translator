import base64
import io
import sqlite3
import requests
import streamlit as st
from sarvamai import SarvamAI
from deep_translator import GoogleTranslator, MyMemoryTranslator
from gtts import gTTS

st.set_page_config(
    page_title="Gujarati Mitra - Adaptive Translation Studio",
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
    <p>Self-Learning Multi-Engine STEM Translation Studio</p>
</div>
""", unsafe_allow_html=True)

# --- Database Setup (Persistent Memory & Progress) ---
def init_db():
    conn = sqlite3.connect("stem_memory.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS translation_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            english_text TEXT UNIQUE,
            gujarati_translation TEXT,
            source TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            english_text TEXT,
            gujarati_translation TEXT,
            engine TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_memory(text):
    """Checks if a human-verified or corrected translation already exists."""
    conn = sqlite3.connect("stem_memory.db")
    c = conn.cursor()
    c.execute("SELECT gujarati_translation FROM translation_memory WHERE LOWER(english_text) = LOWER(?)", (text.strip(),))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def save_memory(english, gujarati, source="Human Expert Correction"):
    """Saves user-corrected translation to persistent memory so the system learns."""
    conn = sqlite3.connect("stem_memory.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO translation_memory (english_text, gujarati_translation, source)
        VALUES (?, ?, ?)
        ON CONFLICT(english_text) DO UPDATE SET gujarati_translation=excluded.gujarati_translation, source=excluded.source
    """, (english.strip(), gujarati.strip(), source))
    conn.commit()
    conn.close()

def log_session(english, gujarati, engine):
    """Logs translation activity so users can resume work later."""
    conn = sqlite3.connect("stem_memory.db")
    c = conn.cursor()
    c.execute("INSERT INTO user_history (english_text, gujarati_translation, engine) VALUES (?, ?, ?)", (english, gujarati, engine))
    conn.commit()
    conn.close()

def get_recent_history(limit=10):
    conn = sqlite3.connect("stem_memory.db")
    c = conn.cursor()
    c.execute("SELECT english_text, gujarati_translation, engine, timestamp FROM user_history ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# --- Sidebar Configuration ---
st.sidebar.title("⚙️ Engine & API Settings")
st.sidebar.info(
    "💡 **Multi-Engine Strategy:**\n\n"
    "0. **Adaptive Memory** (Self-learning verified corrections)\n"
    "1. **Bhashini (MeitY)** (if configured)\n"
    "2. **Sarvam AI** (if key provided)\n"
    "3. **Free Open-Source Fallback** (Google / MyMemory)"
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
    # 0. Check Adaptive Self-Learning Memory First
    cached = get_memory(text)
    if cached:
        return cached, "Adaptive Memory (Verified Correction)"

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
        return translated, "Google Translate"
    except Exception:
        # 4. Fallback: MyMemory
        try:
            translated = MyMemoryTranslator(source='en-IN', target='gu-IN').translate(text)
            return translated, "MyMemory Engine"
        except Exception:
            return "Translation temporarily unavailable.", "Error"

def speak_gujarati(text):
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
            pass

    # Free Fallback: gTTS
    tts = gTTS(text=text, lang='gu')
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)
    return audio_fp.getvalue(), "audio/mp3"

# --- Main Workspace UI ---
if "current_english" not in st.session_state:
    st.session_state.current_english = ""
if "current_gujarati" not in st.session_state:
    st.session_state.current_gujarati = ""
if "current_engine" not in st.session_state:
    st.session_state.current_engine = ""

st.markdown("### ✍️ Translate & Refine STEM Content")
english_input = st.text_area("English Source Sentence:", value=st.session_state.current_english, height=100)

if st.button("🌐 Translate", type="primary", use_container_width=True):
    if english_input.strip():
        with st.spinner("Translating..."):
            gujarati_result, engine_used = translate_text(english_input.strip())
            st.session_state.current_english = english_input.strip()
            st.session_state.current_gujarati = gujarati_result
            st.session_state.current_engine = engine_used
            log_session(st.session_state.current_english, st.session_state.current_gujarati, engine_used)
            st.rerun()

# --- Interactive Edit & Learning Section ---
if st.session_state.current_gujarati:
    st.markdown("---")
    st.markdown(f"### 📝 ગુજરાતી અનુવાદ *(Engine: {st.session_state.current_engine})*")
    
    edited_gujarati = st.text_area(
        "Edit & Improve Translation (Changes will be permanently learned by the app):",
        value=st.session_state.current_gujarati,
        height=120
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Improvement to Memory", use_container_width=True):
            save_memory(st.session_state.current_english, edited_gujarati, "Human Expert Correction")
            log_session(st.session_state.current_english, edited_gujarati, "Human Correction")
            st.success("✅ Saved! Next time anyone enters this exact sentence, your improved translation will load instantly.")
    
    with col2:
        if st.button("🔊 Listen to Audio", use_container_width=True):
            with st.spinner("Generating audio..."):
                audio_bytes, audio_format = speak_gujarati(edited_gujarati)
                st.audio(audio_bytes, format=audio_format)

# --- Persistent Progress Section ---
st.markdown("---")
st.markdown("### 📜 Continue Where You Left Off")
history = get_recent_history()

if history:
    for eng, guj, eng_name, tstamp in history:
        with st.expander(f"🕒 {tstamp} | {eng[:40]}..."):
            st.markdown(f"**English:** {eng}")
            st.markdown(f"**Gujarati:** {guj}")
            st.caption(f"Source: {eng_name}")
            if st.button("Load back into editor", key=f"load_{eng[:15]}"):
                st.session_state.current_english = eng
                st.session_state.current_gujarati = guj
                st.session_state.current_engine = eng_name
                st.rerun()
else:
    st.info("No saved translation history found yet. Start typing above!")
