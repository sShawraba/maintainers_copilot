import streamlit as st
import requests
from datetime import datetime

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Maintainer's Copilot")
st.title("🐼 Maintainer's Copilot")

# ---------- Session state defaults ----------
if "token" not in st.session_state:
    st.session_state.token = None
if "current_conv_id" not in st.session_state:
    st.session_state.current_conv_id = None
if "conversations" not in st.session_state:
    st.session_state.conversations = {}  # {conv_id: {"title": str, "messages": []}}
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------- Helper functions ----------
def fetch_conversations_from_backend():
    if not st.session_state.token:
        return []
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    try:
        resp = requests.get(f"{API_URL}/conversations/", headers=headers, timeout=5)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.sidebar.error(f"Error {resp.status_code}: {resp.text[:100]}")
            return []
    except Exception as e:
        st.sidebar.error(f"Connection error: {e}")
        return []

def fetch_conversation_messages(conv_id):
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    try:
        resp = requests.get(f"{API_URL}/conversations/{conv_id}", headers=headers, timeout=5)
        if resp.status_code == 200:
            return resp.json()["messages"]
        else:
            st.sidebar.error(f"Error loading messages: {resp.status_code}")
            return []
    except Exception as e:
        st.sidebar.error(f"Error: {e}")
        return []

def new_conversation():
    conv_id = str(int(datetime.now().timestamp()))
    title = f"Conversation {datetime.now().strftime('%H:%M')}"
    st.session_state.conversations[conv_id] = {"title": title, "messages": []}
    st.session_state.current_conv_id = conv_id
    st.session_state.messages = []
    st.rerun()

def load_conversation(conv_id):
    st.session_state.current_conv_id = conv_id
    messages = fetch_conversation_messages(conv_id)
    st.session_state.messages = messages
    if conv_id not in st.session_state.conversations:
        st.session_state.conversations[conv_id] = {"title": f"Conv {conv_id[-6:]}", "messages": messages}
    else:
        st.session_state.conversations[conv_id]["messages"] = messages
    st.rerun()

def add_message(role, content):
    st.session_state.messages.append({"role": role, "content": content})
    if st.session_state.current_conv_id:
        if st.session_state.current_conv_id not in st.session_state.conversations:
            st.session_state.conversations[st.session_state.current_conv_id] = {"title": "New", "messages": []}
        st.session_state.conversations[st.session_state.current_conv_id]["messages"] = st.session_state.messages.copy()

def refresh_conversation_list():
    convs = fetch_conversations_from_backend()
    new_convs = {}
    for conv in convs:
        conv_id = conv["conversation_id"]
        new_convs[conv_id] = {
            "title": conv.get("title", f"Conv {conv_id[-6:]}"),
            "messages": []
        }
    # Preserve current conversation messages if still present
    if st.session_state.current_conv_id and st.session_state.current_conv_id in new_convs:
        new_convs[st.session_state.current_conv_id]["messages"] = st.session_state.messages
    elif st.session_state.current_conv_id and st.session_state.current_conv_id in st.session_state.conversations:
        new_convs[st.session_state.current_conv_id] = st.session_state.conversations[st.session_state.current_conv_id]
    st.session_state.conversations = new_convs
    return new_convs

# ---------- Authentication ----------
if not st.session_state.token:
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        email_login = st.text_input("Email", key="login_email")
        password_login = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            resp = requests.post(f"{API_URL}/auth/login", data={"username": email_login, "password": password_login})
            if resp.status_code == 200:
                st.session_state.token = resp.json()["access_token"]
                convs = refresh_conversation_list()
                if convs:
                    most_recent = sorted(convs.keys(), reverse=True)[0]
                    load_conversation(most_recent)
                else:
                    new_conversation()
                st.rerun()
            else:
                st.error("Invalid credentials")
    with tab2:
        email_reg = st.text_input("Email", key="reg_email")
        password_reg = st.text_input("Password", type="password", key="reg_password")
        if st.button("Sign Up"):
            resp = requests.post(f"{API_URL}/auth/register", json={"email": email_reg, "password": password_reg})
            if resp.status_code in [200, 201]:
                # Auto-login
                login_resp = requests.post(f"{API_URL}/auth/login", data={"username": email_reg, "password": password_reg})
                if login_resp.status_code == 200:
                    st.session_state.token = login_resp.json()["access_token"]
                    refresh_conversation_list()
                    if st.session_state.conversations:
                        most_recent = sorted(st.session_state.conversations.keys(), reverse=True)[0]
                        load_conversation(most_recent)
                    else:
                        new_conversation()
                    st.rerun()
                else:
                    st.success("Account created! Please login.")
            else:
                st.error("Registration failed. Email may already exist.")
else:
    # ---------- Sidebar ----------
    with st.sidebar:
        st.success("Logged in")
        if st.button("➕ New Conversation"):
            new_conversation()
        if st.button("🔄 Refresh"):
            refresh_conversation_list()
            st.rerun()
        st.divider()
        st.subheader("Conversations")
        if st.session_state.conversations:
            for conv_id, conv_data in sorted(st.session_state.conversations.items(), key=lambda x: x[0], reverse=True):
                title = conv_data.get("title", "Untitled")
                if conv_id == st.session_state.current_conv_id:
                    st.markdown(f"**✅ {title}**")
                else:
                    if st.button(title, key=conv_id):
                        load_conversation(conv_id)
                        st.rerun()
        else:
            st.info("No conversations yet")
        st.divider()
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

    # ---------- Chat ----------
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("Ask about pandas...")
    if user_input:
        if not st.session_state.current_conv_id:
            new_conversation()
        add_message("user", user_input)
        with st.chat_message("user"):
            st.write(user_input)

        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        payload = {"message": user_input, "conversation_id": st.session_state.current_conv_id}
        try:
            with st.spinner("Thinking..."):
                resp = requests.post(f"{API_URL}/chat/", json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                bot_reply = resp.json()["response"]
                add_message("assistant", bot_reply)
                with st.chat_message("assistant"):
                    st.write(bot_reply)
                refresh_conversation_list()
            else:
                error_msg = f"Error: {resp.status_code}"
                add_message("assistant", error_msg)
                with st.chat_message("assistant"):
                    st.error(error_msg)
        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            add_message("assistant", error_msg)
            with st.chat_message("assistant"):
                st.error(error_msg)

        st.rerun()