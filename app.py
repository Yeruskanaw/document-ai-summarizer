import mimetypes
import os
import re
import sqlite3
from html import escape
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types


# ==========================================
# CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "chat_history.db"

load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)

# File upload settings
MAX_FILE_MB = 10
ALLOWED_TYPES = [
    "pdf", "png", "jpg", "jpeg", "webp",
    "txt", "md", "csv", "json", "py", "html", "css", "js", "xml",
]
TEXT_EXTS = {
    ".txt", ".md", ".csv", ".json", ".py",
    ".html", ".css", ".js", ".xml", ".log",
}

# Tells the model how to hand files back to the user.
SYSTEM_INSTRUCTION = (
    "You are a friendly, helpful assistant. Answer in the same "
    "language the user writes in. "
    "When the user asks you to create a file (text, CSV, code, "
    "markdown, HTML, JSON and so on), put the full file content "
    "in exactly this format, with the file name and extension of "
    "your choice:\n"
    "<<<FILE:name.ext>>>\n"
    "file content here\n"
    "<<<END>>>\n"
    "Do not wrap that block in a code fence. You may write normal "
    "text before and after it."
)

st.set_page_config(
    page_title="My AI Assistant",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==========================================
# THEME - soft pink and lilac
# ==========================================

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Varela+Round&display=swap');

:root {
    --white: #FFFFFF;
    --pink-50: #FFF5FA;
    --pink-100: #FFE4EF;
    --pink-200: #FBCFE3;
    --pink-300: #F8C8DC;
    --pink-500: #F48FB8;
    --pink-600: #EE79AA;
    --lilac-100: #F3ECFD;
    --lilac-200: #EADCFB;
    --lilac-400: #C9B1F2;
    --lilac-600: #9B7FDC;
    --plum: #5A2347;
    --plum-soft: #A0587E;
    --muted: #B5628F;
    color-scheme: light;
}

/* ---------- Font ---------- */
html, body, .stApp,
.stApp p, .stApp li, .stApp h1, .stApp h2, .stApp h3,
.stApp label, .stApp button, .stApp textarea, .stApp input,
.stApp [data-testid="stMarkdownContainer"],
.stApp [data-testid="stCaptionContainer"] {
    font-family: 'Varela Round', sans-serif !important;
}

.stApp {
    font-size: 14px;
    color: var(--plum);
    background: linear-gradient(
        160deg, #FFFFFF 0%, #FFE9F2 50%, #FBCFE3 100%
    );
    background-attachment: fixed;
}

.stApp p, .stApp li {
    font-size: 14px;
    color: var(--plum);
    unicode-bidi: plaintext;
}

h1, h2, h3 {
    color: var(--plum);
    font-weight: 400;
}

[data-testid="stHeader"] {
    background: transparent;
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(180deg, #FFF8FB 0%, #FFE4EF 100%);
    border-right: none;
}

.section-label {
    color: var(--muted);
    font-size: 11px;
    letter-spacing: 1px;
    margin: 16px 0 6px 0;
}

/* ---------- Buttons (general) ---------- */
.stButton > button {
    border-radius: 14px;
    border: 1px solid var(--pink-300);
    background: var(--white);
    color: var(--plum);
    min-height: 38px;
    font-size: 13px;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    border-color: var(--lilac-400);
    color: var(--lilac-600);
    background: var(--lilac-100);
}

/* New chat button */
[class*="st-key-new_chat"] button {
    background: var(--pink-500) !important;
    border: none !important;
    color: #4A1431 !important;
    border-radius: 999px !important;
}

[class*="st-key-new_chat"] button:hover {
    background: var(--pink-600) !important;
    color: #4A1431 !important;
}

/* Chat history: plain text rows, no frames */
[class*="st-key-open_"] button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: var(--plum-soft) !important;
    justify-content: flex-start !important;
    min-height: 34px;
    padding: 4px 6px;
}

[class*="st-key-open_"] button:hover {
    background: transparent !important;
    color: var(--lilac-600) !important;
}

[class*="st-key-open_"] button div,
[class*="st-key-open_"] button p {
    width: 100%;
    text-align: start;
    unicode-bidi: plaintext;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* The active chat: lilac text, no frame */
[class*="st-key-open_"] button[kind="primary"],
[class*="st-key-open_"] button[data-testid="stBaseButton-primary"] {
    color: var(--lilac-600) !important;
}

/* Delete button: just an icon */
[class*="st-key-delete_"] button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: var(--muted) !important;
    min-height: 34px;
}

[class*="st-key-delete_"] button:hover {
    background: transparent !important;
    color: var(--pink-600) !important;
}

/* ---------- Hero ---------- */
.hero {
    padding: 18px 24px;
    border-radius: 24px;
    background: rgba(255, 255, 255, 0.6);
    margin-bottom: 20px;
}

.hero-title {
    font-size: 24px;
    margin: 0;
    color: var(--plum);
}

.hero-subtitle {
    color: var(--muted);
    font-size: 13px;
    margin-top: 6px;
}

/* ---------- Chat messages ---------- */
/* Bot answer: left side, no color, no frame */
[data-testid="stChatMessage"] {
    border: none;
    border-radius: 0;
    background: transparent;
    padding: 4px 0;
    margin-bottom: 10px;
    max-width: 100%;
}

/* User question: right side, pink rounded bubble */
[data-testid="stChatMessage"]:has(
    [data-testid="chatAvatarIcon-user"]
),
[data-testid="stChatMessage"]:has(
    [data-testid="stChatMessageAvatarUser"]
) {
    background: var(--pink-200);
    border-radius: 20px;
    padding: 10px 16px;
    width: fit-content;
    max-width: 75%;
    margin-left: auto;
}

/* No avatars, just the bubbles */
[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"],
[data-testid="chatAvatarIcon-user"],
[data-testid="chatAvatarIcon-assistant"] {
    display: none;
}

/* ---------- Chat input ---------- */
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] {
    background: transparent !important;
}

[data-testid="stChatInput"] {
    border: 1px solid var(--pink-200);
    border-radius: 16px;
    background: var(--white);
    box-shadow: none;
}

[data-testid="stChatInput"] > div {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: var(--pink-300);
    box-shadow: none;
}

[data-testid="stChatInput"] textarea {
    color: var(--plum) !important;
    background: transparent !important;
    caret-color: var(--lilac-600);
    font-size: 14px;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: var(--muted) !important;
    opacity: 1;
}

[data-testid="stChatInput"] button {
    color: var(--lilac-600) !important;
}

/* ---------- File uploader and expanders ---------- */
[data-testid="stFileUploaderDropzone"] {
    background: rgba(255, 255, 255, 0.7);
    border: 1.5px dashed var(--pink-500);
    border-radius: 18px;
}

[data-testid="stExpander"] details {
    border: none !important;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.55);
}

