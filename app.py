# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import os
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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

# --- 1. LOGIN SYSTEM (SECURE VIA SECRETS) ---
def check_password():
    def password_entered():
        # Holt die Anmeldedaten sicher aus den Streamlit Secrets statt aus dem Klartext-Code
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
    st.title("My All-in-One Fitness Hub")

    # --- 3. DATEI-HANDLING ---
    DATA_FILE = "fitness_data.csv"
    SETTINGS_FILE = "user_settings.csv"

    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df['Datum'] = pd.to_datetime(df['Datum'])
        needed_cols = {
            'Uhrzeit': "00:00", 'Bemerkung': "", 'Schritte': 0, 'Gewicht': 0.0, 
            'Kalorien_In': 0, 'Kalorien_Out': 0, 'Hals': 0.0, 'Brust': 0.0, 
            'Bauch': 0.0, 'Oberschenkel': 0.0, 'Aktivitaet': "Gehen"
        }
        for col, default in needed_cols.items():
            if col not in df.columns:
                df[col] = default
    else:
        columns = ['Datum', 'Uhrzeit', 'Gewicht', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Aktivitaet', 'Bemerkung']
        df = pd.DataFrame(columns=columns)

    if os.path.exists(SETTINGS_FILE):
        try: 
            settings_data = pd.read_csv(SETTINGS_FILE)
            settings = settings_data.iloc[0].to_dict()
        except: 
            settings = {"email": "florian.pohn@protonmail.com", "reminder_active": False, "weight_daily": True, "measures_day": "Donnerstag", "height": 179, "target_weight": 75.0, "birthday": "1990-01-01", "last_email_kw": 0}
    else:
        settings = {"email": "florian.pohn@protonmail.com", "reminder_active": False, "weight_daily": True, "measures_day": "Donnerstag", "height": 179, "target_weight": 75.0, "birthday": "1990-01-01", "last_email_kw": 0}

    # --- LOGIK: WERTE AUFFÜLLEN (FORWARD FILL) ---
    df_filled = df.sort_values(['Datum', 'Uhrzeit']).copy()
    cols_to_fill = ['Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Gewicht']
    for col in cols_to_fill:
        df_filled[col] = df_filled[col].replace(0, pd.NA)
        df_filled[col] = df_filled[col].ffill().fillna(0)

    # --- AUTOMATISCHE LIVE-EMAIL LOGIK BEIM LOGIN ---
    if settings.get("reminder_active", False):
        wochentage_dict = {"Montag": 0, "Dienstag": 1, "Mittwoch": 2, "Donnerstag": 3, "Freitag": 4, "Samstag": 5, "Sonntag": 6}
        ziel_wochentag = wochentage_dict.get(settings.get("measures_day", "Donnerstag"), 3)
        heute = date.today()
        aktuelle_kw = heute.isocalendar()[1]
        
        if heute.weekday() == ziel_wochentag and int(settings.get("last_email_kw", 0)) != aktuelle_kw:
            latest_mail_row = df_filled.iloc[-1] if not df_filled.empty else None
            mail_text = f"Hallo Florian!\n\nHier ist deine wöchentliche Erinnerung vom My Fitness Hub.\n\n"
            if latest_mail_row is not None:
                mail_text += f"Aktueller Stand deiner letzten Messungen:\n"
                mail_text += f"- Gewicht: {latest_mail_row['Gewicht']:.1f} kg\n"
                mail_text += f"- Bauchumfang: {latest_mail_row['Bauch']:.1f} cm\n"
                mail_text += f"- Brustumfang: {latest_mail_row['Brust']:.1f} cm\n"
                mail_text += f"- Halsumfang: {latest_mail_row['Hals']:.1f} cm\n"
                mail_text += f"- Oberschenkel: {latest_mail_row['Oberschenkel']:.1f} cm\n"
            else:
                mail_text += "Du hast bisher noch keine Daten eingetragen. Zeit für den ersten Eintrag!\n"
            mail_text += "\nBleib dran! ⚡"
            
            if send_reminder_email(settings.get("email"), "My Fitness Hub - Wöchentlicher Check-In", mail_text):
                settings["last_email_kw"] = aktuelle_kw
                pd.DataFrame([settings]).to_csv(SETTINGS_FILE, index=False)
                st.sidebar.success("📧 Erinnerungs-Mail gesendet!")

    # --- 4. SEITENLEISTE: DATENEINGABE ---
    st.sidebar.header(f"Hallo Florian!")
    with st.sidebar.form("entry_form", clear_on_submit=True):
        d = st.date_input("Datum auswählen", date.today())
        
        st.subheader("🏃‍♂️ Aktivität wählen")
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
        now_t, in_d = datetime.now().strftime("%H:%M"), pd.to_datetime(d)
        new_row = {
            'Datum': in_d, 'Uhrzeit': now_t, 'Gewicht': gew, 'Schritte': step, 
            'Aktivzeit': akt_min, 'Kalorien_In': k_in, 'Kalorien_Out': k_out, 
            'Hals': hals_in, 'Brust': brust_in, 'Bauch': bauch_in, 'Oberschenkel': bein_in, 
            'Aktivitaet': act_type, 'Bemerkung': note
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.rerun()

    # --- 5. SEITENLEISTE: EINSTELLUNGEN ---
    st.sidebar.markdown("---")
    with st.sidebar.expander("⚙️ Profil & Zielgewicht"):
        new_h = st.number_input("Größe (cm)", value=int(settings.get("height", 179)), step=1)
        try:
            stored_bday = datetime.strptime(str(settings.get("birthday", "1990-01-01")), "%Y-%m-%d").date()
        except:
            stored_bday = date(1990, 1, 1)
        new_bday = st.date_input("Geburtsdatum", value=stored_bday, min_value=date(1920, 1, 1), max_value=date.today())
        new_target = st.number_input("Zielgewicht (kg)", value=float(settings.get("target_weight", 75.0)), format="%.1f", step=0.1)
        new_mail = st.text_input("E-Mail", value=settings.get("email", "florian.pohn@protonmail.com"))
        new_active = st.checkbox("E-Mail Aktiv", value=bool(settings.get("reminder_active", False)))
        days = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        try: day_idx = days.index(settings.get("measures_day", "Donnerstag"))
        except: day_idx = 3
        new_day = st.selectbox("Tag für Maße-Erinnerung", days, index=day_idx)
        
        if st.button("Speichern 💾"):
            updated_settings = {
                "email": new_mail, "reminder_active": new_active, "height": new_h, 
                "measures_day": new_day, "weight_daily": True, "target_weight": new_target, 
                "birthday": new_bday.strftime("%Y-%m-%d"), "last_email_kw": settings.get("last_email_kw", 0)
            }
            pd.DataFrame([updated_settings]).to_csv(SETTINGS_FILE, index=False)
            st.success("Einstellungen gespeichert! ✅")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("🚀 Erfolge teilen")
    if not df.empty:
        latest_all_f = df_filled.iloc[-1]
        h_m_f = float(settings.get("height", 179)) / 100
        bmi_val_f = float(latest_all_f['Gewicht']) / (h_m_f ** 2)
        last_7_f = df[df['Datum'] > (pd.Timestamp.now() - pd.Timedelta(days=7))]
        s_steps_f = last_7_f['Schritte'].sum()
        s_kcal_f = last_7_f['Kalorien_Out'].sum()
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
            df_daily = df_filled.groupby('Datum').agg({
                'Kalorien_In': 'sum', 
                'Kalorien_Out': 'sum', 
                'Schritte': 'sum', 
                'Gewicht': 'last',
                'Hals': 'last', 'Brust': 'last', 'Bauch': 'last', 'Oberschenkel': 'last'
            }).reset_index()

            df_p = df_daily[df_daily['Datum'] >= ten_days_ago].sort_values('Datum')
            if df_p.empty: df_p = df_daily.tail(10)
            
            latest = df_p.iloc[-1]
            h_m = float(settings.get("height", 179)) / 100
            bmi_val = float(latest['Gewicht']) / (h_m ** 2)
            bmi_cat = "Normalgewicht" if 18.5 <= bmi_val < 25 else "Übergewicht" if 25 <= bmi_val < 30 else "Adipositas" if bmi_val >= 30 else "Untergewicht"
            limit_kcal = 2300
            target_w = float(settings.get("target_weight", 75.0))
            
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

    with tab3:
        st.header("📋 Datentabelle & Verwaltung")
        if not df.empty:
            disp_view = df.sort_values(['Datum', 'Uhrzeit'], ascending=False).copy()
            disp_view['Datum'] = disp_view['Datum'].dt.strftime('%d.%m.%Y')
            st.dataframe(disp_view[['Datum', 'Uhrzeit', 'Aktivitaet', 'Schritte', 'Gewicht', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel']], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("💾 Datensicherung (Excel)")
            exp_col, imp_col = st.columns(2)
            with exp_col:
                st.write("Daten als Excel-Liste herunterladen:")
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.sort_values(['Datum', 'Uhrzeit'], ascending=False).to_excel(writer, index=False, sheet_name='FitnessData')
                excel_data = output.getvalue()
                st.download_button(label="📥 Excel Export", data=excel_data, file_name=f"fitness_hub_export_{date.today()}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with imp_col:
                st.write("Alte Daten aus Excel hochladen:")
                uploaded_file = st.file_uploader("Excel Datei wählen (.xlsx)", type="xlsx")
                if uploaded_file is not None:
                    try:
                        imp_df = pd.read_excel(uploaded_file)
                        imp_df['Datum'] = pd.to_datetime(imp_df['Datum'])
                        df = pd.concat([df, imp_df]).drop_duplicates(subset=['Datum', 'Uhrzeit'], keep='last')
                        df.to_csv(DATA_FILE, index=False)
                        st.success("✅ Daten erfolgreich importiert!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler beim Import: {e}")

            st.markdown("---")
            edit_col, delete_col = st.columns(2)
            with edit_col:
                st.subheader("✏️ Eintrag korrigieren")
                df_sorted_e = df.sort_values(['Datum', 'Uhrzeit'], ascending=False)
                options_e = {f"{row['Datum'].strftime('%d.%m.%Y')} {row['Uhrzeit']}": idx for idx, row in df_sorted_e.iterrows()}
                selected_label = st.selectbox("Eintrag wählen", list(options_e.keys()), key="edit_sel")
                selected_idx = options_e[selected_label]
                row_to_edit = df.loc[selected_idx]
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
                        df.at[selected_idx, 'Datum'] = pd.to_datetime(e_d)
                        df.at[selected_idx, 'Uhrzeit'] = e_t
                        df.at[selected_idx, 'Aktivitaet'] = e_act
                        df.at[selected_idx, 'Gewicht'] = e_gew
                        df.at[selected_idx, 'Schritte'] = e_step
                        df.at[selected_idx, 'Kalorien_In'] = e_kin
                        df.at[selected_idx, 'Kalorien_Out'] = e_kout
                        df.at[selected_idx, 'Bemerkung'] = e_note
                        df.at[selected_idx, 'Hals'] = e_hals
                        df.at[selected_idx, 'Brust'] = e_brust
                        df.at[selected_idx, 'Bauch'] = e_bauch
                        df.at[selected_idx, 'Oberschenkel'] = e_bein
                        df.to_csv(DATA_FILE, index=False)
                        st.success("Eintrag aktualisiert!")
                        st.rerun()

            with delete_col:
                st.subheader("🗑️ Eintrag löschen")
                df_sorted_d = df.sort_values(['Datum', 'Uhrzeit'], ascending=False)
                options_d = {f"{row['Datum'].strftime('%d.%m.%Y')} {row['Uhrzeit']}": idx for idx, row in df_sorted_d.iterrows()}
                del_label = st.selectbox("Löschen wählen", list(options_d.keys()), key="del_sel")
                if st.button("⚠️ Endgültig löschen"):
                    df = df.drop(options_d[del_label])
                    df.to_csv(DATA_FILE, index=False)
                    st.rerun()
