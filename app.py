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
    try:
        return f"{int(val):,}".replace(",", ".")
    except:
        return "0"

def fmt_dec(val):
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

    # --- 3. CLOUD DATENBANK-ANSCHLUSS ---
    conn = st.connection("db", type="sql")

    with conn.session as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS fitness_data (
                id SERIAL PRIMARY KEY,
                "Datum" TEXT, "Uhrzeit" TEXT, "Gewicht" REAL, "Schritte" INTEGER, 
                "Aktivzeit" INTEGER, "Kalorien_In" INTEGER, "Kalorien_Out" INTEGER, 
                "Hals" REAL, "Brust" REAL, "Bauch" REAL, "Oberschenkel" REAL, 
                "Aktivitaet" TEXT, "Bemerkung" TEXT,
                "Eiweiss" INTEGER DEFAULT 0,
                "Wasser_Menge" INTEGER DEFAULT 0,
                "Koerperfett" REAL DEFAULT 0.0,
                "Muskelmasse" REAL DEFAULT 0.0,
                "Koerperwasser" REAL DEFAULT 0.0
            )
        """))
        try:
            session.execute(text('ALTER TABLE fitness_data ADD COLUMN "Koerperwasser" REAL DEFAULT 0.0'))
            session.commit()
        except: pass
        try:
            session.execute(text('ALTER TABLE fitness_data ADD COLUMN "Muskelmasse" REAL DEFAULT 0.0'))
            session.commit()
        except: pass
        
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS user_settings (
                "key" TEXT PRIMARY KEY, value TEXT
            )
        """))
        session.commit()

    def load_fitness_data():
        cols = ['Datum', 'Uhrzeit', 'Gewicht', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Aktivitaet', 'Bemerkung', 'Eiweiss', 'Wasser_Menge', 'Koerperfett', 'Muskelmasse', 'Koerperwasser']
        try:
            df_sql = conn.query("SELECT * FROM fitness_data", ttl=0)
            if df_sql.empty:
                return pd.DataFrame(columns=cols)
            
            df_sql.columns = [c.lower() for c in df_sql.columns]
            
            df_sql = df_sql.rename(columns={
                'datum': 'Datum', 'uhrzeit': 'Uhrzeit', 'gewicht': 'Gewicht', 
                'schritte': 'Schritte', 'aktivzeit': 'Aktivzeit', 'kalorien_in': 'Kalorien_In', 
                'kalorien_out': 'Kalorien_Out', 'hals': 'Hals', 'brust': 'Brust', 
                'bauch': 'Bauch', 'oberschenkel': 'Oberschenkel', 'aktivitaet': 'Aktivitaet', 
                'bemerkung': 'Bemerkung', 'eiweiss': 'Eiweiss', 'wasser_menge': 'Wasser_Menge', 
                'koerperfett': 'Koerperfett', 'muskelmasse': 'Muskelmasse', 'koerperwasser': 'Koerperwasser'
            })
            
            df_sql['Datum'] = pd.to_datetime(df_sql['Datum'])
            if 'id' in df_sql.columns: 
                df_sql = df_sql.drop(columns=['id'])
            
            for c in ['Eiweiss', 'Wasser_Menge', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out']:
                if c in df_sql.columns: df_sql[c] = df_sql[c].fillna(0).astype(int)
            for c in ['Koerperfett', 'Muskelmasse', 'Koerperwasser', 'Gewicht', 'Hals', 'Brust', 'Bauch', 'Oberschenkel']:
                if c in df_sql.columns: df_sql[c] = df_sql[c].fillna(0.0).astype(float)
            
            return df_sql
        except:
            return pd.DataFrame(columns=cols)

    def load_settings():
        default_settings = {"email": "florian.pohn@protonmail.com", "reminder_active": "False", "weight_daily": "True", "measures_day": "Donnerstag", "height": "179", "target_weight": "75.0", "birthday": "1990-01-01", "last_email_kw": "0"}
        try:
            df_set = conn.query('SELECT "key", value FROM user_settings', ttl=0)
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
                session.execute(text('INSERT INTO user_settings ("key", value) VALUES (:k, :v) ON CONFLICT ("key") DO UPDATE SET value = EXCLUDED.value'), {"k": k, "v": str(v)})
            session.commit()

    df = load_fitness_data()
    settings = load_settings()

    settings["height"] = int(settings.get("height", 179))
    settings["target_weight"] = float(settings.get("target_weight", 75.0))
    settings["reminder_active"] = settings.get("reminder_active") == "True"
    settings["last_email_kw"] = int(settings.get("last_email_kw", 0))

    df_filled = df.sort_values(['Datum', 'Uhrzeit']).copy() if (not df.empty and 'Datum' in df.columns and 'Uhrzeit' in df.columns) else df.copy()
    if not df.empty and 'Datum' in df_filled.columns:
        cols_to_fill = ['Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Gewicht', 'Koerperfett', 'Muskelmasse', 'Koerperwasser']
        for col in cols_to_fill:
            if col in df_filled.columns:
                df_filled[col] = df_filled[col].replace(0, pd.NA)
                df_filled[col] = df_filled[col].ffill().fillna(0)

    # --- EMAIL LOGIK ---
    if settings.get("reminder_active", False) and not df_filled.empty and 'Bauch' in df_filled.columns:
        wochentage_dict = {"Montag": 0, "Dienstag": 1, "Mittwoch": 2, "Donnerstag": 3, "Freitag": 4, "Samstag": 5, "Sonntag": 6}
        ziel_wochentag = wochentage_dict.get(settings.get("measures_day", "Donnerstag"), 3)
        heute = date.today()
        aktuelle_kw = heute.isocalendar()[1]
        
        if heute.weekday() == ziel_wochentag and settings["last_email_kw"] != aktuelle_kw:
            latest_mail_row = df_filled.iloc[-1]
            mail_text = f"Hallo Florian!\n\nHier ist deine wöchentliche Erinnerung vom My Fitness Hub.\n\n"
            mail_text += f"Aktueller Stand deiner letzten Messungen:\n"
            mail_text += f"- Gewicht: {latest_mail_row['Gewicht']:.1f} kg\n"
            mail_text += f"- Bauchumfang: {latest_mail_row['Bauch']:.1f} cm\n"
            mail_text += f"- Brustumfang: {latest_mail_row['Brust']:.1f} cm\n"
            mail_text += f"- Halsumfang: {latest_mail_row['Hals']:.1f} cm\n"
            mail_text += f"- Oberschenkel: {latest_mail_row['Oberschenkel']:.1f}
