import streamlit as st
import plotly.express as px
import pandas as pd
import sqlite3
import json
import os
import time

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))) 

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


KB_FOLDER = "../rasabot/kb"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
PALETTE = ["#A1E3C3", "#D7BDE2", "#F7DC6F", "#85C1E9", "#F1948A", "#73C6B6", "#F5B041"]

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/wellbot.db"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


def login_page():
    st.markdown("""
        <style>
        .stApp {
            background: radial-gradient(circle, #A7C7E7, #D7BDE2);
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h2 style='text-align:center'>WellBot Admin Login</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center'>Please log in to access the admin dashboard.</p>", unsafe_allow_html=True)

        with st.form("admin_login_form"):
            username = st.text_input("Username", placeholder="Enter username", key="admin_login_user")
            password = st.text_input("Password", type="password", placeholder="Enter password", key="admin_login_pass")
            submitted = st.form_submit_button("Login")
            if submitted:
                if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                    st.session_state["admin_logged_in"] = True
                    st.success("Login successful! Redirecting...")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")


def apply_dashboard_style():
    st.markdown("""
        <style>
        .stApp { background-color: #F9F6EE; }
        .metric-card {
            padding: 1rem;
            border-radius: 1rem;
            background-color: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)


def load_kb_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

def save_kb_file(file_path, data):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        st.error(f"Error saving file: {e}")


def init_kb_session_keys():
    keys_defaults = {
        "kb_new_id": "",
        "kb_new_keywords": "",
        "kb_new_en": "",
        "kb_new_hi": "",
        "kb_edit_id": "",
        "kb_edit_keywords": "",
        "kb_edit_en": "",
        "kb_edit_hi": "",
        "kb_del_id": "",
        "clear_kb_fields": False
    }
    for k, v in keys_defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def clear_kb_fields():
    st.session_state["clear_kb_fields"] = True
    st.rerun()


def dashboard_page():
    st.set_page_config(page_title="WellBot Admin Dashboard", layout="wide")
    init_kb_session_keys()
    apply_dashboard_style()

    st.title("WellBot Admin Dashboard")

    col1, col2 = st.columns([10, 1])
    with col2:
        if st.button("🚪 Logout"):
            st.session_state.admin_logged_in = False
            st.success("Logged out successfully. Returning to app...")
            st.rerun()

    if st.session_state.get("clear_kb_fields", False):
        st.session_state["kb_new_id"] = ""
        st.session_state["kb_new_keywords"] = ""
        st.session_state["kb_new_en"] = ""
        st.session_state["kb_new_hi"] = ""
        st.session_state["kb_edit_id"] = ""
        st.session_state["kb_edit_keywords"] = ""
        st.session_state["kb_edit_en"] = ""
        st.session_state["kb_edit_hi"] = ""
        st.session_state["kb_del_id"] = ""
        st.session_state["clear_kb_fields"] = False

    tabs = st.tabs([
        "📊 Dashboard",
        "📚 Knowledge Base",
        "💬 User Feedback",
        "👥 User Management"
    ])

    # Analytics
    with tabs[0]:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            #Total users
            cursor.execute("SELECT COUNT(*) FROM users;")
            total_users = cursor.fetchone()[0]

            #Total queries
            cursor.execute("SELECT COUNT(*) FROM chat_history;")
            total_queries = cursor.fetchone()[0]

            #Positive feedback%
            cursor.execute("SELECT COUNT(*) FROM feedback WHERE feedback='positive';")
            positive_count = cursor.fetchone()[0]
            positive_feedback_pct = round((positive_count / total_queries) * 100, 1) if total_queries else 0

            #Queries per day
            df_queries = pd.read_sql_query("""
                SELECT DATE(timestamp) AS day, COUNT(*) AS Queries
                FROM chat_history
                GROUP BY day
                ORDER BY day;
            """, conn)

            #Intent distribution
            df_intents = pd.read_sql_query("""
                SELECT intent AS Intent, COUNT(*) AS Count
                FROM chat_history
                GROUP BY intent
                ORDER BY Count DESC;
            """, conn)
            
            #Gender distribution
            df_gender = pd.read_sql_query("""
                SELECT gender AS Gender, COUNT(*) AS Count
                FROM profiles
                WHERE gender IS NOT NULL
                GROUP BY gender;
            """, conn)

            #Language preference
            df_lang = pd.read_sql_query("""
                SELECT language AS Language, COUNT(*) AS Count
                FROM profiles
                WHERE language IS NOT NULL
                GROUP BY language;
            """, conn)

            conn.close()
        except Exception as e:
            st.error(f"Database error: {e}")
            total_users, total_queries, positive_feedback_pct = 0, 0, 0
            df_queries = pd.DataFrame(columns=["day", "Queries"])
            df_intents = pd.DataFrame(columns=["Intent", "Count"])
            df_gender = pd.DataFrame(columns=["Gender", "Count"])
            df_lang = pd.DataFrame(columns=["Language", "Count"])

        # ---- Metrics ----
        st.markdown("### Overview")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='metric-card'><h3>👥 {total_users}</h3><p>Total Users</p></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><h3>💬 {total_queries}</h3><p>Total Queries</p></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='metric-card'><h3>👍 {positive_feedback_pct}%</h3><p>Positive Feedback</p></div>", unsafe_allow_html=True)

        st.markdown("---")
        
        # ---- Plots ----
        col1, col2 = st.columns(2)
        with col1:
            if not df_queries.empty:
                fig1 = px.line(
                    df_queries,
                    x="day",
                    y="Queries",
                    title="Queries per Day",
                    markers=True,
                    color_discrete_sequence=["#FF5733"]
                )
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("No query data available.")
        
        with col2:
            if not df_intents.empty:
                fig2 = px.pie(df_intents, names="Intent", values="Count", title="Intent Distribution",
                            color_discrete_sequence=PALETTE)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No intent data available.")
        
        st.markdown("---")

        st.subheader("User Demographics")
        col1, col2 = st.columns(2)

        #Gender Distribution
        with col1:
            if not df_gender.empty:
                fig_gender = px.pie(
                    df_gender,
                    names="Gender",
                    values="Count",
                    hole=0.5,
                    title="Gender Distribution",
                    color_discrete_sequence=["#E47BC6", "#669DDB"]
                )
                st.plotly_chart(fig_gender, use_container_width=True)
            else:
                st.info("No gender data available.")
        
        with col2:
            if not df_lang.empty:
                fig_lang = px.bar(
                    df_lang,
                    x="Count",
                    y="Language",
                    orientation="h",
                    title="Language Preference",
                    text_auto=True,
                    color="Language",
                    color_discrete_sequence=["#F1948A", "#73C6B6"]
                )
                st.plotly_chart(fig_lang, use_container_width=True)
            else:
                st.info("No language data available.")


    # KB Management
    with tabs[1]:
        st.subheader("📚 Manage Knowledge Base (KB)")

        try:
            kb_files = [f for f in os.listdir(KB_FOLDER) if f.endswith(".json")]
        except Exception:
            kb_files = []
        selected_file = st.selectbox("Select a KB File", kb_files)

        if not selected_file:
            st.info("No KB file selected.")
        else:
            file_path = os.path.join(KB_FOLDER, selected_file)
            kb_data = load_kb_file(file_path)
            if not kb_data or "entries" not in kb_data:
                st.warning("Invalid KB file structure.")
            else:
                st.write(f"### Intent: {kb_data.get('intent','Unknown')}")
                df_entries = pd.DataFrame(kb_data["entries"])

                search_term = st.text_input("🔍 Search KB Entries (ID, keyword, English/Hindi)", key="kb_search")
                if search_term:
                    df_filtered = df_entries[
                        df_entries.apply(lambda r:
                            search_term.lower() in str(r["id"]).lower()
                            or any(search_term.lower() in k.lower() for k in r.get("keywords", []))
                            or search_term.lower() in str(r.get("en", "")).lower()
                            or search_term.lower() in str(r.get("hi", "")).lower()
                        , axis=1)
                    ]
                else:
                    df_filtered = df_entries
                st.dataframe(df_filtered, use_container_width=True)

                st.markdown("---")
                st.subheader("➕ Add New Entry")
                col1, col2 = st.columns(2)
                with col1:
                    new_id = st.text_input("ID (unique, new)", value=st.session_state["kb_new_id"], key="kb_new_id")
                    new_keywords = st.text_area("Keywords (comma separated)", value=st.session_state["kb_new_keywords"], key="kb_new_keywords")
                with col2:
                    new_en = st.text_area("Answer (English)", value=st.session_state["kb_new_en"], key="kb_new_en", height=150)
                    new_hi = st.text_area("Answer (Hindi)", value=st.session_state["kb_new_hi"], key="kb_new_hi", height=150)

                if st.button("💾 Add Entry"):
                    if not new_id.strip():
                        st.warning("Enter a valid ID.")
                    elif any(e["id"] == new_id.strip() for e in kb_data["entries"]):
                        st.warning("ID already exists! Use Edit instead.")
                    else:
                        kb_data["entries"].append({
                            "id": new_id.strip(),
                            "keywords": [k.strip() for k in new_keywords.split(",") if k.strip()],
                            "en": new_en.strip(),
                            "hi": new_hi.strip()
                        })
                        save_kb_file(file_path, kb_data)
                        msg_placeholder = st.empty()
                        msg_placeholder.success("✅ Entry added successfully!")
                        time.sleep(2)
                        msg_placeholder.empty()
                        clear_kb_fields()

                st.markdown("---")
                st.subheader("✏️ Edit Existing Entry")
                edit_id = st.text_input("Enter existing ID to edit", value=st.session_state["kb_edit_id"], key="kb_edit_id")
                existing = next((e for e in kb_data["entries"] if e["id"] == edit_id.strip()), None)
                if existing:
                    if st.session_state.get("kb_edit_keywords", "") == "" and existing.get("keywords"):
                        st.session_state["kb_edit_keywords"] = ", ".join(existing.get("keywords", []))
                    if st.session_state.get("kb_edit_en", "") == "" and existing.get("en", ""):
                        st.session_state["kb_edit_en"] = existing.get("en", "")
                    if st.session_state.get("kb_edit_hi", "") == "" and existing.get("hi", ""):
                        st.session_state["kb_edit_hi"] = existing.get("hi", "")

                    col1, col2 = st.columns(2)
                    with col1:
                        edit_keywords = st.text_area("Keywords", value=st.session_state["kb_edit_keywords"], key="kb_edit_keywords")
                    with col2:
                        edit_en = st.text_area("Answer (English)", value=st.session_state["kb_edit_en"], key="kb_edit_en", height=150)
                        edit_hi = st.text_area("Answer (Hindi)", value=st.session_state["kb_edit_hi"], key="kb_edit_hi", height=150)

                    if st.button("💾 Update Entry"):
                        idx = kb_data["entries"].index(existing)
                        kb_data["entries"][idx] = {
                            "id": edit_id.strip(),
                            "keywords": [k.strip() for k in edit_keywords.split(",") if k.strip()],
                            "en": edit_en.strip(),
                            "hi": edit_hi.strip()
                        }
                        save_kb_file(file_path, kb_data)
                        msg_placeholder = st.empty()
                        msg_placeholder.success("✅ Entry updated successfully!")
                        time.sleep(2)
                        msg_placeholder.empty()
                        clear_kb_fields()
                elif edit_id.strip():
                    st.info("ID not found.")

                st.markdown("---")
                st.subheader("🗑️ Delete Entry")
                del_id = st.text_input("Enter ID to delete", value=st.session_state["kb_del_id"], key="kb_del_id")
                if st.button("Delete Entry"):
                    existing_del = next((e for e in kb_data["entries"] if e["id"] == del_id.strip()), None)
                    if existing_del:
                        kb_data["entries"] = [e for e in kb_data["entries"] if e["id"] != del_id.strip()]
                        save_kb_file(file_path, kb_data)
                        msg_placeholder = st.empty()
                        msg_placeholder.success("✅ Entry deleted successfully!")
                        time.sleep(2)
                        msg_placeholder.empty()
                        clear_kb_fields()
                    else:
                        st.warning("ID not found to delete.")


    # Feedback
    with tabs[2]:
        st.subheader("💬 User Feedback")

        try:
            conn = sqlite3.connect(DB_PATH)
            df_feedback = pd.read_sql_query("""
                SELECT f.id, u.name AS user_name, f.user_query AS query, f.bot_response, f.feedback, f.timestamp
                FROM feedback f
                LEFT JOIN users u ON f.user_id = u.id
                ORDER BY f.timestamp DESC;
            """, conn)
            conn.close()

            if df_feedback.empty:
                st.info("✅ No feedback available yet.")
            else:
                st.dataframe(
                    df_feedback[["id", "user_name", "query", "bot_response", "feedback", "timestamp"]],
                    use_container_width=True
                )

                st.download_button(
                    label="⬇️ Export Feedback to CSV",
                    data=df_feedback.to_csv(index=False).encode("utf-8"),
                    file_name="user_feedback.csv",
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"Database error: {e}")


    with tabs[3]:
        st.subheader("👥 User Management")

        from sqlalchemy.orm import Session
        from backend.models import User, Profile, ChatHistory
        from backend.db import SessionLocal
        from werkzeug.security import generate_password_hash

        db = SessionLocal()
        try:
            users_profiles = db.query(User, Profile).outerjoin(Profile, User.id == Profile.user_id).all()
        except Exception as e:
            st.error(f"Database error: {e}")
            users_profiles = []
        finally:
            db.close()

        data = []
        for u, p in users_profiles:
            data.append({
                "ID": u.id,
                "Name": u.name,
                "Email": u.email,
                "Age Group": p.age_group if p else "",
                "Gender": p.gender if p else "",
                "Language": p.language if p else ""
            })

        st.dataframe(data, use_container_width=True)

        st.markdown("---")
        st.subheader("➕ Add New User")
        with st.form("add_user_form"):
            new_name = st.text_input("Name")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            age_options = ["Select Age Group", "Below 18", "18-25", "26-35", "36-45", "46-60", "Above 60"]
            new_age_group = st.selectbox("Age Group", age_options)
            new_gender = st.selectbox("Gender", ["Select Gender", "Male", "Female", "Other"])
            new_language = st.selectbox("Language", ["English", "Hindi"])
            submitted = st.form_submit_button("Add User")

            if submitted:
                if not new_name.strip() or not new_email.strip() or not new_password.strip() or new_age_group == "Select Age Group":
                    st.warning("Please fill all required fields.")
                else:
                    db = SessionLocal()
                    try:
                        hashed_pw = generate_password_hash(new_password)
                        user_obj = User(name=new_name.strip(), email=new_email.strip(), password=hashed_pw)
                        db.add(user_obj)
                        db.commit()
                        db.refresh(user_obj)
                        profile_obj = Profile(user_id=user_obj.id, age_group=new_age_group, gender=new_gender, language=new_language)
                        db.add(profile_obj)
                        db.commit()
                        st.success("✅ User added successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding user: {e}")
                        db.rollback()
                    finally:
                        db.close()

        st.markdown("---")
        st.subheader("✏️ Edit User")
        if users_profiles:
            user_options = [(f"{u.name} ({u.id})", u.id) for u, _ in users_profiles]
            user_dropdown_options = ["Select a User"] + [opt[0] for opt in user_options]
            selected_user_display = st.selectbox("Select User to Edit", user_dropdown_options, key="edit_user_select")

            if selected_user_display != "Select a User":
                selected_user_id = dict(user_options)[selected_user_display]

                db = SessionLocal()
                try:
                    user_obj = db.query(User).filter(User.id == selected_user_id).first()
                    profile_obj = db.query(Profile).filter(Profile.user_id == selected_user_id).first()
                finally:
                    db.close()

                if user_obj:
                    with st.form("edit_user_form"):
                        edit_name = st.text_input("Name", value=user_obj.name)
                        edit_email = st.text_input("Email", value=user_obj.email)
                        edit_password = st.text_input("Password (leave blank to keep)", type="password")

                        age_options = ["Select Age Group", "Below 18", "18-25", "26-35", "36-45", "46-60", "Above 60"]
                        gender_options = ["Male", "Female", "Other"]
                        language_options = ["English", "Hindi"]

                        edit_age_group_index = age_options.index(profile_obj.age_group) if profile_obj and profile_obj.age_group in age_options else 0
                        edit_gender_index = gender_options.index(profile_obj.gender) if profile_obj and profile_obj.gender in gender_options else 0
                        lang_clean = profile_obj.language.strip().capitalize() if profile_obj and profile_obj.language else ""
                        edit_language_index = language_options.index(lang_clean) if lang_clean in language_options else 0

                        edit_age_group = st.selectbox("Age Group", age_options, index=edit_age_group_index)
                        edit_gender = st.selectbox("Gender", gender_options, index=edit_gender_index)
                        edit_language = st.selectbox("Language", language_options, index=edit_language_index)

                        update_submitted = st.form_submit_button("Update User")

                        if update_submitted:
                            db = SessionLocal()
                            try:
                                user_obj.name = edit_name.strip()
                                user_obj.email = edit_email.strip()
                                if edit_password.strip():
                                    user_obj.password = generate_password_hash(edit_password.strip())
                                db.add(user_obj)

                                if profile_obj:
                                    profile_obj.age_group = edit_age_group
                                    profile_obj.gender = edit_gender
                                    profile_obj.language = edit_language
                                    db.add(profile_obj)
                                else:
                                    profile_obj = Profile(
                                        user_id=user_obj.id,
                                        age_group=edit_age_group,
                                        gender=edit_gender,
                                        language=edit_language
                                    )
                                    db.add(profile_obj)

                                db.commit()
                                st.success("✅ User updated successfully!")
                                st.rerun()
                            except Exception as e:
                                db.rollback()
                                st.error(f"Error updating user: {e}")
                            finally:
                                db.close()
        # Delete user
        st.markdown("---")
        st.subheader("🗑️ Delete User")
        if users_profiles:
            delete_dropdown_options = ["Select a User"] + [opt[0] for opt in user_options]
            selected_user_delete = st.selectbox("Select User to Delete", delete_dropdown_options, key="delete_user_select")
            if selected_user_delete != "Select a User":
                selected_user_id = dict(user_options)[selected_user_delete]
                if st.button("Delete User"):
                    db = SessionLocal()
                    try:
                        user_obj = db.query(User).filter(User.id == selected_user_id).first()
                        profile_obj = db.query(Profile).filter(Profile.user_id == selected_user_id).first()
                        if profile_obj:
                            db.delete(profile_obj)
                        if user_obj:
                            db.delete(user_obj)
                        db.commit()
                        st.success("✅ User deleted successfully!")
                        st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"Error deleting user: {e}")
                    finally:
                        db.close()

        st.markdown("---")
        st.subheader("💬 Chat History per User")
        if users_profiles:
            chat_dropdown_options = ["Select a User"] + [opt[0] for opt in user_options]
            selected_user_display = st.selectbox("Select User to View Chat", chat_dropdown_options)

            if selected_user_display != "Select a User":
                selected_user_id = dict(user_options)[selected_user_display]

                db = SessionLocal()
                try:
                    chats = db.query(ChatHistory).filter(ChatHistory.user_id == selected_user_id).order_by(ChatHistory.timestamp).all()
                finally:
                    db.close()

                if chats:
                    for chat in chats:
                        st.markdown(f"**User:** {chat.query}")
                        st.markdown(f"**Bot:** {chat.response}")
                        st.markdown("---")
                else:
                    st.info("No chat history for this user.")
