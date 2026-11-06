"""TRtek Akıllı Servis Masası: Streamlit kullanıcı arayüzü."""

from html import escape
import os
from pathlib import Path
import time
from uuid import uuid4
from urllib.parse import urlsplit

import streamlit as st
import streamlit.components.v1 as components
from email_validator import EmailNotValidError, validate_email

import ui_client
from conversation import history_from_messages
from email_domains import registered_tlds, validate_email_tld

st.set_page_config(page_title="TRtek | Destek Asistanı", page_icon="◈", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
:root { color-scheme: dark; }
.stApp { background: radial-gradient(ellipse at 5% 0%, #152733 0, #101820 36%, #0b1117 82%); color: #e9f0f3; }
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
[data-testid="stSidebar"] { background: rgba(12, 19, 25, .93); border-right: 1px solid #27353e; }
[data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }
.block-container { max-width: 1120px; padding-top: 2.1rem; padding-bottom: 2rem; }
h1, h2, h3 { font-family: 'Manrope', sans-serif !important; letter-spacing: -.035em; }
.eyebrow { color:#75dbc6; font-size:.76rem; font-weight:700; letter-spacing:.13em; text-transform:uppercase; }
.muted { color:#8da0aa; font-size:.94rem; }
.brand { color:#edf5f6; font-family:'Manrope',sans-serif; font-weight:800; font-size:1.15rem; letter-spacing:-.04em; }
.brand-mark { display:inline-flex; width:2.2rem; height:2.2rem; align-items:center; justify-content:center; margin-right:.6rem; border-radius:11px; color:#0b1819; background:#75dbc6; font-weight:800; }
.panel { padding:1.4rem 1.5rem; border:1px solid #293942; border-radius:16px; background:rgba(19,29,36,.82); }
.tiny-label { color:#89a0aa; font-size:.78rem; text-transform:uppercase; letter-spacing:.1em; }
.stButton > button, .stFormSubmitButton > button { min-height:2.8rem; border:1px solid #4ccbb2; border-radius:9px; background:#62d4ba; color:#09201d; font-weight:700; }
.stButton > button:hover, .stFormSubmitButton > button:hover { border-color:#8ce8d4; background:#82e2ce; color:#09201d; }
.stTextInput input, .stTextArea textarea { background:#101a20; border-color:#344650; border-radius:9px; }
.stTextInput input:focus, .stTextArea textarea:focus { border-color:#62d4ba; box-shadow:0 0 0 1px #62d4ba; }
div[data-testid="stChatMessage"] { border:1px solid #263740; border-radius:14px; background:rgba(19,29,36,.72); padding:.7rem 1rem; }
.auth-intro { max-width: 500px; padding: 2.5rem .5rem; }
.auth-heading { font-family:'Manrope',sans-serif; font-size:clamp(2.4rem,4.2vw,4.3rem); font-weight:800; line-height:1.06; letter-spacing:-.06em; }
.auth-card { padding: 1.15rem 1.35rem; border:1px solid #2a3b44; border-radius:18px; background:rgba(17,27,34,.94); box-shadow:0 26px 100px rgba(0,0,0,.22); }
.auth-card [data-testid="stTextInput"] { margin-bottom:.25rem; }
.auth-footnote { color:#82939b; font-size:.84rem; padding-top:.35rem; }
div[data-testid="stPopover"] button { border-radius:8px; }
[data-testid="stChatInput"] textarea { background:#121c22; }
footer { visibility:hidden; }
/* Remove Streamlit chrome on every screen, retaining the sidebar control. */
[data-testid="stHeader"] {
  background:transparent;
  height:0;
  pointer-events:none;
}
[data-testid="stToolbar"],
[data-testid="stAppDeployButton"],
[data-testid="stDecoration"],
[data-testid="stMainMenu"],
#MainMenu { display:none!important; }
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stExpandSidebarButton"] { pointer-events:auto; }
html { scroll-behavior:smooth; }
.stButton > button, .stFormSubmitButton > button, [data-testid="stPopover"] button,
[data-testid="stChatInput"], .stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div {
  transition:background-color .2s ease, border-color .2s ease, color .2s ease, box-shadow .2s ease;
}
[data-testid="stSidebar"] { transition:width .25s ease, transform .25s ease; }
[data-testid="stExpander"] summary { transition:background-color .2s ease; }
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior:auto; }
  *, *::before, *::after { animation:none!important; transition:none!important; }
}
@media (max-width: 760px) {
  .block-container { padding-top:1rem; padding-left:1rem; padding-right:1rem; }
  [data-testid="stHorizontalBlock"] { flex-direction:column; gap:1rem; }
  [data-testid="stHorizontalBlock"] [data-testid="stColumn"] { width:100%!important; flex:1 1 100%!important; }
  .auth-intro { padding:.1rem 0 .8rem; }
  .auth-heading { font-size:2.1rem; }
  .auth-card { padding:.8rem 1rem; }
}
@media (min-width: 761px) and (max-height: 820px) {
  .block-container { padding-top:.8rem; }
  .auth-intro { padding:1rem .3rem; }
  .auth-heading { font-size:clamp(2.3rem,3.5vw,3.6rem); }
  .auth-card { padding:.8rem 1.2rem; }
  [data-testid="stForm"] { gap:.3rem; }
  .stTextInput { margin-bottom:0; }
}
@media (min-width: 761px) and (min-height: 821px) {
  .block-container { padding-top:min(6vh,4rem); }
}
</style>
""", unsafe_allow_html=True)

API_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
MODES = {"Servis Masası": "service_desk", "Windows Server": "windows_server", "Oracle DB": "oracle_db"}


def clear_session() -> None:
    # Token, kullanıcı bilgisi ve konuşma dahil mevcut kullanıcı durumunu temizle.
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def sign_out() -> None:
    clear_session()
    st.rerun()


def handle_api_error(error: ui_client.ApiError) -> None:
    if error.status == 401:
        clear_session()
        st.rerun()
    if error.status == 503:
        st.error("Hizmet şu anda hazır değil. Bağlantı ayarlarını kontrol edip yeniden deneyebilirsin.")
    else:
        st.error(str(error))


def registration_errors(email: str, password: str, confirmation: str) -> list[str]:
    errors = []
    try:
        validate_email(email.strip(), check_deliverability=False, allow_smtputf8=False)
    except EmailNotValidError:
        errors.append("Geçerli bir e-posta adresi gir; örnek: ad@firma.com.")

    try:
        validate_email_tld(email)
    except ValueError as error:
        if str(error) not in errors:
            errors.append(str(error))

    domain = email.strip().rsplit("@", 1)[-1].lower()
    if domain in {"gmail.co", "gmai.com", "gmial.com", "gmail.con", "hotmail.con", "outlook.con"}:
        errors.append("E-posta alan adında yazım hatası olabilir. Adresi kontrol edip düzelt.")

    if not 8 <= len(password) <= 1024:
        errors.append("Parola 8-1024 karakter uzunluğunda olmalı.")
    if not any(character.isupper() for character in password):
        errors.append("Parolada en az bir büyük harf bulunmalı.")
    if not any(character.islower() for character in password):
        errors.append("Parolada en az bir küçük harf bulunmalı.")
    if not any(character in "0123456789" for character in password):
        errors.append("Parolada en az bir rakam bulunmalı.")
    if password != confirmation:
        errors.append("Parolalar eşleşmiyor.")
    return errors


# Local component validates on input without Streamlit's blur-triggered reruns.
_auth_form = components.declare_component(
    "trtek_auth", path=str(Path(__file__).parent / "auth_frontend")
)


def render_auth() -> None:
    # The fixed Streamlit toolbar overlaps our compact authentication layout.
    # Apply this only here so the chat sidebar toggle remains available.
    st.markdown("""
    <style>
    [data-testid="stHeader"] { display:none; }
    </style>
    """, unsafe_allow_html=True)
    intro, auth = st.columns([1.05, 0.95], gap="large", vertical_alignment="center")
    with intro:
        st.markdown('<div class="brand"><span class="brand-mark">T</span>TRtek</div>', unsafe_allow_html=True)
        st.markdown("<br><div class='eyebrow'>Yapay zekâ destek mühendisi</div>", unsafe_allow_html=True)
        st.markdown('<div class="auth-heading">Teknik desteğin yeni yolu.</div>', unsafe_allow_html=True)
        st.markdown('<p class="muted">Servis masası, Windows Server ve Oracle DB sorularına kaynaklara dayalı yanıtlar.</p>', unsafe_allow_html=True)
    with auth:
        epoch = st.session_state.get("auth_epoch", 0)
        event = _auth_form(
            tlds=sorted(registered_tlds()), epoch=epoch, response_id=st.session_state.get("auth_handled_event"), email=st.session_state.get("auth_email", ""),
            error=st.session_state.get("auth_error", ""),
            notice=st.session_state.get("auth_notice", ""),
            key=f"auth_form_{epoch}", default=None,
        )
        if not isinstance(event, dict) or not isinstance(event.get("id"), str):
            return
        if event["id"] == st.session_state.get("auth_handled_event"):
            return
        st.session_state.auth_handled_event = event["id"]
        mode = event.get("mode")
        email, password = event.get("email"), event.get("password")
        if mode not in {"login", "register"} or not isinstance(email, str) or not isinstance(password, str):
            return
        try:
            if mode == "register":
                confirmation = event.get("confirmation", "")
                if not isinstance(confirmation, str):
                    return
                problems = registration_errors(email, password, confirmation)
                if problems:
                    st.session_state.auth_error = " ".join(problems)
                else:
                    ui_client.register(API_URL, email, password)
                    st.session_state.auth_epoch = epoch + 1
                    st.session_state.auth_email = email
                    st.session_state.auth_error = ""
                    st.session_state.auth_notice = "Hesabın oluşturuldu. Şimdi giriş yapabilirsin."
            else:
                result = ui_client.login(API_URL, email, password)
                clear_session()
                st.session_state.token = result["access_token"]
                st.session_state.user = result["user"]
                st.session_state.messages = []
                st.session_state.expertise = "service_desk"
                st.session_state.token_expires_at = time.time() + result["expires_in"]
        except ui_client.ApiError as error:
            st.session_state.auth_notice = ""
            st.session_state.auth_error = "E-posta veya parola hatalı." if error.status == 401 else str(error)
            if error.status == 401:
                st.session_state.auth_epoch = epoch + 1
                st.session_state.auth_email = email
        st.rerun()

def safe_source_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme in {"https", "http"} and parsed.hostname and not parsed.username else None
    except ValueError:
        return None


def render_sources(sources: object) -> None:
    if not isinstance(sources, list) or not sources:
        return
    with st.expander(f"Kaynaklar · {len(sources)}"):
        for index, source in enumerate(sources, 1):
            if not isinstance(source, dict):
                continue
            name = source.get("source_name") or "Bilgi tabanı"
            title = source.get("title") or f"Kaynak {index}"
            st.markdown(f"**{index}. {escape(str(name))}** · {escape(str(title))}")
            address = safe_source_url(source.get("answer_url") or source.get("source_url"))
            if address:
                st.markdown(f"[Kaynağı aç]({address})")


def send_chat_request(request: dict) -> None:
    """Send a new question or its retry without appending the user message twice."""
    if request.get("running"):
        return
    request["running"] = True
    request["error"] = None
    request["message"]["status"] = "pending"
    try:
        result = ui_client.ask(
            API_URL, st.session_state.token, request["question"], request["mode"],
            history=request["history"], request_id=request["id"],
        )
        messages = st.session_state.get("mode_messages", {}).get(request["mode"])
        if messages is not request["messages"]:
            return  # A reset or logout discarded this conversation while waiting.
        request["message"]["status"] = "complete"
        messages.append({"role": "assistant", "content": result.get("answer") or "Bu istek için yanıt alınamadı.",
                         "sources": result.get("sources", []),
                         "insufficient_context": result.get("insufficient_context", False),
                         "elapsed_ms": result.get("elapsed_ms")})
        pending = st.session_state.get("pending_requests", {})
        if pending.get(request["mode"]) is request:
            pending.pop(request["mode"], None)
    except ui_client.ApiError as error:
        request["message"]["status"] = "failed"
        if error.status == 401:
            handle_api_error(error)
        request["error"] = str(error)
        request["retryable"] = error.status is None or error.status in {409, 429, 500, 502, 503, 504}
    finally:
        request["running"] = False


def render_chat() -> None:
    user = st.session_state.user
    with st.sidebar:
        st.markdown('<div class="brand"><span class="brand-mark">T</span>TRtek</div>', unsafe_allow_html=True)
        st.markdown("<br><div class='tiny-label'>Uzmanlık alanı</div>", unsafe_allow_html=True)
        if "expertise_selector" not in st.session_state:
            current_mode = st.session_state.get("expertise", "service_desk")
            st.session_state.expertise_selector = next(name for name, mode in MODES.items() if mode == current_mode)
        selected = st.selectbox("Uzmanlık modu", list(MODES), label_visibility="collapsed",
                                key="expertise_selector")
        selected_mode = MODES[selected]
        mode_messages = st.session_state.setdefault("mode_messages", {})
        previous_mode = st.session_state.get("expertise", "service_desk")
        mode_messages[previous_mode] = st.session_state.messages
        st.session_state.expertise = selected_mode
        st.session_state.messages = mode_messages.setdefault(selected_mode, [])
        st.caption("Her uzmanlık alanının sohbeti bu oturumda ayrı tutulur.")
        if st.button("Yeni sohbet", use_container_width=True):
            st.session_state.get("pending_requests", {}).pop(selected_mode, None)
            st.session_state.messages = []
            mode_messages[selected_mode] = st.session_state.messages
            st.rerun()
        st.divider()
        st.markdown("**Oturum**")
        st.caption(str(user.get("email", "")))
        st.caption("Sohbet geçmişi bu oturum süresince saklanır.")
        if st.button("Çıkış yap", use_container_width=True):
            sign_out()
        st.markdown(f"<br><span class='muted'>API · {escape(API_URL)}</span>", unsafe_allow_html=True)

    st.markdown('<div class="eyebrow">TRTEK · TEKNİK DESTEK</div>', unsafe_allow_html=True)
    st.title("Merhaba, nasıl yardımcı olabilirim?")
    st.markdown('<p class="muted">Sorunu anlat. Yanıtlar, kullanılabilir bilgi tabanındaki kaynaklarla birlikte gösterilir.</p>', unsafe_allow_html=True)
    st.info("Bu sohbet yalnızca mevcut oturumda tutulur. Sayfayı yenilediğinde veya çıkış yaptığında geçmiş silinebilir.", icon="ℹ️")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                render_sources(message.get("sources"))
                if message.get("insufficient_context"):
                    st.caption("Bu aramada soruyla doğrudan eşleşen yeterli bir kaynak bulunamadı.")
                if message.get("elapsed_ms") is not None:
                    st.caption(f"Yanıt süresi · {message['elapsed_ms'] / 1000:.1f} sn")

    st.caption("Takip soruları için son 3 tamamlanmış soru–yanıt çifti, uzunluk sınırı içinde kullanılır. Yeni bir konu için Yeni sohbet'e basabilirsin.")
    pending_by_mode = st.session_state.setdefault("pending_requests", {})
    pending = pending_by_mode.get(st.session_state.expertise)
    if pending and pending.get("error"):
        with st.chat_message("assistant"):
            st.error(pending["error"])
            if pending.get("retryable", False):
                if st.button("Tekrar dene", key=f"retry_{pending['id']}", disabled=pending.get("running", False)) and not pending.get("running"):
                    with st.spinner("Aynı soru yeniden deneniyor…"):
                        send_chat_request(pending)
                    st.rerun()
            else:
                st.caption("Sorunu düzeltip yeni bir mesaj gönderebilirsin.")

    if question := st.chat_input("Teknik sorununu yaz…", max_chars=2000, disabled=bool(pending and pending.get("running"))):
        history = history_from_messages(st.session_state.messages)
        user_message = {"role": "user", "content": question, "status": "pending"}
        st.session_state.messages.append(user_message)
        request = {"id": str(uuid4()), "question": question, "history": history,
                   "mode": st.session_state.expertise, "message": user_message,
                   "messages": st.session_state.messages, "running": False}
        pending_by_mode[request["mode"]] = request
        with st.spinner("Kaynaklar inceleniyor, yanıt hazırlanıyor…"):
            send_chat_request(request)
        st.rerun()


def main() -> None:
    token = st.session_state.get("token")
    if token:
        try:
            user = ui_client.current_user(API_URL, token)
            st.session_state.user = user
        except ui_client.ApiError as error:
            if error.status == 401:
                clear_session()
            elif (error.status is None or error.status in {500, 502, 503, 504}) and st.session_state.get("user"):
                expires_at = st.session_state.get("token_expires_at")
                if expires_at is not None and expires_at <= time.time():
                    clear_session()
                else:
                    st.warning("Hizmete şu anda ulaşılamıyor. Sohbetin korunuyor; bağlantı düzeldiğinde tekrar deneyebilirsin.")
            else:
                st.error(str(error))
                st.stop()
    if st.session_state.get("token"):
        render_chat()
    else:
        render_auth()


main()
