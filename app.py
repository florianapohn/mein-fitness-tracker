# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import os

# --- 1. LOGIN SYSTEM ---
def check_password():
    def password_entered():
        if st.session_state["username"] == "florian.pohn@protonmail.com" and st.session_state["password"] == "K2yupbo1":
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
            settings = {"email": "florian.pohn@protonmail.com", "reminder_active": False, "weight_daily": True, "measures_day": "Donnerstag", "height": 179, "target_weight": 75.0, "birthday": "1990-01-01"}
    else:
        settings = {"email": "florian.pohn@protonmail.com", "reminder_active": False, "weight_daily": True, "measures_day": "Donnerstag", "height": 179, "target_weight": 75.0, "birthday": "1990-01-01"}

    # --- LOGIK: WERTE AUFFÜLLEN (FORWARD FILL) ---
    df_filled = df.sort_values(['Datum', 'Uhrzeit']).copy()
    cols_to_fill = ['Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Gewicht']
    for col in cols_to_fill:
        df_filled[col] = df_filled[col].replace(0, pd.NA)
        df_filled[col] = df_filled[col].ffill().fillna(0)

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
            updated_settings = {"email": new_mail, "reminder_active": new_active, "height": new_h, "measures_day": new_day, "weight_daily": True, "target_weight": new_target, "birthday": new_bday.strftime("%Y-%m-%d")}
            pd.DataFrame([updated_settings]).to_csv(SETTINGS_FILE, index=False)
            st.success("Einstellungen gespeichert! ✅")
            st.rerun()

    # --- NEU EINGEFÜGT: TEILEN & LOGOUT ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("🚀 Erfolge teilen")
    if not df.empty:
        latest_all = df_filled.iloc[-1]
        h_m = float(settings.get("height", 179)) / 100
        bmi_val = float(latest_all['Gewicht']) / (h_m ** 2)
        last_7 = df[df['Datum'] > (pd.Timestamp.now() - pd.Timedelta(days=7))]
        s_steps = last_7['Schritte'].sum()
        s_kcal = last_7['Kalorien_Out'].sum()
        s_km = s_steps / 1400

        if st.sidebar.button("Erfolg kopieren 📋"):
            st.sidebar.code(f"Hey, schau mal! 🏆\nGewicht: {latest_all['Gewicht']:.1f} kg\nBMI: {bmi_val:.1f}\n\nLetzte 7 Tage:\n🔥 {s_kcal:,} kcal\n🏃‍♂️ {s_km:.1f} km\n👣 {s_steps:,} Schritte", language="text")

    if st.sidebar.button("Logout 🚪"):
        st.session_state.clear()
        st.rerun()

    # --- 6. HAUPTBEREICH ---
    tab1, tab2, tab3 = st.tabs(["Kurven & Trends 📈", "Langzeit-Statistik 📊", "Datentabelle 📋"])

    with tab1:
        if not df_filled.empty:
            ten_days_ago = pd.Timestamp.now() - pd.Timedelta(days=10)
            df_p = df_filled[df_filled['Datum'] >= ten_days_ago].sort_values(['Datum', 'Uhrzeit'])
            if df_p.empty: df_p = df_filled.tail(10)
            
            latest = df_p.iloc[-1]
            h_m = float(settings.get("height", 179)) / 100
            bmi_val = float(latest['Gewicht']) / (h_m ** 2)
            bmi_cat = "Normalgewicht" if 18.5 <= bmi_val < 25 else "Übergewicht" if 25 <= bmi_val < 30 else "Adipositas" if bmi_val >= 30 else "Untergewicht"
            limit_kcal = 2300
            target_w = float(settings.get("target_weight", 75.0))
            
            # Reihe 1: Gewicht
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
            # Reihe 2: Kalorien
            st.subheader("🥗 Kalorien-Haushalt")
            netto_kcal = latest['Kalorien_In'] - latest['Kalorien_Out']
            diff_to_limit = limit_kcal - latest['Kalorien_In']
            c_m, c_g = st.columns([0.25, 0.75])
            with c_m:
                st.metric("Aufgenommen", f"{latest['Kalorien_In']} kcal")
                st.metric("Übrig", f"{diff_to_limit} kcal", delta_color="normal" if diff_to_limit >= 0 else "inverse")
                st.metric("Netto-Bilanz", f"{netto_kcal} kcal")
            with c_g:
                fig_c = px.bar(df_p, x='Datum', y=['Kalorien_In', 'Kalorien_Out'], barmode='group')
                fig_c.add_hline(y=limit_kcal, line_dash="dot", line_color="red")
                fig_c.update_layout(height=350, margin=dict(l=0,r=0,t=20,b=0))
                st.plotly_chart(fig_c, use_container_width=True, config={'staticPlot': True})

            st.markdown("---")
            # Reihe 3: Maße Trend
            st.subheader("📏 Körpermaße Trend")
            def get_trend_icon(current, previous):
                if current > previous: return "🔺", "red"
                elif current < previous: return "🔻", "green"
                else: return "➖", "yellow"

            prev_row = df_filled.iloc[-2] if len(df_filled) >= 2 else latest
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
            periods = {"Woche": 7, "Monat": 30, "Quartal": 90, "Jahr": 365}
            for title, days in periods.items():
                p_df = df_filled[df_filled['Datum'] >= (now - pd.Timedelta(days=days))].sort_values('Datum')
                if not p_df.empty:
                    st.subheader(f"Letzte(r) {title}")
                    c1, c2, c3, c4 = st.columns([1,1,1,1.5])
                    c1.metric("👣 Schritte", f"{int(p_df['Schritte'].sum()):,}")
                    w_diff = p_df.iloc[-1]['Gewicht'] - p_df.iloc[0]['Gewicht']
                    c2.metric("⚖️ Gewicht", f"{p_df.iloc[-1]['Gewicht']:.1f} kg", f"{w_diff:+.1f} kg", delta_color="inverse")
                    c3.metric("🔥 Kalorien Out", f"{int(p_df['Kalorien_Out'].sum()):,}")
                    with c4:
                        st.markdown("**📏 Maße (Diff):**")
                        for m in ['Hals', 'Brust', 'Bauch', 'Oberschenkel']:
                            d = p_df.iloc[-1][m] - p_df.iloc[0][m]
                            st.write(f"{m}: {d:+.1f} cm")
                    st.markdown("---")

    with tab3:
        st.header("📋 Datentabelle & Verwaltung")
        if not df.empty:
            disp_view = df_filled.sort_values(['Datum', 'Uhrzeit'], ascending=False).copy()
            disp_view['Datum'] = disp_view['Datum'].dt.strftime('%d.%m.%Y')
            st.dataframe(disp_view[['Datum', 'Uhrzeit', 'Aktivitaet', 'Schritte', 'Gewicht', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel']], use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("🗑️ Eintrag löschen")
            df_sorted = df.sort_values(['Datum', 'Uhrzeit'], ascending=False)
            options = {f"{row['Datum'].strftime('%d.%m.%Y')} {row['Uhrzeit']}": idx for idx, row in df_sorted.iterrows()}
            del_label = st.selectbox("Löschen wählen", list(options.keys()))
            if st.button("⚠️ Endgültig löschen"):
                df = df.drop(options[del_label])
                df.to_csv(DATA_FILE, index=False)
                st.rerun()
