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
        cols_to_fill = ['Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Gewicht', 'Koerperfett', 'Muskelmasse']
        for col in cols_to_fill:
            df_filled[col] = df_filled[col].replace(0, pd.NA)
            df_filled[col] = df_filled[col].ffill().fillna(0)

    # --- EMAIL LOGIK ---
    if settings.get("reminder_active", False) and not df_filled.empty:
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
            mail_text += f"- Oberschenkel: {latest_mail_row['Oberschenkel']:.1f} cm\n"
            mail_text += "\nBleib dran! 🏆"
            
            if send_reminder_email(settings.get("email"), "My Fitness Hub - Wöchentlicher Check-In", mail_text):
                settings["last_email_kw"] = aktuelle_kw
                save_settings_to_db(settings)
                st.sidebar.success("📧 Erinnerungs-Mail gesendet!")

    # --- 4. SEITENLEISTE: DATENEINGABE ---
    st.sidebar.header(f"Hallo Florian!")
    with st.sidebar.form("entry_form", clear_on_submit=True):
        d = st.date_input("Datum auswählen", date.today())
        sport_options = ["Kein Sport", "Gehen", "Fahrrad", "Schwimmen", "Krafttraining"]
        act_type = st.select_slider("Welchen Sport hast du heute gemacht?", options=sport_options, value="Gehen")
        c_in1, c_in2 = st.columns(2)
        with c_in1:
            gew = st.number_input("Gewicht (kg)", format="%.1f", min_value=0.0)
            step = st.number_input("Schritte", step=100, min_value=0)
        with c_in2:
            k_in = st.number_input("Kalorien (In)", step=50, min_value=0)
            k_out = st.number_input("Kalorien (Out)", step=50, min_value=0)
        akt_min = st.number_input("Dauer (Minuten)", step=5, min_value=0)
        note = st.text_input("📝 Bemerkung", placeholder="Urlaub, Krank, Feier...")
        
        st.subheader("📏 Körpermaße (cm)")
        h1, h2 = st.columns(2)
        hals_in = h1.number_input("Hals", format="%.1f", value=0.0)
        brust_in = h2.number_input("Brust", format="%.1f", value=0.0)
        bauch_in = h1.number_input("Bauch", format="%.1f", value=0.0)
        bein_in = h2.number_input("Oberschenkel", format="%.1f", value=0.0)
        
        st.subheader("📊 Ernährung & Tracking")
        in_eiweiss = st.number_input("🍗 Eiweiß am Tag (Gramm aus FatSecret)", step=5, min_value=0)
        in_wasser = st.number_input("💧 Flüssigkeit am Tag (Gläser / Flaschen)", step=1, min_value=0)
        
        submit = st.form_submit_button("Speichern ✨")

    if submit:
        now_t = datetime.now().strftime("%H:%M")
        with conn.session as session:
            session.execute(text("""
                INSERT INTO fitness_data (Datum, Uhrzeit, Gewicht, Schritte, Aktivzeit, Kalorien_In, Kalorien_Out, Hals, Brust, Bauch, Oberschenkel, Aktivitaet, Bemerkung, Eiweiss, Wasser_Menge, Koerperfett, Muskelmasse)
                VALUES (:Datum, :Uhrzeit, :Gewicht, :Schritte, :Aktivzeit, :Kalorien_In, :Kalorien_Out, :Hals, :Brust, :Bauch, :Oberschenkel, :Aktivitaet, :Bemerkung, :Eiweiss, :Wasser_Menge, 0.0, 0.0)
            """), {
                "Datum": d.strftime("%Y-%m-%d"), "Uhrzeit": now_t, "Gewicht": gew, "Schritte": step, 
                "Aktivzeit": akt_min, "Kalorien_In": k_in, "Kalorien_Out": k_out, "Hals": hals_in, 
                "Brust": brust_in, "Bauch": bauch_in, "Oberschenkel": bein_in, "Aktivitaet": act_type, 
                "Bemerkung": note, "Eiweiss": in_eiweiss, "Wasser_Menge": in_wasser
            })
            session.commit()
        st.rerun()

    # --- 5. SEITENLEISTE: EINSTELLUNGEN ---
    st.sidebar.markdown("---")
    with st.sidebar.expander("⚙️ Profil & Zielgewicht"):
        new_h = st.number_input("Größe (cm)", value=settings["height"], step=1)
        try: stored_bday = datetime.strptime(str(settings.get("birthday", "1990-01-01")), "%Y-%m-%d").date()
        except: stored_bday = date(1990, 1, 1)
        new_bday = st.date_input("Geburtsdatum", value=stored_bday, min_value=date(1920, 1, 1), max_value=date.today())
        new_target = st.number_input("Zielgewicht (kg)", value=settings["target_weight"], format="%.1f", step=0.1)
        new_mail = st.text_input("E-Mail", value=settings.get("email", "florian.pohn@protonmail.com"))
        new_active = st.checkbox("E-Mail Aktiv", value=settings["reminder_active"])
        days = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        try: day_idx = days.index(settings.get("measures_day", "Donnerstag"))
        except: day_idx = 3
        new_day = st.selectbox("Tag für Maße-Erinnerung", days, index=day_idx)
        
        if st.button("Speichern 💾"):
            updated_settings = {"email": new_mail, "reminder_active": new_active, "height": new_h, "measures_day": new_day, "weight_daily": "True", "target_weight": new_target, "birthday": new_bday.strftime("%Y-%m-%d"), "last_email_kw": settings["last_email_kw"]}
            save_settings_to_db(updated_settings)
            st.success("Einstellungen gespeichert! ✅")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("🚀 Erfolge teilen")
    if not df.empty:
        latest_all_f = df_filled.iloc[-1]
        h_m_f = float(settings["height"]) / 100
        bmi_val_f = float(latest_all_f['Gewicht']) / (h_m_f ** 2) if latest_all_f['Gewicht'] > 0 else 0.0
        last_7_f = df[df['Datum'] > (pd.Timestamp.now() - pd.Timedelta(days=7))]
        s_steps_f = last_7_f['Schritte'].sum() if 'Schritte' in last_7_f.columns else 0
        s_kcal_f = last_7_f['Kalorien_Out'].sum() if 'Kalorien_Out' in last_7_f.columns else 0
        s_km_f = s_steps_f / 1400
        if st.sidebar.button("Erfolg kopieren 📋"):
            st.sidebar.code(f"Hey, schau mal! 🏆\nGewicht: {fmt_dec(latest_all_f['Gewicht'])} kg\nBMI: {fmt_dec(bmi_val_f)}\n\nLetzte 7 Tage:\n🔥 {fmt_int(s_kcal_f)} kcal\n🏃‍♂️ {fmt_dec(s_km_f)} km\n👣 {fmt_int(s_steps_f)} Schritte", language="text")

    if st.sidebar.button("Logout 🚪"):
        st.session_state.clear()
        st.rerun()

    # --- 6. HAUPTBEREICH ---
    tab1, tab2, tab3 = st.tabs(["Kurven & Trends 📈", "Langzeit-Statistik 📊", "Datentabelle 📋"])

    with tab1:
        if not df_filled.empty:
            ten_days_ago = pd.Timestamp.now() - pd.Timedelta(days=10)
            
            df_daily = df_filled.groupby('Datum').agg({
                'Kalorien_In': 'sum', 'Kalorien_Out': 'sum', 'Schritte': 'sum', 'Gewicht': 'last', 
                'Hals': 'last', 'Brust': 'last', 'Bauch': 'last', 'Oberschenkel': 'last',
                'Eiweiss': 'sum', 'Wasser_Menge': 'sum', 'Koerperfett': 'last', 'Muskelmasse': 'last'
            }).reset_index()
            
            df_p = df_daily[df_daily['Datum'] >= ten_days_ago].sort_values('Datum')
            if df_p.empty: df_p = df_daily.tail(10)
            
            latest = df_p.iloc[-1]
            h_m = float(settings["height"]) / 100
            bmi_val = float(latest['Gewicht']) / (h_m ** 2) if latest['Gewicht'] > 0 else 0.0
            bmi_cat = "Normalgewicht" if 18.5 <= bmi_val < 25 else "Übergewicht" if 25 <= bmi_val < 30 else "Adipositas" if bmi_val >= 30 else "Untergewicht"
            limit_kcal = 2300
            target_w = float(settings["target_weight"])
            
            st.subheader("⚖️ Gewichtsanalyse & KI-Prognose")
            col_w_metric, col_w_graph = st.columns([0.25, 0.75])
            
            prognose_text = "Nicht genügend Wiege-Daten für KI-Prognose."
            fig_w = go.Figure()
            fig_w.add_trace(go.Scatter(x=df_p['Datum'], y=df_p['Gewicht'], fill='tozeroy', mode='lines+markers', name="Gewicht (Real)", line=dict(width=3, color='#0288D1', shape='spline')))
            
            df_w_valid = df_daily[df_daily['Gewicht'] > 0.1].copy()
            if sklearn_available and len(df_w_valid) >= 3:
                try:
                    first_date = df_w_valid['Datum'].min()
                    df_w_valid['Tage'] = (df_w_valid['Datum'] - first_date).dt.days
                    X = df_w_valid[['Tage']].values
                    y = df_w_valid['Gewicht'].values
                    
                    model = LinearRegression()
                    model.fit(X, y)
                    
                    future_days = 28
                    last_tag = df_w_valid['Tage'].max()
                    future_x = np.array([[last_tag], [last_tag + future_days]])
                    future_y = model.predict(future_x)
                    future_dates = [df_w_valid['Datum'].max(), df_w_valid['Datum'].max() + timedelta(days=future_days)]
                    
                    fig_w.add_trace(go.Scatter(x=future_dates, y=future_y, mode='lines', name="KI Trend (4 Wochen)", line=dict(dash='dash', color='magenta', width=3)))
                    steigung = model.coef_[0]
                    achsenabschnitt = model.intercept_
                    if steigung < 0:
                        tage_bis_ziel = (target_w - achsenabschnitt) / steigung
                        ziel_datum = first_date + timedelta(days=int(tage_bis_ziel))
                        if ziel_datum > datetime.now():
                            prognose_text = f"🔮 **KI-Prognose:** Bei gleichbleibendem Trend erreichst du
