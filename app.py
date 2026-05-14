# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os

# --- 1. LOGIN & GAST-SYSTEM ---
def check_access():
    query_params = st.query_params
    is_guest = query_params.get("view") == "guest"
    
    if is_guest:
        st.session_state["access_level"] = "guest"
        st.session_state["password_correct"] = True
        return True

    def password_entered():
        # Dein festgelegter Benutzername und Passwort
        if st.session_state["username"] == "florian.pohn@protonmail.com" and st.session_state["password"] == "K2yupbo1":
            st.session_state["password_correct"] = True
            st.session_state["access_level"] = "admin"
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

if check_access():
    access_level = st.session_state.get("access_level", "admin")
    
    # --- 2. APP KONFIGURATION ---
    st.set_page_config(page_title="My Fitness Hub", layout="wide")
    st.title("🏆 My All-in-One Fitness Hub ⚡")
    if access_level == "guest":
        st.info("👁️ Du befindest dich im Gast-Modus (Nur Lesezugriff)")

    # --- 3. DATEI-HANDLING & REPARATUR ---
    DATA_FILE = "fitness_data.csv"
    SETTINGS_FILE = "user_settings.csv"

    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df['Datum'] = pd.to_datetime(df['Datum'])
        # Spalten reparieren falls nötig
        needed_cols = {'Uhrzeit': "00:00", 'Bemerkung': "", 'Schritte': 0, 'Gewicht': 0.0, 'Kalorien_In': 0, 'Kalorien_Out': 0, 'Hals': 0.0, 'Brust': 0.0, 'Bauch': 0.0, 'Oberschenkel': 0.0}
        for col, default in needed_cols.items():
            if col not in df.columns:
                df[col] = default
    else:
        df = pd.DataFrame(columns=['Datum', 'Uhrzeit', 'Gewicht', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Bemerkung'])

    # Einstellungen laden
    if os.path.exists(SETTINGS_FILE):
        try:
            settings_df = pd.read_csv(SETTINGS_FILE)
            settings = settings_df.iloc[0].to_dict()
        except:
            settings = {"height": 180, "email": "User", "reminder_active": False, "measures_day": "Donnerstag"}
    else:
        settings = {"height": 180, "email": "User", "reminder_active": False, "measures_day": "Donnerstag"}

    # --- 4. SEITENLEISTE ---
    if access_level == "admin":
        st.sidebar.header(f"Admin: {settings.get('email', 'User')}")
        
        # A) Eingabe-Formular
        with st.sidebar.form("entry_form", clear_on_submit=True):
            d = st.date_input("Datum auswählen", date.today())
            c_in1, c_in2 = st.columns(2)
            gew = c_in1.number_input("Gewicht (kg)", format="%.1f", min_value=0.0)
            step = c_in2.number_input("Schritte", step=100, min_value=0)
            k_in = c_in1.number_input("Kalorien (In)", step=50, min_value=0)
            k_out = c_in2.number_input("Kalorien (Out)", step=50, min_value=0)
            akt = st.number_input("Aktivzeit (Min)", step=5, min_value=0)
            note = st.text_input("📝 Bemerkung")
            
            st.subheader("📏 Maße (cm)")
            h1, h2 = st.columns(2)
            hals = h1.number_input("Hals", format="%.1f")
            brust = h2.number_input("Brust", format="%.1f")
            bauch = h1.number_input("Bauch", format="%.1f")
            bein = h2.number_input("Oberschenkel", format="%.1f")
            submit = st.form_submit_button("Speichern ✨")

        if submit:
            now_t, in_d = datetime.now().strftime("%H:%M"), pd.to_datetime(d)
            new_row = {'Datum': in_d, 'Uhrzeit': now_t, 'Gewicht': gew, 'Schritte': step, 'Aktivzeit': akt, 'Kalorien_In': k_in, 'Kalorien_Out': k_out, 'Hals': hals, 'Brust': brust, 'Bauch': bauch, 'Oberschenkel': bein, 'Bemerkung': note}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.rerun()

        st.sidebar.markdown("---")
        
        # B) DIE VERMISSTEN EINSTELLUNGEN (Wieder da!)
        with st.sidebar.expander("⚙️ Profil & Erinnerungen"):
            cur_h = st.number_input("Größe (cm)", value=int(settings.get("height", 180)), step=1)
            u_mail = st.text_input("E-Mail Adresse", value=settings.get("email", ""))
            r_on = st.checkbox("E-Mail Erinnerungen aktiv", value=settings.get("reminder_active", False))
            m_d = st.selectbox("Tag für Maße", ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"], 
                                 index=["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"].index(settings.get("measures_day", "Donnerstag")))
            
            if st.button("Einstellungen speichern 💾"):
                new_set = pd.DataFrame([{"email": u_mail, "reminder_active": r_on, "measures_day": m_d, "height": cur_h, "weight_daily": True}])
                new_set.to_csv(SETTINGS_FILE, index=False)
                st.sidebar.success("Gespeichert!")
                st.rerun()

        # C) Gast-Link & Logout
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔗 Gast-Link")
        st.sidebar.code("https://mein-fitness-tracker.streamlit.app/?view=guest")
        
        if st.sidebar.button("Logout 🚪"):
            st.session_state.clear()
            st.rerun()
    else:
        st.sidebar.warning("🔐 Gast-Modus: Keine Eingabe möglich.")

    # --- 5. HAUPTBEREICH (Charts & Tabelle) ---
    t1, t2 = st.tabs(["Kurven & Trends 📈", "Datentabelle 📋"])

    with t1:
        if not df.empty:
            df_p = df.sort_values(['Datum', 'Uhrzeit'])
            latest = df_p.iloc[-1]
            
            # BMI
            h_m = float(settings.get("height", 180)) / 100
            bmi_val = float(latest['Gewicht']) / (h_m ** 2)
            
            col_charts, col_bmi = st.columns([0.8, 0.2])
            with col_charts:
                c1, c2 = st.columns(2)
                # Gewicht
                fig_w = go.Figure(go.Scatter(x=df_p['Datum'], y=df_p['Gewicht'], fill='tozeroy', mode='lines+markers', line=dict(color='#0288D1', shape='spline')))
                fig_w.update_layout(height=350, margin=dict(l=0,r=0,t=0,b=0), title="⚖️ Gewicht")
                c1.plotly_chart(fig_w, use_container_width=True)
                # Kalorien
                fig_c = px.bar(df_p, x='Datum', y=['Kalorien_In', 'Kalorien_Out'], barmode='group', title="🔥 Kalorien")
                c2.plotly_chart(fig_c, use_container_width=True)

            with col_bmi:
                st.markdown(f"<h3 style='text-align: center;'>BMI: {bmi_val:.1f}</h3>", unsafe_allow_html=True)
                fig_bmi = go.Figure(go.Indicator(mode="gauge+number", value=bmi_val, gauge={'axis': {'range': [15, 40]}, 'steps': [{'range': [15, 18.5], 'color': "lightblue"}, {'range': [18.5, 25], 'color': "green"}, {'range': [25, 30], 'color': "orange"}, {'range': [30, 40], 'color': "red"}]}))
                st.plotly_chart(fig_bmi, use_container_width=True)

            # Schritte
            st.markdown("---")
            st.subheader("👣 Schritte")
            fig_s = go.Figure(go.Bar(x=df_p['Datum'], y=df_p['Schritte'], text=df_p['Schritte'], textposition='outside', marker_color='orange'))
            st.plotly_chart(fig_s, use_container_width=True)
            
            # Maße Metriken
            st.markdown("---")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("Hals", f"{latest['Hals']} cm")
            m_col2.metric("Brust", f"{latest['Brust']} cm")
            m_col3.metric("Bauch", f"{latest['Bauch']} cm")
            m_col4.metric("Beine", f"{latest['Oberschenkel']} cm")
    
    with t2:
        if not df.empty:
            st.dataframe(df.sort_values(['Datum', 'Uhrzeit'], ascending=False), use_container_width=True, hide_index=True)
