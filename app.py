
import streamlit as st
from sarvamai import SarvamAI

st.set_page_config(
    page_title="Gujarati Mitra | English to Gujarati",
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
    padding-top: 2.5rem;
}
.hero {
    text-align: center;
    padding: 1rem 0 1.5rem;
}
.hero h1 {
    color: #273c75;
    font-size: 2.5rem;
}
.hero p {
    color: #65708a;
    font-size: 1.05rem;
}
.stButton > button {
    border-radius: 12px;
    min-height: 3rem;
    font-weight: 600;
}
</style>
<div class="hero">
    <h1>🌼 ગુજરાતી મિત્ર</h1>
    <p>Your simple English-to-Gujarati translator</p>
</div>
""", unsafe_allow_html=True)

st.markdown("### ✍️ Enter your English text")

english = st.text_area(
    "English",
    placeholder="For example: How are you today?",
    height=140,
    max_chars=1000,
    label_visibility="collapsed"
)

if "history" not in st.session_state:
    st.session_state.history = []

if st.button("🌐 Translate to Gujarati", type="primary",
              use_container_width=True):
    if not english.strip():
        st.warning("Please enter some English text.")
    else:
        try:
            with st.spinner("Translating with Sarvam AI..."):
                client = SarvamAI(
                    api_subscription_key=st.secrets["SARVAM_API_KEY"]
                )
                response = client.text.translate(
                    input=english.strip(),
                    source_language_code="en-IN",
                    target_language_code="gu-IN",
                    model="mayura:v1"
                )
                translated = response.translated_text

            st.session_state.translation = translated
            st.session_state.history.insert(
                0, (english.strip(), translated)
            )
            st.session_state.history = st.session_state.history[:5]

        except Exception:
            st.error(
                "Translation failed. Check the app's API secret "
                "and try again."
            )

if "translation" in st.session_state:
    st.markdown("### ગુજરાતી અનુવાદ")
    st.text_area(
        "Gujarati translation",
        value=st.session_state.translation,
        height=140,
        key="translation_display"
    )
    st.caption("Select the Gujarati text above to copy it.")

if st.session_state.history:
    with st.expander("🕘 Recent translations"):
        for en, gu in st.session_state.history:
            st.markdown(f"**English:** {en}")
            st.markdown(f"**ગુજરાતી:** {gu}")
            st.divider()

st.caption("Powered by Sarvam AI · Made with ❤️ for Gujarati")
