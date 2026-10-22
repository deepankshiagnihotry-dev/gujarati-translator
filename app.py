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

# --- Database Setup (Multi-User Isolated Memory) ---
def init_db():
    conn = sqlite3.connect("stem_memory.db")
    c = conn.cursor()
    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    """)
    # Per-user adaptive translation memory
    c.execute("""
        CREATE TABLE IF NOT EXISTS translation_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            english_text TEXT,
            gujarati_translation TEXT,
            source TEXT,
            UNIQUE(username, english_text)
        )
    """)
    # Per-user project history
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
    conn.close()

init_db()

# --- User Auth Helpers ---
def register_user(username, password):
    conn = sqlite3.connect("stem_memory.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username.strip().lower(), hash_password(password)))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def authenticate_user(username, password):
    conn = sqlite3.connect("stem_memory.db")
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username.strip().lower(),))
    row = c.fetchone()
    conn.close()
    if row and row[0] == hash_password(password):
        return True
    return False

# --- Database Operations (Filtered by Username) ---
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
        ON CONFLICT(username, english_text) DO UPDATE SET gujarati_translation=excluded.gujarati_translation, source=excluded.source
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
    tab_login, tab_register = st.tabs(["🔑 Login", "📝 Register New Account"])
    
    with tab_login:
        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log In", type="primary", use_container_width=True):
            if authenticate_user(login_user, login_pass):
                st.session_state.logged_in = True
                st.session_state.username = login_user.strip().lower()
                st.success(f"Welcome back, {st.session_state.username}!")
                st.rerun()
            else:
                st.error("Invalid username or password.")
                
    with tab_register:
        reg_user = st.text_input("Choose Username", key="reg_user")
        reg_pass = st.text_input("Choose Password", type="password", key="reg_pass")
        if st.button("Create Account", use_container_width=True):
            if reg_user.strip() and reg_pass.strip():
                if register_user(reg_user, reg_pass):
                    st.success("Account created successfully! Please switch to the Login tab.")
                else:
                    st.error("Username already exists. Please choose another.")
            else:
                st.warning("Please enter both username and password.")
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
custom_sarvam_key = st.sidebar.text_input("Sarvam API Key (Optional):", type="password")

with st.sidebar.expander("🏛️ Bhashini API Configuration (Optional)"):
    bhashini_user_id = st.text_input("Bhashini User ID", type="password")
    bhashini_api_key = st.text_input("Bhashini API Key", type="password")
    bhashini_pipeline_id = st.text_input("Pipeline ID", value="64392e20e3204922a8627883")

# --- Translation Logic ---
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
    # 0. Check User's Isolated Memory
    cached = get_memory(st.session_state.username, text)
    if cached:
