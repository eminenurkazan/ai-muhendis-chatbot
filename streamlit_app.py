"""TRtek Akıllı Servis Masası: Streamlit kullanıcı arayüzü."""

from html import escape
import json
import os
from pathlib import Path
import time
from uuid import uuid4
from urllib.parse import urlsplit

import streamlit as st
import streamlit.components.v1 as components
from email_validator import EmailNotValidError, validate_email

import kb_limits
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
/* Compact saved conversation buttons */
[data-testid="stSidebar"] [class*="st-key-saved_chat_"] button {
  display:flex; justify-content:flex-start; width:100%; min-width:0;
  height:2.4rem; min-height:2.4rem; padding:.35rem .65rem;
  background:transparent; border:1px solid transparent; border-radius:8px;
  color:#d7e2e7; font-weight:400; text-align:left; overflow:hidden;
}
[data-testid="stSidebar"] [class*="st-key-saved_chat_"] button:hover {
  background:#1c2b33; border-color:transparent; color:#edf5f6;
}
[data-testid="stSidebar"] [class*="st-key-saved_chat_"] button > div,
[data-testid="stSidebar"] [class*="st-key-saved_chat_"] [data-testid="stMarkdownContainer"] {
  min-width:0; width:100%; overflow:hidden;
}
[data-testid="stSidebar"] [class*="st-key-saved_chat_"] button p {
  display:block; margin:0; white-space:nowrap; overflow:hidden;
  text-overflow:ellipsis; text-align:left; font-size:.9rem; line-height:1.5;
}
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
  overflow:visible;
  pointer-events:none;
}
[data-testid="stExpandSidebarButton"] { position:fixed; top:.6rem; left:.6rem; z-index:999991; }
/* stToolbar also holds the "open sidebar" button, so hide only its action items. */
[data-testid="stToolbarActions"],
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
            if source.get("record_type") == "documentation":
                st.caption(f"{source.get('source_author', '')} · {source.get('license', '')} · Kaynaktan uyarlanmıştır; ortamda çalıştırılarak test edilmemiştir.")
                license_address = safe_source_url(source.get("license_url"))
                if license_address:
                    st.markdown(f"[Lisans]({license_address})")


@st.dialog("Yanıtı değerlendir")
def feedback_dialog(message: dict) -> None:
    st.write("Bu yanıt sana ne kadar yardımcı oldu?")
    st.caption("1: Hiç yardımcı olmadı · 5: Çok yardımcı oldu")
    request_id = message["request_id"]
    current_rating = message.get("feedback_rating")
    with st.form(f"feedback_form_{request_id}"):
        rating = st.radio("Puanın", [1, 2, 3, 4, 5],
                          index=current_rating - 1 if current_rating else None, horizontal=True,
                          key=f"feedback_rating_{request_id}")
        comment = st.text_area("Yorumun (isteğe bağlı)", value=message.get("feedback_comment") or "",
                               max_chars=2000, key=f"feedback_comment_{request_id}")
        submitted = st.form_submit_button("Değerlendirmeyi kaydet", use_container_width=True)
    if submitted:
        if rating is None:
            st.warning("Lütfen 1 ile 5 arasında bir puan seç.")
            return
        try:
            result = ui_client.save_feedback(API_URL, st.session_state.token, message["chat_id"],
                                              request_id, rating, comment)
        except ui_client.ApiError as error:
            if error.status == 401:
                handle_api_error(error)
            else:
                st.error("Değerlendirme kaydedilemedi. Puanın ve yorumun burada korunuyor; tekrar deneyebilirsin.")
            return
        message["feedback_rating"] = result["rating"]
        message["feedback_comment"] = result.get("comment")
        st.session_state.feedback_notice = "Değerlendirmen kaydedildi, teşekkürler."
        st.rerun()


def render_feedback_prompt(message: dict) -> None:
    if not message.get("chat_id") or not message.get("request_id"):
        return
    request_id = message["request_id"]
    if message.get("feedback_rating"):
        st.caption(f"Değerlendirmen · {message['feedback_rating']}/5")
        if st.button("Değerlendirmeyi düzenle", key=f"feedback_edit_{request_id}"):
            feedback_dialog(message)
        return
    if message.get("feedback_dismissed"):
        return
    # A UI invitation only: never append it to saved messages or model context.
    with st.chat_message("assistant"):
        st.write("Bu yanıtı değerlendirmek ister misiniz?")
        yes, no = st.columns(2)
        if yes.button("Değerlendir", key=f"feedback_yes_{request_id}", use_container_width=True):
            feedback_dialog(message)
        if no.button("Şimdi değil", key=f"feedback_no_{request_id}", use_container_width=True):
            message["feedback_dismissed"] = True
            st.rerun()


def send_chat_request(request: dict) -> None:
    """Send a new question or its retry without appending the user message twice."""
    if request.get("running"):
        return
    request["running"] = True
    request["error"] = None
    request["message"]["status"] = "pending"
    try:
        if not request.get("chat_id"):
            chat = ui_client.create_chat(API_URL, st.session_state.token,
                                         request["question"], request["mode"])
            request["chat_id"] = chat["id"]
            st.session_state.setdefault("mode_chat_ids", {})[request["mode"]] = chat["id"]
        result = ui_client.ask_saved(API_URL, st.session_state.token, request["chat_id"],
                                     request["question"], request["id"])
        st.session_state.pop("saved_chats", None)
        messages = st.session_state.get("mode_messages", {}).get(request["mode"])
        if messages is not request["messages"]:
            return  # A reset or logout discarded this conversation while waiting.
        request["message"]["status"] = "complete"
        messages.append({"role": "assistant", "content": result.get("answer") or "Bu istek için yanıt alınamadı.",
                         "chat_id": request["chat_id"], "request_id": request["id"],
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
    # Apply navigation before the expertise selectbox is instantiated.
    if selected_chat := st.session_state.pop("open_saved_chat", None):
        try:
            with st.spinner("Kayıtlı sohbet açılıyor…"):
                rows = ui_client.load_messages(API_URL, st.session_state.token, selected_chat["id"])
            mode = selected_chat["expertise_mode"]
            messages = [{"role": row["role"], "content": row["content"],
                         "chat_id": selected_chat["id"], "request_id": row.get("request_id"),
                         "feedback_rating": row.get("feedback_rating"),
                         "feedback_comment": row.get("feedback_comment"),
                         "status": "complete" if row["message_status"] == "completed" else "failed",
                         "sources": row.get("sources", [])} for row in rows]
            st.session_state.setdefault("mode_messages", {})[mode] = messages
            st.session_state.setdefault("mode_chat_ids", {})[mode] = selected_chat["id"]
            st.session_state.get("pending_requests", {}).pop(mode, None)
            st.session_state.messages = messages
            st.session_state.expertise = mode
            st.session_state.expertise_selector = next(name for name, value in MODES.items() if value == mode)
        except ui_client.ApiError as error:
            handle_api_error(error)
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
        st.caption("Her uzmanlık alanında ayrı bir sohbet sürdürebilirsin.")
        if st.button("Yeni sohbet", use_container_width=True):
            st.session_state.get("pending_requests", {}).pop(selected_mode, None)
            st.session_state.messages = []
            mode_messages[selected_mode] = st.session_state.messages
            st.session_state.setdefault("mode_chat_ids", {}).pop(selected_mode, None)
            st.rerun()
        st.divider()
        st.markdown("**Kayıtlı sohbetler**")
        if st.button("Sohbet listesini yenile", use_container_width=True):
            st.session_state.pop("saved_chats", None)
        if "saved_chats" not in st.session_state:
            try:
                page = ui_client.list_chats(API_URL, st.session_state.token)
                st.session_state.saved_chats = page["items"]
                st.session_state.chats_next_offset = page.get("next_offset")
            except ui_client.ApiError as error:
                if error.status == 401:
                    handle_api_error(error)
                st.caption("Kayıtlı sohbetler şu anda yüklenemedi. Listeyi yenileyebilirsin.")
        for chat in st.session_state.get("saved_chats", []):
            label = " ".join((chat.get("title") or "Yeni sohbet").split())
            mode_name = next((name for name, mode in MODES.items() if mode == chat["expertise_mode"]), "")
            if st.button(label, key=f"saved_chat_{chat['id']}", help=f"{label} · {mode_name}",
                         use_container_width=True):
                st.session_state.open_saved_chat = chat
                st.rerun()
        if st.session_state.get("chats_next_offset") is not None:
            if st.button("Daha eski sohbetler", use_container_width=True):
                try:
                    page = ui_client.list_chats(API_URL, st.session_state.token,
                                                st.session_state.chats_next_offset)
                    known = {chat["id"] for chat in st.session_state.saved_chats}
                    st.session_state.saved_chats.extend(chat for chat in page["items"] if chat["id"] not in known)
                    st.session_state.chats_next_offset = page.get("next_offset")
                    st.rerun()
                except ui_client.ApiError as error:
                    handle_api_error(error)
        st.divider()
        if user.get("role") == "admin":
            if st.button("Yönetim paneli", use_container_width=True):
                st.session_state.view = "admin"
                st.rerun()
        st.markdown("**Oturum**")
        st.caption(str(user.get("email", "")))
        st.caption("Tamamlanan soru ve yanıtlar hesabına kaydedilir.")
        if st.button("Çıkış yap", use_container_width=True):
            sign_out()
        st.markdown(f"<br><span class='muted'>API · {escape(API_URL)}</span>", unsafe_allow_html=True)

    st.markdown('<div class="eyebrow">TRTEK · TEKNİK DESTEK</div>', unsafe_allow_html=True)
    st.title("Merhaba, nasıl yardımcı olabilirim?")
    st.markdown('<p class="muted">Sorunu anlat. Yanıtlar, kullanılabilir bilgi tabanındaki kaynaklarla birlikte gösterilir.</p>', unsafe_allow_html=True)
    st.caption("Eski konuşmalarına soldaki Kayıtlı sohbetler bölümünden ulaşabilirsin.")
    if not st.session_state.messages and st.session_state.get("mode_chat_ids", {}).get(st.session_state.expertise):
        st.info("Bu sohbet açıldı, ancak henüz kaydedilmiş mesajı yok. Önceki istek tamamlanmadıysa soru ve yanıt geçmişe eklenmez. Sorunu aşağıdan yeniden gönderebilirsin.")
    if notice := st.session_state.pop("feedback_notice", None):
        st.toast(notice)

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                render_sources(message.get("sources"))
                if message.get("insufficient_context"):
                    st.caption("Bu aramada soruyla doğrudan eşleşen yeterli bir kaynak bulunamadı.")
                if message.get("elapsed_ms") is not None:
                    st.caption(f"Yanıt süresi · {message['elapsed_ms'] / 1000:.1f} sn")
        if message["role"] == "assistant":
            render_feedback_prompt(message)

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
                   "chat_id": st.session_state.get("mode_chat_ids", {}).get(st.session_state.expertise),
                   "messages": st.session_state.messages, "running": False}
        pending_by_mode[request["mode"]] = request
        with st.spinner("Kaynaklar inceleniyor, yanıt hazırlanıyor…"):
            send_chat_request(request)
        st.rerun()


def _percent(value) -> str:
    return "—" if value is None else f"%{value:.1f}".replace(".", ",")


def render_admin() -> None:
    """Admin reporting panel; the API enforces the admin role, the UI only hides the entry."""
    with st.sidebar:
        st.markdown('<div class="brand"><span class="brand-mark">T</span>TRtek</div>', unsafe_allow_html=True)
        if st.button("Sohbete dön", use_container_width=True):
            st.session_state.view = "chat"
            st.rerun()
        st.caption(str(st.session_state.user.get("email", "")))
        if st.button("Çıkış yap", use_container_width=True):
            sign_out()
    st.markdown('<div class="eyebrow">TRTEK · YÖNETİM</div>', unsafe_allow_html=True)
    st.title("Yönetim paneli")
    section = st.radio("Bölüm", ["Raporlar", "Bilgi Merkezi", "Günlükler"], horizontal=True, key="admin_section",
                       label_visibility="collapsed")
    if section == "Bilgi Merkezi":
        render_knowledge_center()
    elif section == "Günlükler":
        render_logs()
    else:
        render_admin_report()


def render_admin_report() -> None:
    st.subheader("Raporlama")
    days = st.selectbox("Dönem", [7, 30, 90, 365], index=1, format_func=lambda d: f"Son {d} gün")
    try:
        with st.spinner("Rapor hazırlanıyor…"):
            report = ui_client.admin_report(API_URL, st.session_state.token, days)
    except ui_client.ApiError as error:
        if error.status == 403:
            st.session_state.view = "chat"
        handle_api_error(error)
        return
    first = st.columns(4)
    first[0].metric("Soru", report["questions"])
    first[1].metric("Sohbet", report["chats"])
    first[2].metric("Aktif kullanıcı / toplam", f"{report['users_active']} / {report['users_total']}")
    latency = report["avg_latency_ms"]
    first[3].metric("Ort. yanıt süresi", "—" if latency is None else f"{latency / 1000:.1f} sn")
    second = st.columns(4)
    second[0].metric("Memnuniyet (4–5 puan)", _percent(report["satisfaction_rate"]),
                     help="Puanlanan yanıtlar içinde 4 veya 5 alanların oranı.")
    second[1].metric("Ort. puan", "—" if report["avg_rating"] is None else str(report["avg_rating"]).replace(".", ","))
    second[2].metric("Kaynaklı yanıt oranı", _percent(report["source_answer_rate"]),
                     help="Yeterli kaynak bulunan yanıtların oranı.")
    second[3].metric("Puanlanan yanıt", f"{report['rated_total']} / {report['answers']}")
    st.caption("Chatbot başarısı iki ölçüyle izlenir: kullanıcı memnuniyeti ve kaynak bulunabilirliği. "
               "İkisi de yanıtın teknik doğruluğunun bağımsız kanıtı değildir; puanlanan yanıt sayısı azsa dikkatli yorumla.")
    left, right = st.columns(2)
    with left:
        st.subheader("En çok sorulan sorular")
        if report["top_questions"]:
            st.dataframe([{"Soru": row["question"], "Sayı": row["asked"], "Puanlanan": row["rated"],
                           "Ort. puan": row["avg_rating"]} for row in report["top_questions"]],
                         hide_index=True, use_container_width=True)
            st.caption("Aynı metinli sorular (büyük/küçük harf ve baştaki/sondaki boşluk ayrımı yok) birlikte sayılır.")
        else:
            st.info("Bu dönemde soru yok.")
    with right:
        st.subheader("Puan dağılımı")
        st.bar_chart({str(star): count for star, count in sorted(report["rating_distribution"].items())})
    left, right = st.columns(2)
    with left:
        st.subheader("Uzmanlık alanına göre sorular")
        names = {value: name for name, value in MODES.items()}
        if report["by_mode"]:
            st.bar_chart({names.get(row["expertise_mode"], row["expertise_mode"]): row["questions"]
                          for row in report["by_mode"]})
    with right:
        st.subheader("Günlük soru sayısı")
        if report["daily"]:
            st.bar_chart({row["day"]: row["questions"] for row in report["daily"]})


LEVEL_LABELS = {"error": "Hata", "warning": "Uyarı", "info": "Bilgi", "debug": "Ayıklama"}


def _log_time(value: str) -> str:
    from datetime import datetime
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d.%m.%Y %H:%M:%S") + " UTC"
    except ValueError:
        return value


def render_logs() -> None:
    """Uygulama günlükleri (yalnız yönetici). Parola, token ve soru metni günlüğe yazılmaz."""
    token = st.session_state.token
    days = st.selectbox("Dönem", [1, 7, 30, 90], index=1, format_func=lambda d: f"Son {d} gün", key="log_days")
    try:
        summary = ui_client.log_summary(API_URL, token, days)
    except ui_client.ApiError as error:
        if error.status == 403:
            st.session_state.view = "chat"
        handle_api_error(error)
        return
    columns = st.columns(3)
    for column, level in zip(columns, ("error", "warning", "info")):
        column.metric(LEVEL_LABELS[level], summary["levels"].get(level, 0))
    first = st.columns(3)
    level_name = first[0].selectbox("Düzey", ["Hepsi", *LEVEL_LABELS.values()], key="log_level")
    event_names = ["Hepsi", *[e["event_type"] for e in summary["events"]]]
    event = first[1].selectbox("Olay", event_names, key="log_event")
    query = first[2].text_input("Ara (olay, e-posta veya istek kimliği)", max_chars=100, key="log_query")
    filters = {"days": days, "query": query.strip() or None,
               "level": next((k for k, v in LEVEL_LABELS.items() if v == level_name), None),
               "event_type": None if event == "Hepsi" else event}
    if st.session_state.get("log_filters") != filters:
        st.session_state.log_filters, st.session_state.log_offset = filters, 0
    offset = st.session_state.get("log_offset", 0)
    if st.button("Yenile", key="log_refresh"):
        st.rerun()
    try:
        page = ui_client.logs(API_URL, token, offset=offset, **filters)
    except ui_client.ApiError as error:
        handle_api_error(error)
        return
    items = page["items"]
    if not items:
        st.info("Bu süzgeçle günlük kaydı yok.")
    else:
        st.dataframe([{"Zaman": _log_time(i["created_at"]), "Düzey": LEVEL_LABELS.get(i["level"], i["level"]),
                       "Olay": i["event_type"], "Kullanıcı": i["user_email"] or "—",
                       "İstek": i["correlation_id"][:8],
                       "Ayrıntı": json.dumps(i["details"], ensure_ascii=False)[:120] if i["details"] else ""}
                      for i in items], hide_index=True, use_container_width=True)
        chosen = st.selectbox("Ayrıntı görüntüle", range(len(items)), key="log_pick",
                              format_func=lambda n: f"{_log_time(items[n]['created_at'])} · {items[n]['event_type']}")
        entry = items[chosen]
        st.caption(f"İstek kimliği: {entry['correlation_id']} — aynı isteğin olaylarını görmek için bu kimliği Ara kutusuna yapıştır.")
        st.json(entry["details"] if entry["details"] is not None else {})
    nav = st.columns(2)
    if nav[0].button("Önceki sayfa", disabled=offset == 0, key="log_prev"):
        st.session_state.log_offset = max(0, offset - 50)
        st.rerun()
    if nav[1].button("Sonraki sayfa", disabled=page["next_offset"] is None, key="log_next"):
        st.session_state.log_offset = page["next_offset"]
        st.rerun()


STATUS_LABELS = {"pending": "Onay bekliyor", "approved": "Aktif", "excluded": "Devre dışı"}
DOMAIN_LABELS = {"general_it": "Genel BT", "windows_server": "Windows Server", "oracle_db": "Oracle DB"}
TYPE_LABELS = {"ticket": "Ticket", "qa": "Soru–cevap", "documentation": "Rehber"}
KB_MAX_BYTES = kb_limits.MAX_UPLOAD_CHARS


def _kb_payload(kind: str, domain: str, license_note: str, uploaded) -> dict | None:
    """Yüklenen dosyayı güvenli biçimde metne çevirir; dosya içeriği burada hiçbir zaman yorumlanmaz."""
    if uploaded is None:
        return None
    raw = uploaded.getvalue()
    if len(raw) > KB_MAX_BYTES:
        st.error(f"Dosya en fazla {KB_MAX_BYTES / 1_000_000:g} MB olabilir.")
        return None
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        st.error("Dosya UTF-8 veya UTF-8 BOM olmalı.")
        return None
    return {"kind": kind, "filename": uploaded.name[:120], "content": content, "domain": domain,
            "license_note": license_note.strip()}


def render_kb_upload() -> None:
    token = st.session_state.token
    st.caption("Yüklenen kayıtlar önce **Onay bekliyor** durumunda eklenir ve aranamaz. Onayladığında embedding "
               "üretilir ve bot kullanmaya başlar. Dosya içeriği çalıştırılmaz.")
    label = st.radio("Dosya türü", ["Servis masası CSV", "Rehber JSON"], horizontal=True, key="kb_kind")
    is_csv = label == "Servis masası CSV"
    domain, license_note = "general_it", ""
    if is_csv:
        st.caption("Sütunlar: issueid, problem, solution (zorunlu); category, resolution, resolution_confirmed, "
                   f"solution_scope, limitations (isteğe bağlı). En fazla {kb_limits.MAX_ROWS} satır.")
        chosen_domain = st.selectbox("Alan", list(DOMAIN_LABELS.values()), key="kb_domain")
        domain = next(key for key, value in DOMAIN_LABELS.items() if value == chosen_domain)
        license_note = st.text_input("Kaynak / lisans notu (zorunlu)", max_chars=200, key="kb_license")
    else:
        st.caption("Resmî rehber kaydı: `data_sources/official_guides` biçimi. Yalnız learn.microsoft.com ve "
                   "docs.oracle.com kaynakları kabul edilir. Oracle belgelerinin telifi Oracle'a aittir; metni "
                   "kopyalama, kısa ve kendi cümlelerinle yazılmış olgu özeti yükle.")
    uploaded = st.file_uploader("Dosya", type=["csv" if is_csv else "json"], key=f"kb_file_{label}",
                                max_upload_size=max(1, -(-KB_MAX_BYTES // 1_000_000)),
                                help=f"En fazla {KB_MAX_BYTES / 1_000_000:g} MB ve {kb_limits.MAX_ROWS} satır.")
    payload = _kb_payload("tickets_csv" if is_csv else "guide_json", domain, license_note, uploaded)
    checked = st.session_state.get("kb_check")
    if st.button("Doğrula", disabled=payload is None, key="kb_validate"):
        try:
            with st.spinner("Dosya doğrulanıyor…"):
                result = ui_client.kb_upload(API_URL, token, {**payload, "dry_run": True})
            st.session_state.kb_check = checked = {"payload": payload, "result": result}
        except ui_client.ApiError as error:
            st.session_state.pop("kb_check", None)
            checked = None
            handle_api_error(error)
    if checked and payload is not None and checked["payload"] == payload:
        result = checked["result"]
        st.write(f"Geçerli kayıt: **{result['valid']}**")
        for message in result["errors"]:
            st.warning(message)
        if result["preview"]:
            st.dataframe([{"Kimlik": i["id"], "Alan": DOMAIN_LABELS.get(i["domain"], i["domain"]),
                           "Başlık": i["title"], "Problem": i["problem"]} for i in result["preview"]],
                         hide_index=True, use_container_width=True)
        if st.button("Onay bekleyenlere ekle", disabled=bool(result["errors"]) or not result["valid"],
                     key="kb_stage"):
            try:
                with st.spinner("Kayıtlar ekleniyor…"):
                    done = ui_client.kb_upload(API_URL, token, {**payload, "dry_run": False})
                st.session_state.pop("kb_check", None)
                st.session_state.kb_notice = (f"{done['added']} kayıt onay bekleyenlere eklendi; "
                                              f"{done['already_present']} kayıt zaten vardı.")
                st.rerun()
            except ui_client.ApiError as error:
                handle_api_error(error)


def render_knowledge_center() -> None:
    token = st.session_state.token
    if notice := st.session_state.pop("kb_notice", None):
        st.success(notice)
    try:
        summary = ui_client.kb_summary(API_URL, token)
    except ui_client.ApiError as error:
        if error.status == 403:
            st.session_state.view = "chat"
        handle_api_error(error)
        return
    count = lambda status: sum(g["count"] for g in summary["groups"] if g["review_status"] == status)
    columns = st.columns(4)
    columns[0].metric("Toplam kayıt", summary["total"])
    columns[1].metric("Aranabilir", summary["searchable"], help="Onaylı ve geçerli embedding'i olan kayıtlar.")
    columns[2].metric("Onay bekleyen", count("pending"))
    columns[3].metric("Devre dışı", count("excluded"))
    st.caption("Bilgi tabanını yalnız yöneticiler değiştirir. Kayıtlar silinmez; devre dışı bırakılanlar aramadan çıkar.")
    with st.expander("Dosya yükle"):
        render_kb_upload()

    st.subheader("Kayıtlar")
    first = st.columns(4)
    status = first[0].selectbox("Durum", ["Hepsi", *STATUS_LABELS.values()], key="kb_f_status")
    domain = first[1].selectbox("Alan", ["Hepsi", *DOMAIN_LABELS.values()], key="kb_f_domain")
    kind = first[2].selectbox("Tür", ["Hepsi", *TYPE_LABELS.values()], key="kb_f_type")
    query = first[3].text_input("Ara", max_chars=100, key="kb_f_query")
    filters = {"review_status": next((k for k, v in STATUS_LABELS.items() if v == status), None),
               "domain": next((k for k, v in DOMAIN_LABELS.items() if v == domain), None),
               "record_type": next((k for k, v in TYPE_LABELS.items() if v == kind), None),
               "query": query.strip() or None}
    if st.session_state.get("kb_filters") != filters:
        st.session_state.kb_filters, st.session_state.kb_offset = filters, 0
    offset = st.session_state.get("kb_offset", 0)
    try:
        page = ui_client.kb_records(API_URL, token, offset=offset, **filters)
    except ui_client.ApiError as error:
        handle_api_error(error)
        return
    items = page["items"]
    st.caption(f"{page['total']} kayıt · gösterilen {offset + 1 if items else 0}–{offset + len(items)}")
    if items:
        st.dataframe([{"Kaynak kimliği": i["source_record_id"], "Tür": TYPE_LABELS.get(i["record_type"], ""),
                       "Alan": DOMAIN_LABELS.get(i["domain"], i["domain"]),
                       "Durum": STATUS_LABELS.get(i["review_status"], i["review_status"]),
                       "Kaynak": i["source_name"], "Problem": i["problem"]} for i in items],
                     hide_index=True, use_container_width=True)
    nav = st.columns(2)
    if nav[0].button("Önceki sayfa", disabled=offset == 0, key="kb_prev"):
        st.session_state.kb_offset = max(0, offset - 50)
        st.rerun()
    if nav[1].button("Sonraki sayfa", disabled=page["next_offset"] is None, key="kb_next"):
        st.session_state.kb_offset = page["next_offset"]
        st.rerun()

    label = lambda i: f"{i['source_record_id']} · {DOMAIN_LABELS.get(i['domain'], '')} — {i['problem'][:70]}"
    pending = {i["id"]: i for i in items if i["review_status"] == "pending"}
    if pending:
        st.subheader("Onay bekleyenler")
        chosen = st.multiselect("Onaylanacak kayıtlar (en fazla 10)", list(pending), max_selections=10,
                                format_func=lambda key: label(pending[key]), key="kb_approve_ids")
        if st.button("Seçilenleri indeksle ve onayla", disabled=not chosen, key="kb_approve"):
            try:
                with st.spinner("Embedding üretiliyor ve kayıtlar indeksleniyor…"):
                    outcome = ui_client.kb_approve(API_URL, token, chosen)
                done = sum(1 for r in outcome["items"] if r["status"] in {"indexed", "already"})
                failed = [r["message"] for r in outcome["items"] if r["status"] == "failed"]
                st.session_state.kb_notice = f"{done} kayıt aktif; {len(failed)} kayıt başarısız." + (
                    " " + " / ".join(dict.fromkeys(failed)) if failed else "")
                st.session_state.pop("kb_approve_ids", None)
                st.rerun()
            except ui_client.ApiError as error:
                handle_api_error(error)
        if len(pending) > 1 and st.button(f"Sayfadaki {len(pending)} bekleyeni onayla (10'arlı gruplar)",
                                          key="kb_approve_page"):
            ids, done, failed = list(pending), 0, []
            bar = st.progress(0.0, text="Kayıtlar indeksleniyor…")
            try:
                for start in range(0, len(ids), 10):
                    outcome = ui_client.kb_approve(API_URL, token, ids[start:start + 10])
                    done += sum(1 for r in outcome["items"] if r["status"] in {"indexed", "already"})
                    failed += [r["message"] for r in outcome["items"] if r["status"] == "failed"]
                    bar.progress(min(1.0, (start + 10) / len(ids)), text=f"{min(start + 10, len(ids))}/{len(ids)}")
            except ui_client.ApiError as error:
                st.session_state.kb_notice = f"İşlem yarıda kaldı: {done} kayıt aktif. {error}"
                st.rerun()
            st.session_state.kb_notice = f"{done} kayıt aktif; {len(failed)} kayıt başarısız." + (
                " " + " / ".join(dict.fromkeys(failed)) if failed else "")
            st.rerun()
    manageable = {i["id"]: i for i in items if i["review_status"] in {"approved", "excluded"}}
    if manageable:
        st.subheader("Devre dışı bırak / geri al")
        record_id = st.selectbox("Kayıt", list(manageable), key="kb_status_id",
                                 format_func=lambda key: f"[{STATUS_LABELS[manageable[key]['review_status']]}] "
                                                         + label(manageable[key]))
        excluded = manageable[record_id]["review_status"] == "approved"
        if st.button("Devre dışı bırak" if excluded else "Geri al", key="kb_toggle"):
            try:
                result = ui_client.kb_set_status(API_URL, token, record_id, excluded)
                st.session_state.kb_notice = "Kayıt güncellendi: " + STATUS_LABELS.get(
                    "excluded" if result["status"] == "excluded" else result["status"], result["status"])
                st.rerun()
            except ui_client.ApiError as error:
                handle_api_error(error)


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
        if st.session_state.get("view") == "admin" and st.session_state.get("user", {}).get("role") == "admin":
            render_admin()
        else:
            st.session_state.view = "chat"
            render_chat()
    else:
        render_auth()


main()
