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
        needed_cols = {'Uhrzeit': "00:00", 'Bemerkung': "", 'Schritte': 0, 'Gewicht': 0.0, 'Kalorien_In': 0, 'Kalorien_Out': 0, 'Hals': 0.0, 'Brust': 0.0, 'Bauch': 0.0, 'Oberschenkel': 0.0}
        for col, default in needed_cols.items():
            if col not in df.columns:
                df[col] = default
    else:
        columns = ['Datum', 'Uhrzeit', 'Gewicht', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Bemerkung']
        df = pd.DataFrame(columns=columns)

    if os.path.exists(SETTINGS_FILE):
        try: 
            settings_data = pd.read_csv(SETTINGS_FILE)
            settings = settings_data.iloc[0].to_dict()
        except: 
            settings = {"email": "florian.pohn@protonmail.com", "reminder_active": False, "weight_daily": True, "measures_day": "Donnerstag", "height": 179}
    else:
        settings = {"email": "florian.pohn@protonmail.com", "reminder_active": False, "weight_daily": True, "measures_day": "Donnerstag", "height": 179}

    # --- 4. SEITENLEISTE: DATENEINGABE ---
    st.sidebar.header(f"Hallo Florian!")
    with st.sidebar.form("entry_form", clear_on_submit=True):
        d = st.date_input("Datum auswählen", date.today())
        c_in1, c_in2 = st.columns(2)
        with c_in1:
            gew = st.number_input("Gewicht (kg)", format="%.1f", min_value=0.0)
            step = st.number_input("Schritte", step=100, min_value=0)
        with c_in2:
            k_in = st.number_input("Kalorien (In)", step=50, min_value=0)
            k_out = st.number_input("Kalorien (Out)", step=50, min_value=0)
        
        akt = st.number_input("Aktivzeit (Min)", step=5, min_value=0)
        note = st.text_input("📝 Bemerkung", placeholder="Urlaub, Krank, Feier...")
        
        st.subheader("📏 Körpermaße (cm)")
        h1, h2 = st.columns(2)
        hals_in = h1.number_input("Hals", format="%.1f")
        brust_in = h2.number_input("Brust", format="%.1f")
        bauch_in = h1.number_input("Bauch", format="%.1f")
        bein_in = h2.number_input("Oberschenkel", format="%.1f")
        submit = st.form_submit_button("Speichern ✨")

    if submit:
        now_t, in_d = datetime.now().strftime("%H:%M"), pd.to_datetime(d)
        new_row = {'Datum': in_d, 'Uhrzeit': now_t, 'Gewicht': gew, 'Schritte': step, 'Aktivzeit': akt, 'Kalorien_In': k_in, 'Kalorien_Out': k_out, 'Hals': hals_in, 'Brust': brust_in, 'Bauch': bauch_in, 'Oberschenkel': bein_in, 'Bemerkung': note}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.rerun()

    # --- 5. SEITENLEISTE: EINSTELLUNGEN & EXTRAS ---
    st.sidebar.markdown("---")
    with st.sidebar.expander("⚙️ Profil & Erinnerungen"):
        new_h = st.number_input("Größe (cm)", value=int(settings.get("height", 179)), step=1)
        new_mail = st.text_input("E-Mail", value=settings.get("email", "florian.pohn@protonmail.com"))
        new_active = st.checkbox("E-Mail Aktiv", value=bool(settings.get("reminder_active", False)))
        
        days = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        try: day_idx = days.index(settings.get("measures_day", "Donnerstag"))
        except: day_idx = 3
            
        new_day = st.selectbox("Tag für Maße-Erinnerung", days, index=day_idx)
        
        if st.button("Speichern 💾"):
            updated_settings = {"email": new_mail, "reminder_active": new_active, "height": new_h, "measures_day": new_day, "weight_daily": True}
            pd.DataFrame([updated_settings]).to_csv(SETTINGS_FILE, index=False)
            st.success("Einstellungen gespeichert! ✅")
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("🚀 Erfolge teilen")
    if not df.empty:
        latest = df.sort_values(['Datum', 'Uhrzeit']).iloc[-1]
        h_m = float(settings.get("height", 179)) / 100
        bmi_val = float(latest['Gewicht']) / (h_m ** 2)
        
        last_7 = df[df['Datum'] > (pd.Timestamp.now() - pd.Timedelta(days=7))]
        s_steps = last_7['Schritte'].sum()
        s_kcal = last_7['Kalorien_Out'].sum()
        s_km = s_steps / 1400

        if st.sidebar.button("Erfolg kopieren 📋"):
            st.sidebar.code(f"Hey, schau mal! 🏆\nGewicht: {latest['Gewicht']:.1f} kg\nBMI: {bmi_val:.1f}\n\nLetzte 7 Tage:\n🔥 {s_kcal:,} kcal\n🏃‍♂️ {s_km:.1f} km\n👣 {s_steps:,} Schritte", language="text")

    if st.sidebar.button("Logout 🚪"):
        st.session_state.clear()
        st.rerun()

    # --- 6. HAUPTBEREICH ---
    tab1, tab2, tab3 = st.tabs(["Kurven & Trends 📈", "Langzeit-Statistik 📊", "Datentabelle 📋"])

    with tab1:
        if not df.empty:
            ten_days_ago = pd.Timestamp.now() - pd.Timedelta(days=10)
            df_10d = df[df['Datum'] >= ten_days_ago].sort_values(['Datum', 'Uhrzeit'])
            df_p = df_10d if not df_10d.empty else df.sort_values(['Datum', 'Uhrzeit'])

            bmi_cat = "Normalgewicht" if 18.5 <= bmi_val < 25 else "Übergewicht" if 25 <= bmi_val < 30 else "Adipositas" if bmi_val >= 30 else "Untergewicht"
            
            # Reihe 1: Gewicht & Kalorien (Handy-optimiert)
            c1, c2 = st.columns(2)
            with c1:
                fig_w = go.Figure(go.Scatter(x=df_p['Datum'], y=df_p['Gewicht'], fill='tozeroy', mode='lines+markers', line=dict(width=2, color='#0288D1', shape='spline')))
                fig_w.update_layout(height=350, margin=dict(l=0,r=0,t=40,b=0), title="⚖️ Gewichtsverlauf (10 Tage)")
                st.plotly_chart(fig_w, use_container_width=True, config={'staticPlot': True})
            with c2:
                fig_c = px.bar(df_p, x='Datum', y=['Kalorien_In', 'Kalorien_Out'], barmode='group')
                fig_c.update_layout(height=350, margin=dict(l=0,r=0,t=40,b=0), title="🔥 Kalorienvergleich (10 Tage)")
                st.plotly_chart(fig_c, use_container_width=True, config={'staticPlot': True})

            st.markdown("---")

            # Reihe 2: Schritte & BMI (Handy-optimiert)
            col_steps, col_bmi_gauge = st.columns([0.7, 0.3])
            with col_steps:
                fig_s = go.Figure(go.Bar(x=df_p['Datum'], y=df_p['Schritte'], marker_color='lightblue', text=df_p['Schritte'], textposition='outside'))
                fig_s.add_hline(y=10000, line_dash="dash", line_color="white")
                fig_s.update_layout(height=400, margin=dict(l=0,r=0,t=40,b=0), title="👣 Tägliche Schritte (10 Tage)")
                st.plotly_chart(fig_s, use_container_width=True, config={'staticPlot': True})
            
            with col_bmi_gauge:
                st.markdown(f"<h3 style='text-align: center; margin-bottom: 0;'>{bmi_cat}</h3>", unsafe_allow_html=True)
                fig_bmi = go.Figure(go.Indicator(mode="gauge+number", value=bmi_val, number={'valueformat': ".1f"},
                    gauge={'axis': {'range': [15, 40]}, 'bar': {'color': "white"},
                        'steps': [{'range': [15, 18.5], 'color': "#3498db"}, {'range': [18.5, 25], 'color': "#2ecc71"}, {'range': [25, 30], 'color': "#f1c40f"}, {'range': [30, 40], 'color': "#e74c3c"}]}))
                fig_bmi.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_bmi, use_container_width=True, config={'staticPlot': True})

            st.info(f"📊 **Letzte 7 Tage:** {s_steps:,} Schritte | {s_km:.1f} km | {s_kcal:,} kcal verbrannt")
            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Hals🦒", f"{latest['Hals']} cm")
            m2.metric("Brust🦍", f"{latest['Brust']} cm")
            m3.metric("Bauch🍕", f"{latest['Bauch']} cm")
            m4.metric("Beine🍗", f"{latest['Oberschenkel']} cm")

    with tab2:
        st.header("📊 Deine Langzeit-Entwicklung")
        if not df.empty:
            now = pd.Timestamp.now()
            periods = {
                "Diese Woche": now - pd.Timedelta(days=7),
                "Dieser Monat": now - pd.Timedelta(days=30),
                "Dieses Quartal": now - pd.Timedelta(days=90),
                "Dieses Jahr": now - pd.Timedelta(days=365)
            }

            for title, start_date in periods.items():
                mask = df['Datum'] >= start_date
                p_df = df[mask].sort_values('Datum')
                
                if not p_df.empty:
                    st.subheader(title)
                    col_base, col_details = st.columns([3, 1])
                    with col_base:
                        c1, c2, c3 = st.columns(3)
                        t_steps = int(p_df['Schritte'].sum())
                        t_km = t_steps / 1400
                        c1.metric("👣 Schritte", f"{t_steps:,}", f"{t_km:.1f} km")
                        c2.metric("🔥 Kalorien Out", f"{int(p_df['Kalorien_Out'].sum()):,} kcal")
                        w_diff = p_df.iloc[-1]['Gewicht'] - p_df.iloc[0]['Gewicht']
                        c3.metric("⚖️ Gewicht", f"{p_df.iloc[-1]['Gewicht']:.1f} kg", f"{w_diff:+.1f} kg", delta_color="inverse")
                    
                    with col_details:
                        st.markdown("**📏 Maße (Diff):**")
                        m_list = {"Hals": "Hals", "Brust": "Brust", "Bauch": "Bauch", "Beine": "Oberschenkel"}
                        for label, key in m_list.items():
                            diff = p_df.iloc[-1][key] - p_df.iloc[0][key]
                            color = "green" if diff <= 0 else "red"
                            st.markdown(f"{label}: <span style='color:{color}; font-weight:bold;'>{diff:+.1f} cm</span>", unsafe_allow_html=True)
                    st.markdown("---")

    with tab3:
        if not df.empty:
            disp = df.sort_values(['Datum', 'Uhrzeit'], ascending=[False, False]).copy()
            disp['Datum'] = disp['Datum'].dt.strftime('%d.%m.%Y')
            st.dataframe(disp[['Datum', 'Uhrzeit', 'Schritte', 'Gewicht', 'Bemerkung', 'Hals', 'Brust', 'Bauch', 'Oberschenkel']], use_container_width=True, hide_index=True)
