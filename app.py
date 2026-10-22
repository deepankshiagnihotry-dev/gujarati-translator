import base64
import hashlib
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
    <p>Multi-User Adaptive STEM Translation Studio</p>
</div>
""", unsafe_allow_html=True)

# --- Password Hashing Utility ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Database Setup & Migration (Prevents OperationalError) ---
def init_db():
    conn = sqlite3.connect("stem_memory.db")
    c = conn.cursor()
    
    # Base Table Creation
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS translation_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            english_text TEXT,
            gujarati_translation TEXT,
            source TEXT
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            english_text TEXT,
            gujarati_translation TEXT,
            engine TEXT
        )
    """)
    conn.commit()

    # --- Migration Checks for Old Database Files ---
    # 1. Migration for 'users' table (Fixes: table users has no column named email)
    c.execute("PRAGMA table_info(users)")
    user_columns = [col[1] for col in c.fetchall()]
    if "email" not in user_columns:
        if "username" in user_columns:
            try:
                c.execute("ALTER TABLE users RENAME COLUMN username TO email")
            except Exception:
                c.execute("ALTER TABLE users ADD COLUMN email TEXT")
        else:
            c.execute("ALTER TABLE users ADD COLUMN email TEXT")

    # 2. Migration for 'translation_memory'
    c.execute("PRAGMA table_info(translation_memory)")
    mem_columns = [col[1] for col in c.fetchall()]
    if "username" not in mem_columns:
        c.execute("ALTER TABLE translation_memory ADD COLUMN username TEXT DEFAULT 'default_user'")

    # 3. Migration for 'user_history'
    c.execute("PRAGMA table_info(user_history)")
    hist_columns = [col[1] for col in c.fetchall()]
    if "username" not in hist_columns:
        c.execute("ALTER TABLE user_history ADD COLUMN username TEXT DEFAULT 'default_user'")

    conn.commit()
    conn.close()

init_db()