[data-testid="stDownloadButton"] button {
    background: var(--lilac-200);
    border: none;
    color: #3D2C6B;
    border-radius: 999px;
}

[data-testid="stDownloadButton"] button:hover {
    background: var(--lilac-400);
    color: #3D2C6B;
}

hr {
    border-color: var(--pink-300);
}

@media (max-width: 700px) {
    .hero {
        padding: 14px 16px;
        border-radius: 18px;
    }
    .hero-title {
        font-size: 20px;
    }
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


# ==========================================
# DATABASE
# Uses the existing SQLite database.
# ==========================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (
                    datetime('now', 'localtime')
                )
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL
                    CHECK(role IN ('user', 'model')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (
                    datetime('now', 'localtime')
                ),
                FOREIGN KEY(chat_id)
                    REFERENCES chats(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                data BLOB NOT NULL,
                FOREIGN KEY(message_id)
                    REFERENCES messages(id)
                    ON DELETE CASCADE
            );
        """)


def get_chats():
    with get_db() as conn:
        return conn.execute("""
            SELECT id, title, created_at
            FROM chats
            ORDER BY id DESC
        """).fetchall()


def create_chat():
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO chats (title) VALUES (?)",
            ("שיחה חדשה",)
        )
        return cursor.lastrowid


def delete_chat(chat_id):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM chats WHERE id = ?",
            (chat_id,)
        )


def get_messages(chat_id):
    with get_db() as conn:
        return conn.execute("""
            SELECT id, role, content, created_at
            FROM messages
            WHERE chat_id = ?
            ORDER BY id ASC
        """, (chat_id,)).fetchall()


def save_message(chat_id, role, content):
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO messages (chat_id, role, content)
            VALUES (?, ?, ?)
        """, (chat_id, role, content))
        return cursor.lastrowid


