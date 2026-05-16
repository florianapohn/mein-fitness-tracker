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
from sqlalchemy import text # NEU: Wird für die Ausführung der SQL-Befehle benötigt

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

    # KORREKTUR: Befehle werden jetzt in text() gepackt, um den ArgumentError zu verhindern
    with conn.session as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS fitness_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Datum TEXT, Uhrzeit TEXT, Gewicht REAL, Schritte INTEGER, 
                Aktivzeit INTEGER, Kalorien_In INTEGER, Kalorien_Out INTEGER, 
                Hals REAL, Brust REAL, Bauch REAL, Oberschenkel REAL, 
                Aktivitaet TEXT, Bemerkung TEXT
            )
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS user_settings (
                key TEXT PRIMARY KEY, value TEXT
            )
        """))
        session.commit()

    # Hilfsfunktionen zum Laden & Speichern der Daten aus SQL
    def load_fitness_data():
        try:
            df_sql = conn.query("SELECT * FROM fitness_data", ttl=0)
            if df_sql.empty:
                columns = ['Datum', 'Uhrzeit', 'Gewicht', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Aktivitaet', 'Bemerkung']
                return pd.DataFrame(columns=columns)
            df_sql['Datum'] = pd.to_datetime(df_sql['Datum'])
            if 'id' in df_sql.columns: df_sql = df_sql.drop(columns=['id'])
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

    # Daten laden
    df = load_fitness_data()
    settings = load_settings()

    # Konvertierungen für Settings
    settings["height"] = int(settings.get("height", 179))
    settings["target_weight"] = float(settings.get("target_weight", 75.0))
    settings["reminder_active"] = settings.get("reminder_active") == "True"
    settings["last_email_kw"] = int(settings.get("last_email_kw", 0))

    # Forward-Fill Logik
    df_filled = df.sort_values(['Datum', 'Uhrzeit']).copy() if not df.empty else pd.DataFrame()
    if not df.empty:
        cols_to_fill = ['Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Gewicht']
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
            mail_text += "\nBleib dran! ⚡"
            
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
        submit = st.form_submit_button("Speichern ✨")

    if submit:
        now_t = datetime.now().strftime("%H:%M")
        with conn.session as session:
            session.execute(text("""
                INSERT INTO fitness_data (Datum, Uhrzeit, Gewicht, Schritte, Aktivzeit, Kalorien_In, Kalorien_Out, Hals, Brust, Bauch, Oberschenkel, Aktivitaet, Bemerkung)
                VALUES (:Datum, :Uhrzeit, :Gewicht, :Schritte, :Aktivzeit, :Kalorien_In, :Kalorien_Out, :Hals, :Brust, :Bauch, :Oberschenkel, :Aktivitaet, :Bemerkung)
            """), {"Datum": d.strftime("%Y-%m-%d"), "Uhrzeit": now_t, "Gewicht": gew, "Schritte": step, "Aktivzeit": akt_min, "Kalorien_In": k_in, "Kalorien_Out": k_out, "Hals": hals_in, "Brust": brust_in, "Bauch": bauch_in, "Oberschenkel": bein_in, "Aktivitaet": act_type, "Bemerkung": note})
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
            st.sidebar.code(f"Hey, schau mal! 🏆\nGewicht: {latest_all_f['Gewicht']:.1f} kg\nBMI: {bmi_val_f:.1f}\n\nLetzte 7 Tage:\n🔥 {int(s_kcal_f):,} kcal\n🏃‍♂️ {s_km_f:.1f} km\n👣 {int(s_steps_f):,} Schritte", language="text")

    if st.sidebar.button("Logout 🚪"):
        st.session_state.clear()
        st.rerun()

    # --- 6. HAUPTBEREICH ---
    tab1, tab2, tab3 = st.tabs(["Kurven & Trends 📈", "Langzeit-Statistik 📊", "Datentabelle 📋"])

    with tab1:
        if not df_filled.empty:
            ten_days_ago = pd.Timestamp.now() - pd.Timedelta(days=10)
            df_daily = df_filled.groupby('Datum').agg({'Kalorien_In': 'sum', 'Kalorien_Out': 'sum', 'Schritte': 'sum', 'Gewicht': 'last', 'Hals': 'last', 'Brust': 'last', 'Bauch': 'last', 'Oberschenkel': 'last'}).reset_index()
            df_p = df_daily[df_daily['Datum'] >= ten_days_ago].sort_values('Datum')
            if df_p.empty: df_p = df_daily.tail(10)
            
            latest = df_p.iloc[-1]
            h_m = float(settings["height"]) / 100
            bmi_val = float(latest['Gewicht']) / (h_m ** 2) if latest['Gewicht'] > 0 else 0.0
            bmi_cat = "Normalgewicht" if 18.5 <= bmi_val < 25 else "Übergewicht" if 25 <= bmi_val < 30 else "Adipositas" if bmi_val >= 30 else "Untergewicht"
            limit_kcal = 2300
            target_w = float(settings["target_weight"])
            
            st.subheader("⚖️ Gewichtsanalyse")
            col_w_metric, col_w_graph = st.columns([0.25, 0.75])
            with col_w_metric:
                st.metric("Aktuell", f"{latest['Gewicht']:.1f} kg", f"{latest['Gewicht'] - target_w:+.1f} kg zum Ziel", delta_color="inverse")
            with col_w_graph:
                fig_w = go.Figure(go.Scatter(x=df_p['Datum'], y=df_p['Gewicht'], fill='tozeroy', mode='lines+markers', name="Gewicht", line=dict(width=3, color='#0288D1', shape='spline')))
                fig_w.add_hline(y=target_w, line_dash="dash", line_color="red", annotation_text=f"Ziel {target_w}kg")
                fig_w.update_layout(height=300, margin=dict(l=0,r=0,t=20,b=0))
                st.plotly_chart(fig_w, use_container_width=True, config={'staticPlot': True})

            st.markdown("---")
            st.subheader("🥗 Kalorien-Haushalt")
            netto_kcal = int(latest['Kalorien_In'] - latest['Kalorien_Out'])
            diff_to_limit = int(limit_kcal - latest['Kalorien_In'])
            c_m, c_g = st.columns([0.25, 0.75])
            with c_m:
                st.metric("Aufgenommen", f"{int(latest['Kalorien_In'])} kcal")
                st.metric("Übrig (vom Limit)", f"{diff_to_limit} kcal", delta_color="normal" if diff_to_limit >= 0 else "inverse")
                st.metric("Netto-Bilanz (In-Out)", f"{netto_kcal} kcal")
            with c_g:
                fig_c = px.bar(df_p, x='Datum', y=['Kalorien_In', 'Kalorien_Out'], barmode='group')
                fig_c.add_hline(y=limit_kcal, line_dash="dot", line_color="red", annotation_text="Limit 2300")
                fig_c.update_layout(height=350, margin=dict(l=0,r=0,t=20,b=0))
                st.plotly_chart(fig_c, use_container_width=True, config={'staticPlot': True})

            st.markdown("---")
            col_steps, col_bmi_gauge = st.columns([0.7, 0.3])
            with col_steps:
                fig_s = go.Figure(go.Bar(x=df_p['Datum'], y=df_p['Schritte'], marker_color='lightblue', text=df_p['Schritte'], textposition='outside'))
                fig_s.add_hline(y=10000, line_dash="dash", line_color="white")
                fig_s.update_layout(height=350, margin=dict(l=0,r=0,t=40,b=0), title="👣 Tägliche Schritte (Letzte 10 Tage)")
                st.plotly_chart(fig_s, use_container_width=True, config={'staticPlot': True})
            with col_bmi_gauge:
                st.markdown(f"<p style='text-align: center; margin-bottom: 0;'><b>{bmi_cat}</b></p>", unsafe_allow_html=True)
                fig_bmi = go.Figure(go.Indicator(mode="gauge+number", value=bmi_val, number={'valueformat': ".1f", 'font': {'size': 20}},
                    gauge={'axis': {'range': [15, 40]}, 'bar': {'color': "white"},
                        'steps': [{'range': [15, 18.5], 'color': "#3498db"}, {'range': [18.5, 25], 'color': "#2ecc71"}, {'range': [25, 30], 'color': "#f1c40f"}, {'range': [30, 40], 'color': "#e74c3c"}]}))
                fig_bmi.update_layout(height=250, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_bmi, use_container_width=True, config={'staticPlot': True})

            st.info(f"📊 **Letzte 7 Tage:** {int(s_steps_f):,} Schritte | {s_km_f:.1f} km | {int(s_kcal_f):,} kcal verbrannt")
            st.markdown("---")
            st.subheader("📏 Körpermaße Trend")
            def get_trend_icon(current, previous):
                if current < previous: return "🔻", "green"
                elif current > previous: return "🔺", "red"
                else: return "➖", "yellow"
            prev_row = df_daily.iloc[-2] if len(df_daily) >= 2 else latest
            m_data = [{"label": "Hals🦒", "key": "Hals", "avg": "40 cm"}, {"label": "Brust🦍", "key": "Brust", "avg": "103 cm"}, {"label": "Bauch🍕", "key": "Bauch", "avg": "89 cm"}, {"label": "Beine🍗", "key": "Oberschenkel", "avg": "56 cm"}]
            m_cols = st.columns(4)
            for i, item in enumerate(m_data):
                icon, color = get_trend_icon(latest[item['key']], prev_row[item['key']])
                with m_cols[i]:
                    st.markdown(f"**{item['label']}**")
                    st.markdown(f"<h2 style='margin-bottom:0;'>{latest[item['key']]} cm <span style='font-size:20px; color:{color};'>{icon}</span></h2>", unsafe_allow_html=True)
                    st.caption(f"Durchschnitt: {item['avg']}")
        else:
            st.info("💡 Willkommen! Sobald du Daten einträgst oder dein Backup hochlädst, erscheinen hier deine Kurven.")

    with tab2:
        st.header("📊 Langzeit-Statistik")
        if not df_filled.empty:
            now = pd.Timestamp.now()
            periods = {"Letzte Woche": 7, "Letzter Monat": 30, "Letztes Quartal": 90, "Letztes Jahr": 365}
            for title, days in periods.items():
                p_df = df_daily[df_daily['Datum'] >= (now - pd.Timedelta(days=days))].sort_values('Datum')
                if not p_df.empty:
                    st.subheader(title)
                    c1, c2, c3, c4 = st.columns([1,1,1,1.5])
                    c1.metric("👣 Schritte", f"{int(p_df['Schritte'].sum()):,}")
                    w_diff = p_df.iloc[-1]['Gewicht'] - p_df.iloc[0]['Gewicht']
                    c2.metric("⚖️ Gewicht", f"{p_df.iloc[-1]['Gewicht']:.1f} kg", f"{w_diff:+.1f} kg", delta_color="inverse")
                    c3.metric("🔥 Kalorien Out", f"{int(p_df['Kalorien_Out'].sum()):,}")
                    with c4:
                        st.markdown("**📏 Maße (Diff):**")
                        for m in ['Hals', 'Brust', 'Bauch', 'Oberschenkel']:
                            d = p_df.iloc[-1][m] - p_df.iloc[0][m]
                            color = "green" if d < 0 else "red" if d > 0 else "#f1c40f"
                            st.markdown(f"{m}: <span style='color:{color}; font-weight:bold;'>{d:+.1f} cm</span>", unsafe_allow_html=True)
                    st.markdown("---")
        else:
            st.info("📊 Hier werden die Vergleiche für Woche, Monat und Jahr berechnet, sobald Daten vorliegen.")

    with tab3:
        st.header("📋 Datentabelle & Verwaltung")
        st.subheader("💾 Datensicherung (Excel)")
        exp_col, imp_col = st.columns(2)
        with exp_col:
            st.write("Daten als Excel-Liste herunterladen:")
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.sort_values(['Datum', 'Uhrzeit'], ascending=False).to_excel(writer, index=False, sheet_name='FitnessData')
            excel_data = output.getvalue()
            st.download_button(label="📥 Excel Export", data=excel_data, file_name=f"fitness_hub_export_{date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", disabled=df.empty)
        with imp_col:
            st.write("Alte Daten aus Excel hochladen:")
            uploaded_file = st.file_uploader("Excel Datei wählen (.xlsx)", type="xlsx")
            if uploaded_file is not None:
                try:
                    imp_df = pd.read_excel(uploaded_file)
                    with conn.session as session:
                        for _, row in imp_df.iterrows():
                            d_val = pd.to_datetime(row['Datum']).strftime("%Y-%m-%d")
                            check = session.execute(text("SELECT 1 FROM fitness_data WHERE Datum = :d AND Uhrzeit = :u"), {"d": d_val, "u": str(row['Uhrzeit'])}).fetchone()
                            if not check:
                                session.execute(text("""
                                    INSERT INTO fitness_data (Datum, Uhrzeit, Gewicht, Schritte, Aktivzeit, Kalorien_In, Kalorien_Out, Hals, Brust, Bauch, Oberschenkel, Aktivitaet, Bemerkung)
                                    VALUES (:Datum, :Uhrzeit, :Gewicht, :Schritte, :Aktivzeit, :Kalorien_In, :Kalorien_Out, :Hals, :Brust, :Bauch, :Oberschenkel, :Aktivitaet, :Bemerkung)
                                """), {"Datum": d_val, "Uhrzeit": str(row['Uhrzeit']), "Gewicht": float(row.get('Gewicht', 0)), "Schritte": int(row.get('Schritte', 0)), "Aktivzeit": int(row.get('Aktivzeit', 0)), "Kalorien_In": int(row.get('Kalorien_In', 0)), "Kalorien_Out": int(row.get('Kalorien_Out', 0)), "Hals": float(row.get('Hals', 0)), "Brust": float(row.get('Brust', 0)), "Bauch": float(row.get('Bauch', 0)), "Oberschenkel": float(row.get('Oberschenkel', 0)), "Aktivitaet": str(row.get('Aktivitaet', 'Gehen')), "Bemerkung": str(row.get('Bemerkung', ''))})
                        session.commit()
                    st.success("✅ Daten erfolgreich permanent importiert!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Import: {e}")

        if not df.empty:
            st.markdown("---")
            disp_view = df.sort_values(['Datum', 'Uhrzeit'], ascending=False).copy()
            disp_view['Datum'] = disp_view['Datum'].dt.strftime('%d.%m.%Y')
            st.dataframe(disp_view[['Datum', 'Uhrzeit', 'Aktivitaet', 'Schritte', 'Gewicht', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel']], use_container_width=True, hide_index=True)
            
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
                    
                    if st.form_submit_button("Änderungen speichern 💾"):
                        with conn.session as session:
                            session.execute(text("""
                                UPDATE fitness_data 
                                SET Datum = :new_d, Uhrzeit = :new_t, Gewicht = :gew, Schritte = :step, 
                                    Aktivzeit = :akt, Kalorien_In = :kin, Kalorien_Out = :kout, 
                                    Hals = :hals, Brust = :brust, Bauch = :bauch, Oberschenkel = :bein, 
                                    Aktivitaet = :act, Bemerkung = :note
                                WHERE Datum = :old_d AND Uhrzeit = :old_t
                            """), {"new_d": e_d.strftime("%Y-%m-%d"), "new_t": e_t, "gew": e_gew, "step": e_step, "akt": int(row_to_edit['Aktivzeit']), "kin": e_kin, "kout": e_kout, "hals": e_hals, "brust": e_brust, "bauch": e_bauch, "bein": e_bein, "act": e_act, "note": e_note, "old_d": sel_date_sql, "old_t": sel_time_str})
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
