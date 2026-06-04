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

# --- DEUTSCHE ZAHLENFORMATIERUNG ---
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

# --- E-MAIL VERSAND FUNKTION ---
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

# --- LOGIN SYSTEM ---
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

    # --- APP KONFIGURATION ---
    st.set_page_config(page_title="My Fitness Hub", layout="wide")
    st.title("My All-in-One Fitness Hub 🚀")

    # --- CLOUD DATENBANK-ANSCHLUSS ---
    conn = st.connection("local_db", type="sql")

    with conn.session as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS fitness_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Datum TEXT, Uhrzeit TEXT, Gewicht REAL, Schritte INTEGER, 
                Aktivzeit INTEGER, Kalorien_In INTEGER, Kalorien_Out INTEGER, 
                Hals REAL, Brust REAL, Bauch REAL, Oberschenkel REAL, 
                Aktivitaet TEXT, Bemerkung TEXT,
                Eiweiss REAL DEFAULT 0.0,
                Wasser_Menge INTEGER DEFAULT 0,
                Koerperfett REAL DEFAULT 0.0,
                Muskelmasse REAL DEFAULT 0.0,
                Koerperwasser REAL DEFAULT 0.0
            )
        """))
        try:
            session.execute(text('ALTER TABLE fitness_data ADD COLUMN Eiweiss REAL DEFAULT 0.0'))
            session.commit()
        except: pass
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
                key TEXT PRIMARY KEY, value TEXT
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
            
            for c in ['Wasser_Menge', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out']:
                if c in df_sql.columns: df_sql[c] = df_sql[c].fillna(0).astype(int)
            for c in ['Eiweiss', 'Koerperfett', 'Muskelmasse', 'Koerperwasser', 'Gewicht', 'Hals', 'Brust', 'Bauch', 'Oberschenkel']:
                if c in df_sql.columns: df_sql[c] = df_sql[c].fillna(0.0).astype(float)
            
            return df_sql
        except:
            return pd.DataFrame(columns=cols)

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
        cols_to_fill = ['Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Gewicht', 'Koerperfett', 'Muskelmasse', 'Koerperwasser']
        for col in cols_to_fill:
            df_filled[col] = df_filled[col].replace(0, pd.NA)
            df_filled[col] = df_filled[col].ffill().fillna(0)

    # --- EMAIL LOGIK ---
    if "email" in st.secrets and settings.get("reminder_active", False) and not df_filled.empty:
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
        
        st.subheader("📊 Waagen-Analyse")
        wc1, wc2 = st.columns(2)
        gew = wc1.number_input("Gewicht (kg)", format="%.1f", min_value=0.0, value=None, placeholder="z.B. 75,2")
        in_fat = wc2.number_input("Körperfett (%)", format="%.1f", min_value=0.0, max_value=100.0, step=0.1, value=None, placeholder="z.B. 15,4")
        in_musc = wc1.number_input("Muskeln (kg)", format="%.1f", min_value=0.0, max_value=200.0, step=0.1, value=None, placeholder="z.B. 34,2")
        in_water = wc2.number_input("Körperwasser (%)", format="%.1f", min_value=0.0, max_value=100.0, step=0.1, value=None, placeholder="z.B. 55,1")
        
        st.subheader("🏃‍♂️ Aktivität")
        ac1, ac2 = st.columns(2)
        step = ac1.number_input("Schritte", step=100, min_value=0, value=None, placeholder="z.B. 10000")
        k_out = ac2.number_input("Kalorien (Out)", step=50, min_value=0, value=None, placeholder="z.B. 400")
        akt_min = st.number_input("Dauer (Minuten)", step=5, min_value=0, value=None, placeholder="z.B. 45")
        note = st.text_input("📝 Bemerkung", placeholder="Urlaub, Krank, Feier...")
        
        st.subheader("🍗 Ernährung & Tracking")
        ec1, ec2 = st.columns(2)
        k_in = ec1.number_input("Kalorien (In)", step=50, min_value=0, value=None, placeholder="z.B. 2100")
        in_eiweiss = ec2.number_input("Eiweiß am Tag (Gramm)", format="%.1f", min_value=0.0, value=None, placeholder="z.B. 112,5")
        in_wasser = st.number_input("Flüssigkeit am Tag (Gläser / Flaschen)", step=1, min_value=0, value=None, placeholder="z.B. 6")
        
        st.subheader("📏 Körpermaße (cm)")
        h1, h2 = st.columns(2)
        hals_in = h1.number_input("Hals", format="%.1f", value=None, placeholder="z.B. 38,0")
        brust_in = h2.number_input("Brust", format="%.1f", value=None, placeholder="z.B. 102,5")
        bauch_in = h1.number_input("Bauch", format="%.1f", value=None, placeholder="z.B. 88,0")
        bein_in = h2.number_input("Oberschenkel", format="%.1f", value=None, placeholder="z.B. 56,5")
        
        submit = st.form_submit_button("Speichern ✨")

    if submit:
        now_t = datetime.now().strftime("%H:%M")
        with conn.session as session:
            session.execute(text("""
                INSERT INTO fitness_data (Datum, Uhrzeit, Gewicht, Schritte, Aktivzeit, Kalorien_In, Kalorien_Out, Hals, Brust, Bauch, Oberschenkel, Aktivitaet, Bemerkung, Eiweiss, Wasser_Menge, Koerperfett, Muskelmasse, Koerperwasser)
                VALUES (:Datum, :Uhrzeit, :Gewicht, :Schritte, :Aktivzeit, :Kalorien_In, :Kalorien_Out, :Hals, :Brust, :Bauch, :Oberschenkel, :Aktivitaet, :Bemerkung, :Eiweiss, :Wasser_Menge, :Koerperfett, :Muskelmasse, :Koerperwasser)
            """), {
                "Datum": d.strftime("%Y-%m-%d"), "Uhrzeit": now_t, 
                "Gewicht": gew if gew is not None else 0.0, 
                "Schritte": step if step is not None else 0, 
                "Aktivzeit": akt_min if akt_min is not None else 0, 
                "Kalorien_In": k_in if k_in is not None else 0, 
                "Kalorien_Out": k_out if k_out is not None else 0, 
                "Hals": hals_in if hals_in is not None else 0.0, 
                "Brust": brust_in if brust_in is not None else 0.0, 
                "Bauch": bauch_in if bauch_in is not None else 0.0, 
                "Oberschenkel": bein_in if bein_in is not None else 0.0, 
                "Aktivitaet": act_type, "Bemerkung": note, 
                "Eiweiss": in_eiweiss if in_eiweiss is not None else 0.0, 
                "Wasser_Menge": in_wasser if in_wasser is not None else 0, 
                "Koerperfett": in_fat if in_fat is not None else 0.0, 
                "Muskelmasse": in_musc if in_musc is not None else 0.0, 
                "Koerperwasser": in_water if in_water is not None else 0.0
            })
            session.commit()
        st.session_state["active_tab"] = 0
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
        bmi_val_f = float(latest_all_f['Regular'] if 'Regular' in latest_all_f else latest_all_f['Gewicht']) / (h_m_f ** 2) if latest_all_f['Gewicht'] > 0 else 0.0
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
    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = 0

    tab1, tab2, tab3 = st.tabs(["Kurven & Trends 📈", "Langzeit-Statistik 📊", "Datentabelle 📋"])

    if st.session_state["active_tab"] == 0:
        current_tab = tab1
    elif st.session_state["active_tab"] == 1:
        current_tab = tab2
    else:
        current_tab = tab3

    with tab1:
        if not df_filled.empty:
            df_daily = df_filled.groupby('Datum').agg({
                'Kalorien_In': 'sum', 'Kalorien_Out': 'sum', 'Schritte': 'sum', 'Gewicht': 'last', 
                'Hals': 'last', 'Brust': 'last', 'Bauch': 'last', 'Oberschenkel': 'last',
                'Eiweiss': 'sum', 'Wasser_Menge': 'sum', 'Koerperfett': 'last', 'Muskelmasse': 'last', 'Koerperwasser': 'last'
            }).reset_index()
            
            min_datum_in_db = df_daily['Datum'].min()
            ten_days_ago = pd.Timestamp.now() - pd.Timedelta(days=10)
            if min_datum_in_db < ten_days_ago:
                df_p = df_daily.sort_values('Datum')
            else:
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
                            prognose_text = f"🔮 **KI-Prognose:** Bei gleichbleibendem Trend erreichst du dein Zielgewicht von {fmt_dec(target_w)} kg am **{ziel_datum.strftime('%d.%m.%Y')}**."
                        else:
                            prognose_text = "🔮 **KI-Prognose:** Du bist voll auf Kurs!"
                    elif steigung > 0:
                        prognose_text = "🔮 **KI-Prognose:** Das Gewicht steigt aktuell leicht an. Defizit prüfen! 📊"
                except:
                    prognose_text = "🔮 **KI-Prognose:** Berechnungsfehler. Füge mehr Daten hinzu."
            else:
                prognose_text = "🔮 **KI-Prognose:** Wird automatisch aktiv, sobald mindestens 3 Wiege-Einträge in der Tabelle stehen."
            
            with col_w_metric:
                st.metric("Aktuell", f"{fmt_dec(latest['Gewicht'])} kg", f"{fmt_dec(latest['Gewicht'] - target_w)} kg zum Ziel", delta_color="inverse")
                st.write("")
                st.markdown(prognose_text)
                
            with col_w_graph:
                fig_w.add_hline(y=target_w, line_dash="dash", line_color="red", annotation_text=f"Ziel {fmt_dec(target_w)}kg")
                fig_w.update_layout(height=300, margin=dict(l=0,r=0,t=20,b=0))
                st.plotly_chart(fig_w, use_container_width=True, config={'staticPlot': True})

            # --- GEWEBE-ANALYSE BEREICH ---
            st.markdown("---")
            st.subheader("🧬 Gewebe-Analyse (Körperzusammensetzung)")
            
            b_col1, b_col2, b_col3 = st.columns(3)
            with b_col1:
                df_valid_fat = df_daily[df_daily['Koerperfett'] > 0.1].sort_values('Datum')
                if not df_valid_fat.empty:
                    fig_fat = go.Figure(go.Scatter(x=df_valid_fat.tail(10)['Datum'], y=df_valid_fat.tail(10)['Koerperfett'], mode='lines+markers', name="Fett %", line=dict(color='#e74c3c', width=3)))
                    fig_fat.update_layout(height=220, margin=dict(l=0,r=0,t=20,b=0), title=f"📉 Körperfett-Verlauf (Aktuell: {fmt_dec(latest['Koerperfett'])} %)")
                    st.plotly_chart(fig_fat, use_container_width=True, config={'staticPlot': True})
                else:
                    st.info("Trage links Körperfett-Werte ein.")
            with b_col2:
                df_valid_water = df_daily[df_daily['Koerperwasser'] > 0.1].sort_values('Datum')
                if not df_valid_water.empty:
                    fig_water = go.Figure(go.Scatter(x=df_valid_water.tail(10)['Datum'], y=df_valid_water.tail(10)['Koerperwasser'], mode='lines+markers', name="Wasser %", line=dict(color='#3498db', width=3)))
                    fig_water.update_layout(height=220, margin=dict(l=0,r=0,t=20,b=0), title=f"💧 Körperwasser-Verlauf (Aktuell: {fmt_dec(latest['Koerperwasser'])} %)")
                    st.plotly_chart(fig_water, use_container_width=True, config={'staticPlot': True})
                else:
                    st.info("Trage links Körperwasser-Werte ein.")
            with b_col3:
                df_valid_musc = df_daily[df_daily['Muskelmasse'] > 0.1].sort_values('Datum')
                if not df_valid_musc.empty:
                    fig_musc = go.Figure(go.Scatter(x=df_valid_musc.tail(10)['Datum'], y=df_valid_musc.tail(10)['Muskelmasse'], mode='lines+markers', name="Muskeln kg", line=dict(color='#2ecc71', width=3)))
                    fig_musc.update_layout(height=220, margin=dict(l=0,r=0,t=20,b=0), title=f"💪 Muskelmasse-Verlauf (Aktuell: {fmt_dec(latest['Muskelmasse'])} kg)")
                    st.plotly_chart(fig_musc, use_container_width=True, config={'staticPlot': True})
                else:
                    st.info("Trage links Muskelmasse ein.")

            st.markdown("---")
            st.subheader("🥗 Kalorien-Haushalt")
            netto_kcal = int(latest['Kalorien_In'] - latest['Kalorien_Out'])
            diff_to_limit = int(limit_kcal - latest['Kalorien_In'])
            
            if netto_kcal <= 1800:
                ampel_color = "#1e3d2f"
                ampel_text = "🟢 Optimales Defizit"
            elif 1800 < netto_kcal <= 2300:
                ampel_color = "#3a351c"
                ampel_text = "🟡 Grenzwertig / Haltekalorien"
            else:
                ampel_color = "#4c1c1c"
                ampel_text = "🔴 Kalorien-Überschuss!"
                
            c_m, c_g = st.columns([0.25, 0.75])
            with c_m:
                st.metric("Aufgenommen", f"{fmt_int(latest['Kalorien_In'])} kcal")
                st.metric("Übrig (vom Limit)", f"{fmt_int(diff_to_limit)} kcal", delta_color="normal" if diff_to_limit >= 0 else "inverse")
                st.markdown(f"""
                <div style="background-color:{ampel_color}; padding:15px; border-radius:10px; border-left: 5px solid {'#2ecc71' if '🟢' in ampel_text else '#f1c40f' if '🟡' in ampel_text else '#e74c3c'};">
                    <p style="margin:0; font-size:12px; color:#aaa; font-weight:bold;">NETTO-BILANZ (IN-OUT)</p>
                    <h2 style="margin:0; color:white;">{fmt_int(netto_kcal)} kcal</h2>
                    <p style="margin:5px 0 0 0; font-size:14px; font-weight:bold;">{ampel_text}</p>
                </div>
                """, unsafe_allow_html=True)
                
            with c_g:
                fig_c = px.bar(df_p, x='Datum', y=['Kalorien_In', 'Kalorien_Out'], barmode='group')
                fig_c.add_hline(y=limit_kcal, line_dash="dot", line_color="red", annotation_text="Limit 2300")
                fig_c.update_layout(height=350, margin=dict(l=0,r=0,t=20,b=0))
                st.plotly_chart(fig_c, use_container_width=True, config={'staticPlot': True})

            st.markdown("---")
            st.subheader("🎯 Ernährungs-Fortschritt (Heute)")
            ef_col1, ef_col2 = st.columns(2)
            
            size_protein = 112
            aktuelles_protein = float(latest.get('Eiweiss', 0.0))
            protein_quote = min(int((aktuelles_protein / size_protein) * 100), 100) if aktuelles_protein > 0 else 0
            
            with ef_col1:
                st.markdown(f"**🍗 Proteine:** {fmt_dec(aktuelles_protein)}g von {size_protein}g ({protein_quote}%)")
                st.progress(protein_quote / 100)

            grid_wasser = 5
            aktuelles_wasser = int(latest.get('Wasser_Menge', 0))
            wasser_quote = min(int((aktuelles_wasser / grid_wasser) * 100), 100) if aktuelles_wasser > 0 else 0
            
            with ef_col2:
                st.markdown(f"**💧 Flüssigkeit:** {aktuelles_wasser} von {grid_wasser} Einheiten ({wasser_quote}%)")
                st.progress(wasser_quote / 100)

            st.markdown("---")
            col_steps, col_bmi_gauge = st.columns([0.7, 0.3])
            with col_steps:
                fig_s = go.Figure(go.Bar(x=df_p['Datum'], y=df_p['Schritte'], marker_color='lightblue', text=df_p['Schritte'], textposition='outside'))
                fig_s.add_hline(y=10000, line_dash="dash", line_color="white")
                fig_s.update_layout(height=350, margin=dict(l=0,r=0,t=40,b=0), title="👣 Tägliche Schritte")
                st.plotly_chart(fig_s, use_container_width=True, config={'staticPlot': True})
            with col_bmi_gauge:
                st.markdown(f"<p style='text-align: center; margin-bottom: 0;'><b>{bmi_cat}</b></p>", unsafe_allow_html=True)
                fig_bmi = go.Figure(go.Indicator(mode="gauge+number", value=bmi_val, number={'valueformat': ".1f", 'font': {'size': 20}},
                    gauge={'axis': {'range': [15, 40]}, 'bar': {'color': "white"},
                        'steps': [{'range': [15, 18.5], 'color': "#3498db"}, {'range': [18.5, 25], 'color': "#2ecc71"}, {'range': [25, 30], 'color': "#f1c40f"}, {'range': [30, 40], 'color': "#e74c3c"}]}))
                fig_bmi.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_bmi, use_container_width=True, config={'staticPlot': True})

            st.info(f"📊 **Letzte verfügbare 7 Tage:** {fmt_int(s_steps_f)} Schritte | {fmt_dec(s_km_f)} km | {fmt_int(s_kcal_f)} kcal verbrannt")
            
            # --- 🛠️ NEU: DESIGN-SILHOUETTE (BILD 2) & GEFILTERTER 14-TAGE-QUARTALSTREND ---
            st.markdown("---")
            st.subheader("📐 Interaktiver Körpermaße-Spiegel (Silhouette & 2-Wochen-Quartalstrend)")
            
            col_sil, col_trends = st.columns([0.45, 0.55])
            
            with col_sil:
                # Plotly Figure initialisieren
                fig_shape = go.Figure()
                
                # REALE HOCHWERTIGE MÄNNLICHE SILHOUETTE ALS SVG-PFAD (EXAKT NACH BILD 2)
                # Die Koordinaten zeichnen eine saubere, proportionale Silhouette mit Händen in den Taschen
                silhouette_path = (
                    "M 0,2.15 C 0.06,2.15 0.10,2.11 0.10,2.05 C 0.10,1.94 0.05,1.86 0.03,1.81 "
                    "L 0.03,1.77 C 0.08,1.76 0.14,1.74 0.22,1.72 C 0.31,1.70 0.36,1.62 0.36,1.52 "
                    "L 0.30,1.18 C 0.32,1.10 0.33,0.98 0.27,0.85 L 0.29,0.30 C 0.30,0.22 0.22,0.15 0.15,0.15 "
                    "C 0.11,0.15 0.08,0.22 0.06,0.32 L 0.00,0.48 L -0.06,0.32 C -0.08,0.22 -0.11,0.15 -0.15,0.15 "
                    "C -0.22,0.15 -0.30,0.22 -0.29,0.30 L -0.27,0.85 C -0.33,0.98 -0.32,1.10 -0.30,1.18 "
                    "L -0.36,1.52 C -0.36,1.62 -0.31,1.70 -0.22,1.72 C -0.14,1.74 -0.08,1.76 -0.03,1.77 "
                    "L -0.03,1.81 C -0.05,1.86 -0.10,1.94 -0.10,2.05 C -0.10,2.11 -0.06,2.15 0,2.15 Z"
                )
                
                # Füge die Silhouette als gefüllte Hintergrundform hinzu
                fig_shape.add_shape(
                    type="path",
                    path=silhouette_path,
                    fillcolor="#121212", # Edles Anthrazit-Schwarz für die Silhouette
                    line=dict(color="#37474F", width=1.5),
                    xref="x", yref="y"
                )
                
                # Unsichtbarer Punkt zur Skalierung der Achsen
                fig_shape.add_trace(go.Scatter(x=[-0.9, 0.9], y=[0.1, 2.3], mode='markers', marker=dict(opacity=0), showlegend=False))
                
                # Anatomisch perfekt ausgerichtete Messboxen mit Pfeilen direkt auf die Körperstellen
                fig_shape.add_annotation(x=-0.01, y=1.79, ax=-0.65, ay=1.83, text=f"🦒 <b>Hals:</b> {fmt_dec(latest['Hals'])} cm", showarrow=True, arrowhead=2, arrowcolor='#f1c40f', font=dict(size=13, color='white'), bgcolor='#1A1A1A', bordercolor='#f1c40f', borderwidth=1.5)
                fig_shape.add_annotation(x=0.20, y=1.55, ax=0.65, ay=1.55, text=f"🦍 <b>Brust:</b> {fmt_dec(latest['Brust'])} cm", showarrow=True, arrowhead=2, arrowcolor='#3498db', font=dict(size=13, color='white'), bgcolor='#1A1A1A', bordercolor='#3498db', borderwidth=1.5)
                fig_shape.add_annotation(x=-0.15, y=1.26, ax=-0.65, ay=1.26, text=f"🍕 <b>Bauch:</b> {fmt_dec(latest['Bauch'])} cm", showarrow=True, arrowhead=2, arrowcolor='#e74c3c', font=dict(size=13, color='white'), bgcolor='#1A1A1A', bordercolor='#e74c3c', borderwidth=1.5)
                fig_shape.add_annotation(x=0.18, y=0.88, ax=0.65, ay=0.88, text=f"🍗 <b>Beine:</b> {fmt_dec(latest['Oberschenkel'])} cm", showarrow=True, arrowhead=2, arrowcolor='#2ecc71', font=dict(size=13, color='white'), bgcolor='#1A1A1A', bordercolor='#2ecc71', borderwidth=1.5)
                
                # Layout-Konfiguration für die Grafikansicht
                fig_shape.update_layout(
                    xaxis=dict(visible=False, range=[-1.0, 1.0]),
                    yaxis=dict(visible=False, range=[0.05, 2.35]),
                    height=480, margin=dict(l=0, r=0, t=0, b=0),
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_shape, use_container_width=True, config={'staticPlot': True})
                
            with col_trends:
                # Quartals-Filter (Die letzten 90 Tage ab heute)
                quartal_ago = pd.Timestamp.now() - pd.Timedelta(days=90)
                df_q = df_daily[df_daily['Datum'] >= quartal_ago].copy()
                
                if df_q.empty: 
                    df_q = df_daily.copy()
                
                if not df_q.empty:
                    # Sortieren und Resampling auf exakt 14 Tage (2 Wochen), um tägliche Datenschwankungen zu glätten
                    df_q = df_q.sort_values('Datum').set_index('Datum')
                    df_biweekly = df_q.resample('14D').last().dropna(subset=['Hals', 'Brust', 'Bauch', 'Oberschenkel']).reset_index()
                    
                    m_labels = [
                        ("Halsumfang 🦒", "Hals", "#f1c40f"), 
                        ("Brustumfang 🦍", "Brust", "#3498db"), 
                        ("Bauchumfang 🍕", "Bauch", "#e74c3c"), 
                        ("Oberschenkel 🍗", "Oberschenkel", "#2ecc71")
                    ]
                    
                    # Generiere saubere, kompakte Trendkurven für das Quartal
                    for label, col_key, curve_color in m_labels:
                        fig_mini = go.Figure(go.Scatter(
                            x=df_biweekly['Datum'], y=df_biweekly[col_key], 
                            mode='lines+markers', 
                            line=dict(color=curve_color, width=3),
                            marker=dict(size=6, symbol='circle')
                        ))
                        fig_mini.update_layout(
                            height=105, 
                            margin=dict(l=10, r=10, t=22, b=10), 
                            title=dict(text=f"<b>{label}</b> (14-Tage Intervall / Quartal)", font=dict(size=12, color='#ECEFF1')), 
                            xaxis=dict(showgrid=False, tickformat="%d.%m", tickfont=dict(size=9)), 
                            yaxis=dict(showgrid=True, tickfont=dict(size=9), nticks=4)
                        )
                        st.plotly_chart(fig_mini, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Noch keine Messdaten für das Quartals-Diagramm vorhanden.")

        else:
            st.info("💡 Willkommen! Sobald du Daten in der linken Seitenleiste einträgst, erscheinen hier deine Kurven.")

    with tab2:
        st.header("📊 Langzeit-Statistik")
        if not df_filled.empty:
            now = pd.Timestamp.now()
            
            heute_date = date.today()
            start_der_woche = heute_date - timedelta(days=heute_date.weekday())
            df_this_week = df_daily[df_daily['Datum'].dt.date >= start_der_woche].sort_values('Datum')
            
            periods = {
                "Letzte Woche (Rollen-Basis 7 Tage)": 7, 
                "Letzter Monat": 30, 
                "Letztes Quartal": 90, 
                "Letztes Jahr": 365
            }
            
            st.subheader(f"📅 Aktuelle Kalenderwoche (Seit Mo, {start_der_woche.strftime('%d.%m.%Y')})")
            if not df_this_week.empty:
                c1, c2, c3, c4 = st.columns([1,1,1,1.5])
                c1.metric("👣 Schritte", fmt_int(df_this_week['Schritte'].sum()))
                w_diff = df_this_week.iloc[-1]['Gewicht'] - df_this_week.iloc[0]['Gewicht']
                c2.metric("⚖️ Gewicht", f"{fmt_dec(df_this_week.iloc[-1]['Gewicht'])} kg", f"{fmt_dec(w_diff)} kg", delta_color="inverse")
                c3.metric("🔥 Kalorien Out", fmt_int(df_this_week['Schritte'].sum()))
                with c4:
                    st.markdown("**📉 Waagen-Werte (Diff diese Woche):**")
                    fat_diff = df_this_week.iloc[-1]['Koerperfett'] - df_this_week.iloc[0]['Koerperfett']
                    wat_diff = df_this_week.iloc[-1]['Koerperwasser'] - df_this_week.iloc[0]['Koerperwasser']
                    musc_diff = df_this_week.iloc[-1]['Muskelmasse'] - df_this_week.iloc[0]['Muskelmasse']
                    st.markdown(f"Fettanteil: <span style='color:{'green' if fat_diff < 0 else 'red'}; font-weight:bold;'>{fmt_dec(fat_diff)} %</span>", unsafe_allow_html=True)
                    st.markdown(f"Wasseranteil: <span style='color:{'green' if wat_diff > 0 else 'red'}; font-weight:bold;'>{fmt_dec(wat_diff)} %</span>", unsafe_allow_html=True)
                    st.markdown(f"Muskelmasse: <span style='color:{'green' if musc_diff < 0 else 'red'}; font-weight:bold;'>{fmt_dec(musc_diff)} kg</span>", unsafe_allow_html=True)
                    
                    st.markdown("**📏 Maße (Diff diese Woche):**")
                    for m in ['Hals', 'Brust', 'Bauch', 'Oberschenkel']:
                        d = df_this_week.iloc[-1][m] - df_this_week.iloc[0][m]
                        color = "green" if d < 0 else "red" if d > 0 else "#f1c40f"
                        st.markdown(f"{m}: <span style='color:{color}; font-weight:bold;'>{fmt_dec(d)} cm</span>", unsafe_allow_html=True)
            else:
                st.caption("Noch keine Daten für die aktuelle Kalenderwoche erfasst.")
            st.markdown("---")
            
            for title, days in periods.items():
                p_df = df_daily[df_daily['Datum'] >= (now - pd.Timedelta(days=days))].sort_values('Datum')
                if not p_df.empty:
                    st.subheader(title)
                    c1, c2, c3, c4 = st.columns([1,1,1,1.5])
                    c1.metric("👣 Schritte", fmt_int(p_df['Schritte'].sum()))
                    w_diff = p_df.iloc[-1]['Gewicht'] - p_df.iloc[0]['Gewicht']
                    c2.metric("⚖️ Gewicht", f"{fmt_dec(p_df.iloc[-1]['Gewicht'])} kg", f"{fmt_dec(w_diff)} kg", delta_color="inverse")
                    c3.metric("🔥 Kalorien Out", fmt_int(p_df['Kalorien_Out'].sum()))
                    with c4:
                        st.markdown("**📉 Waagen-Werte (Diff):**")
                        fat_d = p_df.iloc[-1]['Koerperfett'] - p_df.iloc[0]['Koerperfett']
                        wat_d = p_df.iloc[-1]['Koerperwasser'] - p_df.iloc[0]['Koerperwasser']
                        musc_d = p_df.iloc[-1]['Muskelmasse'] - p_df.iloc[0]['Muskelmasse']
                        st.markdown(f"Fettanteil: <span style='color:{'green' if fat_d < 0 else 'red'}; font-weight:bold;'>{fmt_dec(fat_d)} %</span>", unsafe_allow_html=True)
                        st.markdown(f"Wasseranteil: <span style='color:{'green' if wat_d > 0 else 'red'}; font-weight:bold;'>{fmt_dec(wat_d)} %</span>", unsafe_allow_html=True)
                        st.markdown(f"Muskelmasse: <span style='color:{'green' if musc_d > 0 else 'red'}; font-weight:bold;'>{fmt_dec(musc_d)} kg</span>", unsafe_allow_html=True)
                        
                        st.markdown("**📏 Maße (Diff):**")
                        for m in ['Hals', 'Brust', 'Bauch', 'Oberschenkel']:
                            d = p_df.iloc[-1][m] - p_df.iloc[0][m]
                            color = "green" if d < 0 else "red" if d > 0 else "#f1c40f"
                            st.markdown(f"{m}: <span style='color:{color}; font-weight:bold;'>{fmt_dec(d)} cm</span>", unsafe_allow_html=True)
                    st.markdown("---")
        else:
            st.info("📊 Hier werden die Vergleiche berechnet, sobald Daten vorliegen.")

    with tab3:
        st.header("📋 Datentabelle & Verwaltung")
        
        st.subheader("💾 Gesamte Datensicherung (Excel Backup)")
        exp_col, imp_col = st.columns(2)
        with exp_col:
            st.write("Daten als Excel-Liste herunterladen:")
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.sort_values(['Datum', 'Uhrzeit'], ascending=False).to_excel(writer, index=False, sheet_name='FitnessData')
            excel_data = output.getvalue()
            st.download_button(label="📥 Excel Export", data=excel_data, file_name=f"fitness_hub_export_{date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", disabled=df.empty)
        with imp_col:
            st.write("Alte Backup-Daten aus Excel oder CSV wieder hochladen:")
            uploaded_file = st.file_uploader("Datei wählen (.xlsx oder .csv)", type=["xlsx", "csv"], key="general_import")
            if uploaded_file is not None:
                try:
                    if uploaded_file.name.endswith('.csv'):
                        imp_df = pd.read_csv(uploaded_file)
                    else:
                        imp_df = pd.read_excel(uploaded_file)
                        
                    with conn.session as session:
                        for _, row in imp_df.iterrows():
                            d_val = pd.to_datetime(row['Datum']).strftime("%Y-%m-%d")
                            check = session.execute(text("SELECT 1 FROM fitness_data WHERE Datum = :d AND Uhrzeit = :u"), {"d": d_val, "u": str(row['Uhrzeit'])}).fetchone()
                            if not check:
                                session.execute(text("""
                                    INSERT INTO fitness_data (Datum, Uhrzeit, Gewicht, Schritte, Aktivzeit, Kalorien_In, Kalorien_Out, Hals, Brust, Bauch, Oberschenkel, Aktivitaet, Bemerkung, Eiweiss, Wasser_Menge, Koerperfett, Muskelmasse, Koerperwasser)
                                    VALUES (:Datum, :Uhrzeit, :Gewicht, :Schritte, :Aktivzeit, :Kalorien_In, :Kalorien_Out, :Hals, :Brust, :Bauch, :Oberschenkel, :Aktivitaet, :Bemerkung, :Eiweiss, :Wasser_Menge, :Koerperfett, :Muskelmasse, :Koerperwasser)
                                """), {
                                    "Datum": d_val, "Uhrzeit": str(row['Uhrzeit']), "Gewicht": float(row.get('Gewicht', 0)), "Schritte": int(row.get('Schritte', 0)), 
                                    "Aktivzeit": int(row.get('Aktivzeit', 0)), "Kalorien_In": int(row.get('Kalorien_In', 0)), "Kalorien_Out": int(row.get('Kalorien_Out', 0)), 
                                    "Hals": float(row.get('Hals', 0)), "Brust": float(row.get('Brust', 0)), "Bauch": float(row.get('Bauch', 0)), "Oberschenkel": float(row.get('Oberschenkel', 0)), 
                                    "Aktivitaet": str(row.get('Aktivitaet', 'Gehen')), "Bemerkung": str(row.get('Bemerkung', '')),
                                    "Eiweiss": float(row.get('Eiweiss', 0.0)), "Wasser_Menge": int(row.get('Wasser_Menge', 0)),
                                    "Koerperfett": float(row.get('Koerperfett', 0.0)), "Muskelmasse": float(row.get('Muskelmasse', 0.0)), "Koerperwasser": float(row.get('Koerperwasser', 0.0))
                                })
                        session.commit()
                    st.cache_data.clear()
                    st.success("✅ Backup erfolgreich eingelesen!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Import: {e}")

        if not df.empty:
            st.markdown("---")
            disp_view = df.sort_values(['Datum', 'Uhrzeit'], ascending=False).copy()
            disp_view['Datum'] = disp_view['Datum'].dt.strftime('%d.%m.%Y')
            st.dataframe(disp_view[['Datum', 'Uhrzeit', 'Aktivitaet', 'Schritte', 'Gewicht', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Eiweiss', 'Wasser_Menge', 'Koerperfett', 'Koerperwasser', 'Muskelmasse']], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            edit_col, delete_col = st.columns(2)
            with edit_col:
                st.subheader("✏️ Eintrag korrigieren")
                df_sorted_e = df.sort_values(['Datum', 'Uhrzeit'], ascending=False)
                options_e = [f"{row['Datum'].strftime('%d.%m.%Y')} {row['Uhrzeit']}" for _, row in df_sorted_e.iterrows()]
                selected_label = st.selectbox("Eintrag wählen", options_e, key="edit_sel")
                
                sel_date_str = selected_label.split(" ")[0]
                sel_time_str = selected_label.split(" ")[1]
                sel_date_sql = datetime.strptime(sel_date_str, "%d.%m.%Y").strftime("%Y-%m-%d")
                row_to_edit = df[(df['Datum'].dt.strftime('%Y-%m-%d') == sel_date_sql) & (df['Uhrzeit'] == sel_time_str)].iloc[0]
                
                with st.form("edit_form"):
                    e_d = st.date_input("Datum", row_to_edit['Datum'])
                    e_t = st.text_input("Uhrzeit", row_to_edit['Uhrzeit'])
                    sport_options = ["Kein Sport", "Gehen", "Fahrrad", "Schwimmen", "Krafttraining"]
                    e_act = st.select_slider("Sportart", options=sport_options, value=row_to_edit.get('Aktivitaet', 'Gehen'))
                    ec1, ec2 = st.columns(2)
                    e_gew = ec1.number_input("Gewicht (kg)", value=float(row_to_edit['Gewicht']), format="%.1f")
                    e_step = ec2.number_input("Schritte", value=int(row_to_edit['Schritte']))
                    e_kin = ec1.number_input("Kalorien In", value=int(row_to_edit['Kalorien_In']))
                    e_kout = ec2.number_input("Kalorien Out", value=int(row_to_edit['Kalorien_Out']))
                    e_note = st.text_input("Bemerkung", value=str(row_to_edit['Bemerkung']))
                    em1, em2 = st.columns(2)
                    e_hals = em1.number_input("Hals", value=float(row_to_edit['Hals']), format="%.1f")
                    e_brust = em2.number_input("Brust", value=float(row_to_edit['Brust']), format="%.1f")
                    e_bauch = em1.number_input("Bauch", value=float(row_to_edit['Bauch']), format="%.1f")
                    e_bein = em2.number_input("Oberschenkel", value=float(row_to_edit['Oberschenkel']), format="%.1f")
                    
                    st.markdown("**✏️ Werte korrigieren**")
                    ee_eiweiss = st.number_input("Eiweiß (Gramm)", value=float(row_to_edit.get('Eiweiss', 0.0)), format="%.1f")
                    ee_wasser = st.number_input("Flüssigkeit (Einheiten)", value=int(row_to_edit.get('Wasser_Menge', 0)))
                    ee_fat = ec1.number_input("Körperfett (%)", value=float(row_to_edit.get('Koerperfett', 0.0)), format="%.1f")
                    ee_water = ec2.number_input("Körperwasser (%)", value=float(row_to_edit.get('Koerperwasser', 0.0)), format="%.1f")
                    ee_musc = st.number_input("Muskelmasse (kg)", value=float(row_to_edit.get('Muskelmasse', 0.0)), format="%.1f")
                    
                    if st.form_submit_button("Änderungen speichern 💾"):
                        with conn.session as session:
                            session.execute(text("""
                                UPDATE fitness_data 
                                SET Datum = :new_d, Uhrzeit = :new_t, Gewicht = :gew, Schritte = :step, 
                                    Kalorien_In = :kin, Kalorien_Out = :kout, 
                                    Hals = :hals, Brust = :brust, Bauch = :bauch, Oberschenkel = :bein, 
                                    Aktivitaet = :act, Bemerkung = :note,
                                    Eiweiss = :ew, Wasser_Menge = :wm, Koerperfett = :kf, Koerperwasser = :kw, Muskelmasse = :mm
                                WHERE Datum = :old_d AND Uhrzeit = :old_t
                            """), {
                                "new_d": e_d.strftime("%Y-%m-%d"), "new_t": e_t, "gew": e_gew, "step": e_step, 
                                "kin": e_kin, "kout": e_kout, "hals": e_hals, "brust": e_brust, "bauch": e_bauch, "bein": e_bein, 
                                "act": e_act, "note": e_note, "ew": ee_eiweiss, "wm": ee_wasser, "kf": ee_fat, "kw": ee_water, "mm": ee_musc,
                                "old_d": sel_date_sql, "old_t": sel_time_str
                            })
                            session.commit()
                        st.success("Eintrag aktualisiert!")
                        st.rerun()

            with delete_col:
                st.subheader("🗑️ Eintrag löschen")
                df_sorted_d = df.sort_values(['Datum', 'Uhrzeit'], ascending=False)
                options_d = [f"{row['Datum'].strftime('%d.%m.%Y')} {row['Uhrzeit']}" for _, row in df_sorted_d.iterrows()]
                del_label = st.selectbox("Löschen wählen", options_d, key="del_sel")
                if st.button("⚠️ Endgültig löschen"):
                    del_date_str = del_label.split(" ")[0]
                    del_time_str = del_label.split(" ")[1]
                    del_date_sql = datetime.strptime(del_date_str, "%d.%m.%Y").strftime("%Y-%m-%d")
                    with conn.session as session:
                        session.execute(text("DELETE FROM fitness_data WHERE Datum = :d AND Uhrzeit = :u"), {"d": del_date_sql, "u": del_time_str})
                        session.commit()
                    st.rerun()
