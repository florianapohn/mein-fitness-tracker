# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os

# --- 1. LOGIN & GAST-SYSTEM ---
def check_access():
    # Prüfen, ob der Gast-Modus über die URL aktiviert wurde (?view=guest)
    query_params = st.query_params
    is_guest = query_params.get("view") == "guest"
    
    if is_guest:
        st.session_state["access_level"] = "guest"
        return True

    def password_entered():
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
        st.info("Hinweis: Gast-Zugang nur über speziellen Link möglich.")
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
    access_level = st.session_state.get("access_level", "guest")
    
    # --- 2. APP KONFIGURATION ---
    st.set_page_config(page_title="My Fitness Hub", layout="wide")
    st.title("🏆 My All-in-One Fitness Hub ⚡")
    if access_level == "guest":
        st.info("👁️ Du befindest dich im Gast-Modus (Nur Lesezugriff)")

    # --- 3. DATEI-HANDLING ---
    DATA_FILE = "fitness_data.csv"
    SETTINGS_FILE = "user_settings.csv"

    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df['Datum'] = pd.to_datetime(df['Datum'])
    else:
        df = pd.DataFrame(columns=['Datum', 'Uhrzeit', 'Gewicht', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Bemerkung'])

    if os.path.exists(SETTINGS_FILE):
        try: settings = pd.read_csv(SETTINGS_FILE).iloc[0].to_dict()
        except: settings = {"height": 180, "email": "User"}
    else:
        settings = {"height": 180, "email": "User"}

    # --- 4. SEITENLEISTE ---
    # EINGABE NUR FÜR ADMINS SICHTBAR
    if access_level == "admin":
        st.sidebar.header(f"Admin: {settings.get('email')}")
        with st.sidebar.form("entry_form", clear_on_submit=True):
            d = st.date_input("Datum auswählen", date.today())
            c1, c2 = st.columns(2)
            gew = c1.number_input("Gewicht (kg)", format="%.1f", min_value=0.0)
            step = c2.number_input("Schritte", step=100, min_value=0)
            k_in = c1.number_input("Kalorien (In)", step=50, min_value=0)
            k_out = c2.number_input("Kalorien (Out)", step=50, min_value=0)
            akt = st.number_input("Aktivzeit (Min)", step=5, min_value=0)
            note = st.text_input("📝 Bemerkung")
            submit = st.form_submit_button("Speichern ✨")

        if submit:
            # (Speicher-Logik bleibt identisch wie zuvor)
            now_t, in_d = datetime.now().strftime("%H:%M"), pd.to_datetime(d)
            new_row = {'Datum': in_d, 'Uhrzeit': now_t, 'Gewicht': gew, 'Schritte': step, 'Aktivzeit': akt, 'Kalorien_In': k_in, 'Kalorien_Out': k_out, 'Bemerkung': note}
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.rerun()

        # TEILEN BUTTON FÜR ADMINS
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔗 Gast-Zugang teilen")
        guest_url = "https://mein-fitness-tracker.streamlit.app/?view=guest"
        if st.sidebar.button("Gast-Link kopieren 📋"):
            st.sidebar.code(guest_url)
            st.sidebar.success("Link oben kopieren!")
        
        if st.sidebar.button("Logout 🚪"):
            st.session_state["password_correct"] = False
            st.rerun()
    else:
        st.sidebar.warning("🔐 Gast-Modus: Keine Eingabe möglich.")

    # --- 5. HAUPTBEREICH (Visualisierung für beide sichtbar) ---
    t1, t2 = st.tabs(["Kurven & Trends 📈", "Datentabelle 📋"])

    with t1:
        if not df.empty:
            df_p = df.sort_values(['Datum', 'Uhrzeit'])
            latest = df_p.iloc[-1]
            
            # BMI Anzeige (wie bisher)
            h_m = float(settings.get("height", 180)) / 100
            bmi_val = float(latest['Gewicht']) / (h_m ** 2)
            st.subheader(f"🧬 Aktueller BMI: {bmi_val:.1f}")

            # Graphen (wie bisher)
            c1, c2 = st.columns(2)
            fig_w = px.line(df_p, x='Datum', y='Gewicht', title="Gewichtsverlauf")
            c1.plotly_chart(fig_w, use_container_width=True)
            
            fig_s = px.bar(df_p, x='Datum', y='Schritte', title="Schritte")
            c2.plotly_chart(fig_s, use_container_width=True)

    with t2:
        if not df.empty:
            st.subheader("🗓️ Historie")
            # Im Gastmodus werden sensible Spalten wie E-Mail oder genaue Maße (falls gewünscht) ausgeblendet
            disp_cols = ['Datum', 'Schritte', 'Gewicht', 'Bemerkung']
            st.dataframe(df[disp_cols].sort_values('Datum', ascending=False), use_container_width=True, hide_index=True)
