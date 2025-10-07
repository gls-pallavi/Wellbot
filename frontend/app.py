import streamlit as st
import re
import requests

st.set_page_config(page_title="WellBot")

st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle, #A7C7E7, #D7BDE2);
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("WellBot")

API_URL = "http://127.0.0.1:8000"

def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "show_forgot" not in st.session_state:
    st.session_state.show_forgot = False
if "token" not in st.session_state:
    st.session_state.token = None
if "edit_profile" not in st.session_state:
    st.session_state.edit_profile = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "feedback_submitted" not in st.session_state:
    st.session_state.feedback_submitted = {}

if st.session_state.admin_logged_in:
    try:
        import admin_dashboard as admin_dashboard_module
    except Exception:
        from importlib import import_module
        admin_dashboard_module = import_module("admin_dashboard")
    admin_dashboard_module.dashboard_page()
    st.stop()

if not st.session_state.logged_in:
    if not st.session_state.show_forgot:
        login_tab, register_tab, admin_tab = st.tabs(["Login", "Register", "Admin Login"])
        with login_tab:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Login"):
                    if not email or not password:
                        st.error("⚠️ Please fill out all fields")
                    elif not is_valid_email(email):
                        st.error("⚠️ Invalid email format")
                    else:
                        try:
                            response = requests.post(
                                f"{API_URL}/login",
                                json={"email": email, "password": password}
                            )
                            if response.status_code == 200:
                                data = response.json()
                                st.session_state.logged_in = True
                                st.session_state.token = data.get("access_token")
                                st.session_state.current_user = email
                                st.session_state.user_id = data.get("user_id")
                                st.success("✅ Logged in successfully!")
                                st.rerun()
                            elif response.status_code == 401:
                                st.error("❌ Invalid password. Please try again.")
                            elif response.status_code == 404:
                                st.error("❌ Email not registered. Please register first.")
                            else:
                                error_msg = response.json().get("detail", "Login failed")
                                st.error(f"❌ {error_msg}")
                        except requests.exceptions.RequestException:
                            st.error("⚠️ Backend not reachable. Please try again later.")
            with col2:
                if st.button("Forgot Password?"):
                    st.session_state.show_forgot = True
                    st.rerun()

        with register_tab:
            name = st.text_input("Full Name", key="reg_name")
            new_email = st.text_input("Email (Register)", key="reg_email")
            new_password = st.text_input("Password (Register)", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
            if st.button("Register"):
                if not name or not new_email or not new_password or not confirm_password:
                    st.error("⚠️ Please fill out all fields")
                elif not is_valid_email(new_email):
                    st.error("⚠️ Invalid email format")
                elif new_password != confirm_password:
                    st.error("⚠️ Passwords do not match")
                else:
                    try:
                        response = requests.post(
                            f"{API_URL}/register",
                            json={"name": name, "email": new_email, "password": new_password}
                        )
                        if response.status_code in [200, 201]:
                            st.success("✅ Registered successfully! Please login.")
                        elif response.status_code == 400:
                            st.error("❌ Email already registered. Try logging in.")
                        else:
                            error_msg = response.json().get("detail", "Registration failed")
                            st.error(f"❌ {error_msg}")
                    except requests.exceptions.RequestException:
                        st.error("⚠️ Backend not reachable. Please try again later.")

        with admin_tab:
            st.subheader("Admin Login")
            admin_user = st.text_input("Admin Username", key="admin_username")
            admin_pass = st.text_input("Admin Password", type="password", key="admin_password")
            if st.button("Login as Admin"):
                if admin_user == "admin" and admin_pass == "admin123":
                    st.session_state.admin_logged_in = True
                    st.success("✅ Admin login successful! Redirecting to admin dashboard...")
                    st.rerun()
                else:
                    st.error("❌ Invalid admin credentials.")
    else:
        st.subheader("Forgot Password")
        st.info("🔒 Feature will be implemented later.")
        if st.button("Back to Login"):
            st.session_state.show_forgot = False
            st.rerun()
else:
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    try:
        profile_resp = requests.get(f"{API_URL}/profile", headers=headers)
        profile_data = profile_resp.json() if profile_resp.status_code == 200 else {}
    except Exception:
        profile_data = {}
    profile_exists = bool(profile_data)
    if not profile_exists:
        st.subheader("Create Your Profile")
        st.session_state.edit_profile = True
    else:
        st.subheader("👤 Your Profile")
        st.text(f"Age Group: {profile_data.get('age_group', '-')}")
        st.text(f"Gender: {profile_data.get('gender', '-')}")
        st.text(f"Language: {profile_data.get('language', '-')}")
        if st.button("Edit Profile"):
            st.session_state.edit_profile = True
            st.rerun()

    if st.session_state.edit_profile:
        age_options = ["Select Age Group", "Below 18", "18-25", "26-35", "36-45", "46-60", "Above 60"]
        gender_options = ["Male", "Female", "Other"]
        lang_options = ["English", "Hindi"]

        age_index = age_options.index(profile_data.get("age_group")) if profile_data.get("age_group") in age_options else 0
        gender_index = gender_options.index(profile_data.get("gender")) if profile_data.get("gender") in gender_options else 0
        lang_index = lang_options.index(profile_data.get("language")) if profile_data.get("language") in lang_options else 0

        age_group = st.selectbox("Select Age Group", age_options, index=age_index)
        gender = st.radio("Gender", gender_options, index=gender_index)
        language = st.selectbox("Preferred Language", lang_options, index=lang_index)
        btn_text = "Update Profile" if profile_exists else "Save Profile"
        if st.button(btn_text):
            if age_group == "Select Age Group":
                st.error("⚠️ Please select a valid age group.")
            else:
                response = requests.put(
                    f"{API_URL}/profile",
                    json={"age_group": age_group, "gender": gender, "language": language},
                    headers=headers
                )
                if response.status_code == 200:
                    st.success("✅ Profile saved successfully! 🎉")
                    st.session_state.edit_profile = False
                    st.rerun()
                else:
                    st.error("❌ Failed to save profile")

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.token = None
        st.session_state.current_user = None
        st.session_state.user_id = None
        st.session_state.edit_profile = False
        st.session_state.chat_history = []
        st.session_state.user_input = ""
        st.rerun()

    st.subheader("💬 Chat with WellBot")

    def send_message():
        user_message = st.session_state.user_input.strip()
        if user_message == "":
            return
        st.session_state.chat_history.append({"sender": "user", "message": user_message})
        try:
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            response = requests.post(
                f"{API_URL}/predict_chat",
                json={"user_id": st.session_state.user_id, "message": user_message},
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                bot_response = data.get("response", "🤖 Sorry, no response from bot.")
            else:
                bot_response = "🤖 Backend error. Please try again."
        except requests.exceptions.RequestException:
            bot_response = "⚠️ Backend not reachable. Please try again later."

        st.session_state.chat_history.append({"sender": "bot", "message": bot_response})
        st.session_state.user_input = ""

    # ---- Render chat history ----
    for idx, chat in enumerate(st.session_state.chat_history):
        is_user = chat["sender"] == "user"
        alignment = "right" if is_user else "left"
        bg_color = "#DCF8C6" if is_user else "#E2E2E2"

        st.markdown(
            f"""
            <div style="text-align:{alignment}; margin:8px 0;">
                <span style="
                    background-color:{bg_color};
                    padding:10px 14px;
                    border-radius:12px;
                    display:inline-block;
                    max-width:70%;
                    word-wrap: break-word;
                    font-size:14px;
                ">
                    {chat['message']}
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

        if not is_user and idx not in st.session_state.feedback_submitted:
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("👍", key=f"up_{idx}"):
                    try:
                        headers = {"Authorization": f"Bearer {st.session_state.token}"}
                        requests.post(
                            f"{API_URL}/feedback",
                            json={
                                "user_id": st.session_state.user_id,
                                "user_query": st.session_state.chat_history[idx-1]["message"] if idx > 0 else "",
                                "bot_response": chat["message"],
                                "feedback": "positive"
                            },
                            headers=headers
                        )
                        st.session_state.feedback_submitted[idx] = True
                        st.toast("Feedback submitted", icon="✅")
                    except:
                        st.error("Failed to submit feedback.")

            with col2:
                if st.button("👎", key=f"down_{idx}"):
                    try:
                        headers = {"Authorization": f"Bearer {st.session_state.token}"}
                        requests.post(
                            f"{API_URL}/feedback",
                            json={
                                "user_id": st.session_state.user_id,
                                "user_query": st.session_state.chat_history[idx-1]["message"] if idx > 0 else "",
                                "bot_response": chat["message"],
                                "feedback": "negative"
                            },
                            headers=headers
                        )
                        st.session_state.feedback_submitted[idx] = True
                        st.toast("Feedback submitted", icon="✅")
                    except:
                        st.error("Failed to submit feedback.")

    st.text_input(
        "Type your message here...",
        key="user_input",
        on_change=send_message
    )

    if st.button("Send"):
        send_message()
