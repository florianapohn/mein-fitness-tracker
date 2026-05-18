# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import text
import numpy as np
try:
    from sklearn.linear_model import LinearRegression
    sklearn_available = True
except:
    sklearn_available = False

# --- FUNCTION: GERMAN NUMBER FORMATTING ---
def fmt_int(val):
    """Format_int: 75784 -> 75.784"""
    try:
        return f"{int(val):,}".replace(",", ".")
    except:
        return "0"

def fmt_dec(val):
    """Format_dec: 93.1 -> 93,1"""
    try:
        return f"{float(val):.1f}".replace(".", ",")
    except:
        return "0,0"

# --- FUNCTION: EMAIL SENDING ---
def send_reminder_email(to_email, subject, body_text):
    try:
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]
        sender_email = st.secrets["email"]["sender_email"]
        sender_password = st.secrets["email"]["sender_password"]
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.sidebar.error(f"E-Mail Fehler: {e}")
        return False

# --- 1. LOGIN SYSTEM ---
def check_password():
    def password_entered():
        correct_username = st.secrets["login"]["username"]
        correct_password = st.secrets["login"]["password"]
        if st.session_state["username"] == correct_username and st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Login zum Fitness Hub")
        st.text_input("Benutzername", key="username")
        st.text_input("Passwort", type="password", key="password")
        st.button("Anmelden", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔐 Login zum Fitness Hub")
        st.text_input("Benutzername", key="username")
        st.text_input("Passwort", type="password", key="password")
        st.button("Anmelden", on_click=password_entered)
        st.error("😕 Benutzername oder Passwort falsch")
        return False
    return True

if check_password():

    # --- 2. APP KONFIGURATION ---
    st.set_page_config(page_title="My Fitness Hub", layout="wide")
    st.title("My All-in-One Fitness Hub 🚀")

    # --- 3. DAUERHAFTER DATENBANK-ANSCHLUSS ---
    conn = st.connection("local_db", type="sql")

    with conn.session as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS fitness_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Datum TEXT, Uhrzeit TEXT, Gewicht REAL, Schritte INTEGER, 
                Aktivzeit INTEGER, Kalorien_In INTEGER, Kalorien_Out INTEGER, 
                Hals REAL, Brust REAL, Bauch REAL, Oberschenkel REAL, 
                Aktivitaet TEXT, Bemerkung TEXT,
                Eiweiss INTEGER DEFAULT 0,
                Wasser_Menge INTEGER DEFAULT 0,
                Koerperfett REAL DEFAULT 0.0,
                Muskelmasse REAL DEFAULT 0.0
            )
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS user_settings (
                key TEXT PRIMARY KEY, value TEXT
            )
        """))
        session.commit()

    def load_fitness_data():
        try:
            df_sql = conn.query("SELECT * FROM fitness_data", ttl=0)
            if df_sql.empty:
                columns = ['Datum', 'Uhrzeit', 'Gewicht', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Aktivitaet', 'Bemerkung', 'Eiweiss', 'Wasser_Menge', 'Koerperfett', 'Muskelmasse']
                return pd.DataFrame(columns=columns)
            df_sql['Datum'] = pd.to_datetime(df_sql['Datum'])
            if 'id' in df_sql.columns: df_sql = df_sql.drop(columns=['id'])
            
            if 'Eiweiss' in df_sql.columns: df_sql['Eiweiss'] = df_sql['Eiweiss'].fillna(0).astype(int)
            if 'Wasser_Menge' in df_sql.columns: df_sql['Wasser_Menge'] = df_sql['Wasser_Menge'].fillna(0).astype(int)
            if 'Koerperfett' in df_sql.columns: df_sql['Koerperfett'] = df_sql['Koerperfett'].fillna(0.0).astype(float)
            if 'Muskelmasse' in df_sql.columns: df_sql['Muskelmasse'] = df_sql['Muskelmasse'].fillna(0.0).astype(float)
            
            return df_sql
        except:
            return pd.DataFrame()

    def load_settings():
        default_settings = {"email": "florian.pohn@protonmail.com", "reminder_active": "False", "weight_daily": "True", "measures_day": "Donnerstag", "height": "179", "target_weight": "75.0", "birthday": "1990-01-01", "last_email_kw": "0"}
        try:
            df_set = conn.query("SELECT * FROM user_settings", ttl=0)
            if df_set.empty: return default_settings
            res = dict(zip(df_set['key'], df_set['value']))
            for k, v in default_settings.items():
                if k not in res: res[k] = v
            return res
        except:
            return default_settings

    def save_settings_to_db(s_dict):
        with conn.session as session:
            for k, v in s_dict.items():
                session.execute(text("INSERT OR REPLACE INTO user_settings (key, value) VALUES (:k, :v)"), {"k": k, "v": str(v)})
            session.commit()

    df = load_fitness_data()
    settings = load_settings()

    settings["height"] = int(settings.get("height", 179))
    settings["target_weight"] = float(settings.get("target_weight", 75.0))
    settings["reminder_active"] = settings.get("reminder_active") == "True"
    settings["last_email_kw"] = int(settings.get("last_email_kw", 0))

    df_filled = df.sort_values(['Datum', 'Uhrzeit']).copy() if not df.empty else pd.DataFrame()
    if not df.empty:
        cols_to_fill =
