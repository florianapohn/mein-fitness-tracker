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
    return st.session_state["password_correct"]

if check_password():
    # --- 2. KONFIGURATION ---
    st.set_page_config(page_title="My Fitness Hub", layout="wide")
    st.title("🏆 My All-in-One Fitness Hub ⚡")

    DATA_FILE = "fitness_data.csv"
    SETTINGS_FILE = "user_settings.csv"

    # Daten laden & Reparieren
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df['Datum'] = pd.to_datetime(df['Datum'])
        needed_cols = {'Schritte': 0, 'Kalorien_Out': 0, 'Gewicht': 0.0, 'Uhrzeit': "00:00", 'Bemerkung': ""}
        for col, default in needed_cols.items():
            if col not in df.columns: df[col] = default
    else:
        df = pd.DataFrame(columns=['Datum', 'Uhrzeit', 'Gewicht', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Bemerkung'])

    if os.path.exists(SETTINGS_FILE):
        try: settings = pd.read_csv(SETTINGS_FILE).iloc[0].to_dict()
        except: settings = {"height": 180, "email": "User"}
    else:
        settings = {"height": 180, "email": "User"}

    # --- 3. SEITENLEISTE ---
    st.sidebar.header(f"Hallo Florian!")
    with st.sidebar.form("entry_form", clear_on_submit=True):
        d = st.date_input("Datum", date.today())
        c1, c2 = st.columns(2)
        gew = c1.number_input("Gewicht (kg)", format="%.1f")
        step = c2.number_input("Schritte", step=100)
        k_in = c1.number_input("Kalorien In", step=50)
        k_out = c2.number_input("Kalorien Out", step=50)
        note = st.text_input("📝 Bemerkung")
        submit = st.form_submit_button("Speichern ✨")

    if submit:
        new_row = {'Datum': pd.to_datetime(d), 'Uhrzeit': datetime.now().strftime("%H:%M"), 'Gewicht': gew, 'Schritte': step, 'Kalorien_In': k_in, 'Kalorien_Out': k_out, 'Bemerkung': note}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.rerun()

    # --- 4. TEILEN LOGIK (ERFOLGE GENERIEREN) ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("🚀 Erfolge teilen")
    
    if not df.empty:
        # Berechnungen
        latest = df.sort_values(['Datum', 'Uhrzeit']).iloc[-1]
        h_m = float(settings.get("height", 180)) / 100
        bmi_val = float(latest['Gewicht']) / (h_m ** 2)
        
        # Wochendaten (letzte 7 Tage)
        last_7_days = df[df['Datum'] > (pd.Timestamp.now() - pd.Timedelta(days=7))]
        sum_steps = last_7_days['Schritte'].sum()
        sum_kcal_out = last_7_days['Kalorien_Out'].sum()
        # Faustformel: 1400 Schritte ca 1 KM
        sum_km = sum_steps / 1400

        # Der fertige Text
        share_text = f"""Hey, schau mal, ich habe einen weiteren Meilenstein erreicht! 🏆
Mein aktuelles Gewicht: {latest['Gewicht']:.1f} kg
Mein BMI: {bmi_val:.1f}

Meine Erfolge der letzten 7 Tage:
🔥 Verbrannte Kalorien: {sum_kcal_out:,} kcal
🏃‍♂️ Zurückgelegte Strecke: {sum_km:.1f} km
👣 Gesamtschritte: {sum_steps:,}

Bleib dran! 💪✨"""

        if st.sidebar.button("Erfolg kopieren 📋"):
            st.sidebar.code(share_text, language="text")
            st.sidebar.success("Text oben kopieren & teilen!")

    if st.sidebar.button("Logout 🚪"):
        st.session_state.clear()
        st.rerun()

    # --- 5. HAUPTBEREICH ---
    t1, t2 = st.tabs(["Kurven & Trends 📈", "Datentabelle 📋"])

    with t1:
        if not df.empty:
            df_p = df.sort_values(['Datum', 'Uhrzeit'])
            # BMI Anzeige
            st.subheader(f"🧬 Aktueller BMI: {bmi_val:.1f}")
            
            # Graphen
            c1, c2 = st.columns(2)
            fig_w = px.line(df_p, x='Datum', y='Gewicht', title="Gewichtsverlauf", markers=True)
            c1.plotly_chart(fig_w, use_container_width=True)
            
            fig_s = px.bar(df_p, x='Datum', y='Schritte', title="Schritte", text_auto=True)
            c2.plotly_chart(fig_s, use_container_width=True)
            
            # Wochen-Statistik als Info-Box
            st.info(f"📊 **Statistik der letzten 7 Tage:** {sum_steps:,} Schritte | {sum_km:.1f} km | {sum_kcal_out:,} kcal verbrannt")
            
    with t2:
        if not df.empty:
            st.dataframe(df.sort_values(['Datum', 'Uhrzeit'], ascending=False), use_container_width=True, hide_index=True)