# --- User Auth Helpers ---
def register_user(email, password):
    conn = sqlite3.connect("stem_memory.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email.strip().lower(), hash_password(password)))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def authenticate_user(email, password):
    conn = sqlite3.connect("stem_memory.db")
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE email = ?", (email.strip().lower(),))
    row = c.fetchone()
    conn.close()
    if row and row[0] == hash_password(password):
        return True
    return False

def reset_password(email, new_password):
    conn = sqlite3.connect("stem_memory.db")
    c = conn.cursor()
    c.execute("SELECT email FROM users WHERE email = ?", (email.strip().lower(),))
    row = c.fetchone()
    if row:
        c.execute("UPDATE users SET password = ? WHERE email = ?", (hash_password(new_password), email.strip().lower()))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

# --- Database Operations (Filtered by User) ---
def get_memory(username, text):
    conn = sqlite3.connect("stem_memory.db")
    c = conn.cursor()
    c.execute("SELECT gujarati_translation FROM translation_memory WHERE username = ? AND LOWER(english_text) = LOWER(?)", (username, text.strip()))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def save_memory(username, english, gujarati, source="Human Expert Correction"):
    conn = sqlite3.connect("stem_memory.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO translation_memory (username, english_text, gujarati_translation, source)
        VALUES (?, ?, ?, ?)
    """, (username, english.strip(), gujarati.strip(), source))
    conn.commit()
    conn.close()

def log_session(username, english, gujarati, engine):
    conn = sqlite3.connect("stem_memory.db")
    c = conn.cursor()
    c.execute("INSERT INTO user_history (username, english_text, gujarati_translation, engine) VALUES (?, ?, ?, ?)", (username, english, gujarati, engine))
    conn.commit()
    conn.close()

def get_recent_history(username, limit=10):
    conn = sqlite3.connect("stem_memory.db")
    c = conn.cursor()
    c.execute("SELECT id, english_text, gujarati_translation, engine, timestamp FROM user_history WHERE username = ? ORDER BY id DESC LIMIT ?", (username, limit))
    rows = c.fetchall()
    conn.close()
    return rows

# --- Session State Management ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "current_english" not in st.session_state:
    st.session_state.current_english = ""
if "current_gujarati" not in st.session_state:
    st.session_state.current_gujarati = ""
if "current_engine" not in st.session_state:
    st.session_state.current_engine = ""

# --- Authentication Screen ---
if not st.session_state.logged_in:
    st.markdown("### 🔐 User Login & Project Isolation")
    tab_login, tab_register, tab_reset = st.tabs(["🔑 Login", "📝 Register New Account", "🔄 Reset Password"])
    
    with tab_login:
        login_email = st.text_input("Email Address", key="login_email")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log In", type="primary", use_container_width=True):
            if authenticate_user(login_email, login_pass):
                st.session_state.logged_in = True
                st.session_state.username = login_email.strip().lower()
                st.success(f"Welcome back, {st.session_state.username}!")
                st.rerun()
            else:
                st.error("Invalid email or password.")
                
    with tab_register:
        reg_email = st.text_input("Email Address", key="reg_email")
        reg_pass = st.text_input("Choose Password", type="password", key="reg_pass")
        if st.button("Create Account", use_container_width=True):
            if reg_email.strip() and reg_pass.strip():
                if register_user(reg_email, reg_pass):
                    st.success("Account created successfully! Please switch to the Login tab.")
                else:
                    st.error("Account with this email already exists.")
            else:
                st.warning("Please enter both email and password.")

    with tab_reset:
        reset_email = st.text_input("Registered Email Address", key="reset_email")
        new_pass = st.text_input("New Password", type="password", key="new_pass")
        if st.button("Reset Password", use_container_width=True):
            if reset_email.strip() and new_pass.strip():
                if reset_password(reset_email, new_pass):
                    st.success("Password updated successfully! You can now log in.")
                else:
                    st.error("Email not found in our records.")
            else:
                st.warning("Please fill in all fields.")
    st.stop()

# --- Sidebar Configuration ---
st.sidebar.title(f"👤 User: {st.session_state.username}")
if st.sidebar.button("🚪 Log Out"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.current_english = ""
    st.session_state.current_gujarati = ""
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.title("⚙️ Engine & API Settings")
st.sidebar.info(
    "💡 **Multi-Engine Pipeline:**\n\n"
    "0. **Personal Adaptive Memory** (Your verified edits)\n"
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

# --- Translation & Speech Helpers ---
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
    headers = {"Content-Type": "application/json", "userID": user_id, "ulcaApiKey": api_key}
    payload = {
        "pipelineTasks": [{"taskType": "translation", "config": {"language": {"sourceLanguage": "en", "targetLanguage": "gu"}, "serviceId": "ai4bharat/indictrans-v2-all-gpu--tda"}}],
        "inputData": {"input": [{"source": text}]}
    }
    response = requests.post(url, headers=headers, json=payload, timeout=5)
    if response.status_code == 200:
        return response.json()["pipelineResponse"][0]["output"][0]["target"]
    raise Exception("Bhashini Error")

def translate_text(text):
    # 0. Check User's Personal Memory First
    cached = get_memory(st.session_state.username, text)
    if cached:
        return cached, "Personal Adaptive Memory"

    # 1. Try Bhashini
    u_id = bhashini_user_id.strip() or st.secrets.get("BHASHINI_USER_ID", "")
    a_key = bhashini_api_key.strip() or st.secrets.get("BHASHINI_API_KEY", "")
    p_id = bhashini_pipeline_id.strip() or st.secrets.get("BHASHINI_PIPELINE_ID", "")
    if u_id and a_key:
        try:
            return translate_bhashini(text, u_id, a_key, p_id), "Bhashini (MeitY)"
        except Exception:
            st.toast("Bhashini unavailable. Switching to Sarvam AI...", icon="⚠️")

    # 2. Try Sarvam AI
    client = get_sarvam_client()
    if client:
        try:
            res = client.text.translate(input=text, source_language_code="en-IN", target_language_code="gu-IN", model="mayura:v1")
            return res.translated_text, "Sarvam AI (Mayura)"
        except Exception:
            st.toast("Sarvam AI quota reached. Switching to free fallback...", icon="⚠️")

    # 3. Fallback: Google Translate
    try:
        return GoogleTranslator(src='en', dest='gu').translate(text), "Google Translate"
    except Exception:
        try:
            return MyMemoryTranslator(source='en-IN', target='gu-IN').translate(text), "MyMemory Engine"
        except Exception:
            return "Translation temporarily unavailable.", "Error"

def speak_gujarati(text):
    client = get_sarvam_client()
    if client:
        try:
            res = client.text_to_speech.convert(text=text, model="bulbul:v3", language_code="gu-IN", speaker="ritu")
            return base64.b64decode("".join(res.audios)), "audio/wav"
        except Exception:
            pass
    tts = gTTS(text=text, lang='gu')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp.getvalue(), "audio/mp3"

# --- Main Text Input Section ---
st.markdown("### ✍️ Type in English")
english_input = st.text_area("English text", value=st.session_state.current_english, placeholder="For example: Gravity pulls objects toward the Earth's center.", height=100)

if st.button("🌐 Translate typed text", type="primary", use_container_width=True):
    if english_input.strip():
        with st.spinner("Translating..."):
            gujarati_result, engine_used = translate_text(english_input.strip())
            st.session_state.current_english = english_input.strip()
            st.session_state.current_gujarati = gujarati_result
            st.session_state.current_engine = engine_used
            log_session(st.session_state.username, st.session_state.current_english, st.session_state.current_gujarati, engine_used)
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
                        st.session_state.current_english = english
                        st.session_state.current_gujarati = gujarati
                        st.session_state.current_engine = engine
                        log_session(st.session_state.username, english, gujarati, engine)
                        st.rerun()
                else:
                    st.warning("No speech recognized. Please try recording again.")
            except Exception:
                st.error("Sarvam STT failed. Check your API credits.")
        else:
            st.error("Sarvam API key required for speech recognition. Use text input for free fallback mode.")

# --- Interactive Output & Learning Section ---
if st.session_state.current_gujarati:
    st.markdown("---")
    st.markdown(f"### 📝 ગુજરાતી અનુવાદ *(Engine: {st.session_state.current_engine})*")
    
    edited_gujarati = st.text_area(
        "Edit & Improve Translation (Saved specifically to your account):",
        value=st.session_state.current_gujarati,
        height=120
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Improvement to My Memory", use_container_width=True):
            save_memory(st.session_state.username, st.session_state.current_english, edited_gujarati, "Human Expert Correction")
            log_session(st.session_state.username, st.session_state.current_english, edited_gujarati, "Human Correction")
            st.success("✅ Saved to your personal memory bank!")
    
    with col2:
        if st.button("🔊 Listen to Audio", use_container_width=True):
            with st.spinner("Generating audio..."):
                audio_bytes, audio_format = speak_gujarati(edited_gujarati)
                st.audio(audio_bytes, format=audio_format)

# --- Persistent History Section ---
st.markdown("---")
st.markdown("### 📜 Your Saved Projects & History")
history = get_recent_history(st.session_state.username)

if history:
    for row_id, eng, guj, eng_name, tstamp in history:
        with st.expander(f"🕒 {tstamp} | {eng[:40]}..."):
            st.markdown(f"**English:** {eng}")
            st.markdown(f"**Gujarati:** {guj}")
            st.caption(f"Source: {eng_name}")
            if st.button("Load back into editor", key=f"load_btn_{row_id}"):
                st.session_state.current_english = eng
                st.session_state.current_gujarati = guj
                st.session_state.current_engine = eng_name
                st.rerun()
else:
    st.info("No saved translation history for your account yet.")