def save_attachment(message_id, filename, mime_type, data):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO chat_files
                (message_id, filename, mime_type, data)
            VALUES (?, ?, ?, ?)
        """, (message_id, filename, mime_type, data))


def get_attachments(message_id):
    with get_db() as conn:
        return conn.execute("""
            SELECT filename, mime_type, data
            FROM chat_files
            WHERE message_id = ?
            ORDER BY id ASC
        """, (message_id,)).fetchall()


def update_chat_title(chat_id, title):
    title = " ".join(title.split())[:48]
    with get_db() as conn:
        conn.execute("""
            UPDATE chats
            SET title = ?
            WHERE id = ?
        """, (title, chat_id))


# ==========================================
# FILE HELPERS
# ==========================================

FILE_PATTERN = re.compile(
    r"<<<FILE:\s*(.+?)\s*>>>\r?\n(.*?)\r?\n?<<<END>>>",
    re.DOTALL,
)


def safe_filename(name):
    name = Path(name.strip()).name
    name = re.sub(r"[^\w.\- ]", "_", name, flags=re.UNICODE)
    return name or "file.txt"


def attachment_to_parts(filename, mime_type, data):
    """Convert a stored attachment into Gemini content parts."""
    ext = Path(filename).suffix.lower()

    if ext in TEXT_EXTS:
        text = data.decode("utf-8", errors="replace")
        return [types.Part(
            text=f"[Attached file: {filename}]\n{text}"
        )]

    return [
        types.Part(text=f"[Attached file: {filename}]"),
        types.Part.from_bytes(data=data, mime_type=mime_type),
    ]


def build_contents(history):
    contents = []

    for message in history:
        parts = [types.Part(text=message["content"])]

        if message["role"] == "user":
            for att in get_attachments(message["id"]):
                parts.extend(attachment_to_parts(
                    att["filename"],
                    att["mime_type"],
                    att["data"],
                ))

        contents.append(
            types.Content(role=message["role"], parts=parts)
        )

    return contents


def render_user_message(message):
    st.markdown(message["content"], unsafe_allow_html=False)

    for att in get_attachments(message["id"]):
        if att["mime_type"].startswith("image/"):
            st.image(att["data"], width=240, caption=att["filename"])
        else:
            st.caption(f"📎 {att['filename']}")


def render_assistant_message(message):
    """Show the answer; turn file blocks into download buttons."""
    content = message["content"]
    position = 0
    index = 0

    for match in FILE_PATTERN.finditer(content):
        before = content[position:match.start()].strip()
        if before:
            st.markdown(before, unsafe_allow_html=False)

        name = safe_filename(match.group(1))
        body = match.group(2)

        # utf-8-sig so Excel opens Hebrew CSV files correctly
        encoding = "utf-8-sig" if name.lower().endswith(".csv") \
            else "utf-8"
        mime = mimetypes.guess_type(name)[0] or "text/plain"

        with st.expander(f"📄 {name}"):
            st.code(body, language=None)

        st.download_button(
            f"⬇ הורדת {name}",
            data=body.encode(encoding),
            file_name=name,
            mime=mime,
            key=f"dl_{message['id']}_{index}",
        )

        position = match.end()
        index += 1

    rest = content[position:].strip()
    if rest:
        st.markdown(rest, unsafe_allow_html=False)


# ==========================================
# SESSION STATE
# ==========================================

initialize_db()

if "chat_id" not in st.session_state:
    st.session_state.chat_id = None

if "delete_confirm_id" not in st.session_state:
    st.session_state.delete_confirm_id = None

if "pending_error" not in st.session_state:
    st.session_state.pending_error = None

if not API_KEY:
    st.error(
        "לא נמצא מפתח API. "
        "בדקי שקובץ .env נמצא בתיקיית הפרויקט."
    )
    st.stop()

client = genai.Client(api_key=API_KEY)

chats = get_chats()

if not chats:
    st.session_state.chat_id = create_chat()
    st.rerun()

valid_ids = {chat["id"] for chat in chats}

if st.session_state.chat_id not in valid_ids:
    st.session_state.chat_id = chats[0]["id"]


# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar:
    st.markdown(
        """
        <div style="padding: 12px 2px 18px 2px;">
            <div style="font-size: 26px; color: var(--pink-600);">
                ✦ My AI Assistant
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "＋ new",
        key="new_chat",
        use_container_width=True,
    ):
        st.session_state.chat_id = create_chat()
        st.session_state.delete_confirm_id = None
        st.session_state.pending_error = None
        st.rerun()

    st.markdown(
        '<div class="section-label">היסטוריית שיחות</div>',
        unsafe_allow_html=True,
    )

    for chat in chats:
        chat_id = chat["id"]
        is_active = chat_id == st.session_state.chat_id

        open_col, delete_col = st.columns([5, 1])

        with open_col:
            label = chat["title"] or "שיחה חדשה"

            if is_active:
                label = "✦ " + label

            if st.button(
                label,
                key=f"open_{chat_id}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.chat_id = chat_id
                st.session_state.delete_confirm_id = None
                st.session_state.pending_error = None
                st.rerun()

        with delete_col:
            if st.button(
                "🗑",
                key=f"delete_{chat_id}",
                help="מחיקת שיחה",
                use_container_width=True,
            ):
                st.session_state.delete_confirm_id = chat_id

        if st.session_state.delete_confirm_id == chat_id:
            st.warning(f'למחוק את "{chat["title"]}"?')

            yes_col, no_col = st.columns(2)

            with yes_col:
                if st.button(
                    "מחיקה",
                    key=f"confirm_{chat_id}",
                    use_container_width=True,
                ):
                    delete_chat(chat_id)
                    st.session_state.delete_confirm_id = None

                    remaining = get_chats()

                    if chat_id == st.session_state.chat_id:
                        st.session_state.chat_id = (
                            remaining[0]["id"]
                            if remaining else create_chat()
                        )

                    st.rerun()

            with no_col:
                if st.button(
                    "ביטול",
                    key=f"cancel_{chat_id}",
                    use_container_width=True,
                ):
                    st.session_state.delete_confirm_id = None
                    st.rerun()

    st.divider()

    st.markdown(
        """
        <div style="padding: 6px 2px 4px 2px;
                    color: var(--muted); font-size: 11px;
                    text-align: center;">
            Powered by Gemini ✦
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==========================================
# MAIN CHAT
# ==========================================

current_chat_id = st.session_state.chat_id

messages = get_messages(current_chat_id)

if not messages:
    st.markdown(
        """
        <div style="text-align:center; padding: 48px 12px 36px 12px;">
            <div style="font-size: 44px; color: var(--pink-500);">
                ✦
            </div>
            <div style="font-size: 22px;
                        color: var(--plum); margin-top: 12px;">
                מה תרצי לדעת היום?
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Display the saved messages.

for message in messages:
    display_role = (
        "assistant" if message["role"] == "model"
        else "user"
    )

    with st.chat_message(display_role):
        if display_role == "user":
            render_user_message(message)
        else:
            render_assistant_message(message)

if st.session_state.pending_error:
    st.error(st.session_state.pending_error)


# ==========================================
# SEND MESSAGE
# The attach button lives inside the input box.
# ==========================================

submission = st.chat_input(
    "כתבי את השאלה שלך כאן...",
    accept_file="multiple",
    file_type=ALLOWED_TYPES,
)

user_input = ""
uploaded_files = []

if submission:
    user_input = (submission.text or "").strip()
    uploaded_files = list(submission.files or [])

if user_input or uploaded_files:

    # Check the attached files.
    attachments = []
    skipped = []

    for f in uploaded_files:
        data = f.getvalue()

        if len(data) > MAX_FILE_MB * 1024 * 1024:
            skipped.append(f.name)
            continue

        mime_type = (
            f.type
            or mimetypes.guess_type(f.name)[0]
            or "application/octet-stream"
        )
        attachments.append((f.name, mime_type, data))

    is_first_message = not messages

    # Save the user's question and its files.
    user_message_id = save_message(
        current_chat_id, "user", user_input
    )

    for filename, mime_type, data in attachments:
        save_attachment(user_message_id, filename, mime_type, data)

    if is_first_message:
        first_title = user_input or (
            attachments[0][0] if attachments else "שיחה חדשה"
        )
        update_chat_title(current_chat_id, first_title)

    # Build the conversation context from SQLite.
    history = get_messages(current_chat_id)
    contents = build_contents(history)

    try:
        with st.spinner("Gemini חושב..."):
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                ),
            )

        answer = response.text

        if not answer:
            answer = "לא התקבלה תשובת טקסט מהמודל."

        save_message(current_chat_id, "model", answer)

        if skipped:
            st.session_state.pending_error = (
                "הקבצים הבאים לא נשלחו כי הם גדולים מדי: "
                + ", ".join(skipped)
            )
        else:
            st.session_state.pending_error = None

    except Exception as e:
        st.session_state.pending_error = (
            f"לא הצלחתי לקבל תשובה מ-Gemini: {e}"
        )

    st.rerun()
    