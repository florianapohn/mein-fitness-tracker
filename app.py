# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os

# 1. App Konfiguration
st.set_page_config(page_title="My Fitness Hub", layout="wide")
st.title("🏆 My All-in-One Fitness Hub ⚡")

# 2. Datei-Handling
DATA_FILE = "fitness_data.csv"
SETTINGS_FILE = "user_settings.csv"

# Fitness-Daten laden
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    df['Datum'] = pd.to_datetime(df['Datum'])
else:
    columns = ['Datum', 'Uhrzeit', 'Gewicht', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Bemerkung']
    df = pd.DataFrame(columns=columns)

# Einstellungen laden (inkl. Körpergröße)
if os.path.exists(SETTINGS_FILE):
    try:
        settings = pd.read_csv(SETTINGS_FILE).iloc[0].to_dict()
    except:
        settings = {"email": "", "reminder_active": False, "weight_daily": True, "measures_day": "Donnerstag", "height": 180}
else:
    settings = {"email": "", "reminder_active": False, "weight_daily": True, "measures_day": "Donnerstag", "height": 180}

# 3. SEITENLEISTE: Dateneingabe
st.sidebar.header("📥 Neue Daten eintragen")
with st.sidebar.form("entry_form", clear_on_submit=True):
    d = st.date_input("Datum auswählen", date.today())
    
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        gew = st.number_input("Gewicht (kg)", format="%.1f", min_value=0.0)
        step = st.number_input("Schritte", step=100, min_value=0)
    with col_in2:
        k_in = st.number_input("Kalorien (In)", step=50, min_value=0)
        k_out = st.number_input("Kalorien (Out)", step=50, min_value=0)
    
    akt = st.number_input("Aktivzeit (Min)", step=5, min_value=0)
    note = st.text_input("📝 Bemerkung", placeholder="Urlaub, Krank, Feier...")
    
    st.subheader("📏 Körpermaße (cm)")
    h1, h2 = st.columns(2)
    hals = h1.number_input("Hals", format="%.1f", min_value=0.0)
    brust = h2.number_input("Brust", format="%.1f", min_value=0.0)
    bauch = h1.number_input("Bauch", format="%.1f", min_value=0.0)
    bein = h2.number_input("Oberschenkel", format="%.1f", min_value=0.0)
    
    submit = st.form_submit_button("Speichern ✨")

if submit:
    now_time = datetime.now().strftime("%H:%M")
    input_date = pd.to_datetime(d)
    same_day = df[df['Datum'] == input_date]
    
    if not same_day.empty and (same_day['Gewicht'].astype(float).sum() == 0):
        idx = same_day.index[0]
        df.at[idx, 'Gewicht'] = gew
        df.at[idx, 'Schritte'] = step
        df.at[idx, 'Aktivzeit'] = akt
        df.at[idx, 'Kalorien_In'] = k_in
        df.at[idx, 'Kalorien_Out'] = k_out
        df.at[idx, 'Hals'] = hals
        df.at[idx, 'Brust'] = brust
        df.at[idx, 'Bauch'] = bauch
        df.at[idx, 'Oberschenkel'] = bein
        df.at[idx, 'Bemerkung'] = note
        df.at[idx, 'Uhrzeit'] = now_time
    else:
        new_row = {
            'Datum': input_date, 'Uhrzeit': now_time, 'Gewicht': gew, 'Schritte': step, 
            'Aktivzeit': akt, 'Kalorien_In': k_in, 'Kalorien_Out': k_out,
            'Hals': hals, 'Brust': brust, 'Bauch': bauch, 'Oberschenkel': bein, 'Bemerkung': note
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    
    df.to_csv(DATA_FILE, index=False)
    st.sidebar.success("Daten gespeichert! ✅")
    st.rerun()

# 4. SEITENLEISTE: Einstellungen & Größe
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Einstellungen")
with st.sidebar.expander("Profil & Erinnerungen"):
    cur_height = st.number_input("Körpergröße (cm)", value=int(settings.get("height", 180)), step=1)
    u_email = st.text_input("E-Mail Adresse", value=settings.get("email", ""))
    r_active = st.checkbox("E-Mail Erinnerungen aktiv", value=settings.get("reminder_active", False))
    m_day = st.selectbox("Maße-Tag", ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"], 
                         index=["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"].index(settings.get("measures_day", "Donnerstag")))
    
    if st.button("Einstellungen speichern 💾"):
        new_set = pd.DataFrame([{
            "email": u_email, 
            "reminder_active": r_active, 
            "weight_daily": settings.get("weight_daily", True), 
            "measures_day": m_day,
            "height": cur_height
        }])
        new_set.to_csv(SETTINGS_FILE, index=False)
        st.success("Profil aktualisiert!")
        st.rerun()

# 5. HAUPTBEREICH
tab1, tab2 = st.tabs(["Kurven & Trends 📈", "Datentabelle 📋"])

with tab1:
    if not df.empty:
        df_p = df.sort_values(['Datum', 'Uhrzeit'])
        latest = df_p.iloc[-1]
        
        # BMI BERECHNUNG & VISUALISIERUNG
        st.subheader("🧬 Dein BMI Status")
        height_m = float(settings.get("height", 180)) / 100
        bmi = float(latest['Gewicht']) / (height_m ** 2)
        
        # BMI Kategorisierung
        if bmi < 18.5:
            label, color, comment = "Untergewicht", "blue", "Achte darauf, genug Energie zu dir zu nehmen!"
        elif 18.5 <= bmi < 25:
            label, color, comment = "Normalgewicht", "green", "Super! Du befindest dich im Idealgewicht."
        elif 25 <= bmi < 30:
            label, color, comment = "Übergewicht", "orange", "Eine leichte Anpassung der Kalorien könnte helfen."
        else:
            label, color, comment = "Adipositas", "red", "Gesundheitliche Risiken steigen. Bleib an deinem Plan!"

        # BMI Gauge / Balken
        fig_bmi = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = bmi,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': f"BMI: {label}", 'font': {'size': 24}},
            gauge = {
                'axis': {'range': [15, 40], 'tickwidth': 1},
                'bar': {'color': "black"}, # Der "Pfeil" bzw. Balken
                'steps': [
                    {'range': [15, 18.5], 'color': "lightblue"},
                    {'range': [18.5, 25], 'color': "lightgreen"},
                    {'range': [25, 30], 'color': "orange"},
                    {'range': [30, 40], 'color': "red"}],
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 0.75,
                    'value': bmi}
            }
        ))
        fig_bmi.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig_bmi, use_container_width=True)
        st.info(f"💡 **Kommentar:** {comment}")

        st.markdown("---")

        # REIHE 1: Gewicht & Kalorien
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("⚖️ Gewichtsverlauf")
            df_p['Diff'] = df_p['Gewicht'].astype(float).diff().fillna(0)
            df_p['Farbe'] = df_p['Diff'].apply(lambda x: 'red' if x > 0 else ('green' if x < 0 else 'gray'))
            fig_w = go.Figure()
            fig_w.add_trace(go.Scatter(x=df_p['Datum'], y=df_p['Gewicht'], fill='tozeroy', mode='lines', line=dict(width=2, color='#0288D1', shape='spline'), fillcolor='rgba(2, 136, 209, 0.1)'))
            fig_w.add_trace(go.Scatter(x=df_p['Datum'], y=df_p['Gewicht'], mode='markers', marker=dict(color=df_p['Farbe'], size=8)))
            fig_w.update_layout(height=350, margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
            st.plotly_chart(fig_w, use_container_width=True)
        with c2:
            st.subheader("🔥 Kalorien: In vs. Out")
            fig_c = px.bar(df_p, x='Datum', y=['Kalorien_In', 'Kalorien_Out'], barmode='group')
            fig_c.update_layout(height=350, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig_c, use_container_width=True)

        # REIHE 2: Körpermaße
        st.markdown("---")
        st.subheader("📏 Maße & Fortschritt")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Hals 🦒", f"{latest['Hals']} cm")
        m2.metric("Brust 🦍", f"{latest['Brust']} cm")
        m3.metric("Bauch 🍕", f"{latest['Bauch']} cm")
        m4.metric("Beine 🍗", f"{latest['Oberschenkel']} cm")

        # REIHE 3: Schritte
        st.markdown("---")
        st.subheader("👣 Tägliche Schritte")
        fig_s = px.area(df_p, x='Datum', y='Schritte', color_discrete_sequence=['#FFA000'])
        fig_s.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig_s, use_container_width=True)
    else:
        st.info("Noch keine Daten vorhanden.")

with tab2:
    st.subheader("🗓️ Deine Historie")
    if not df.empty:
        disp = df.sort_values(['Datum', 'Uhrzeit'], ascending=[False, False]).copy()
        disp['Datum'] = disp['Datum'].dt.strftime('%d.%m.%Y')
        disp = disp.rename(columns={'Datum': '📅 Datum', 'Uhrzeit': '🕒 Zeit', 'Gewicht': '⚖️ kg', 'Schritte': '👣 Schritte', 'Bemerkung': '📝 Info'})
        order = ['📅 Datum', '🕒 Zeit', '⚖️ kg', '👣 Schritte', '📝 Info']
        other = [c for c in disp.columns if c not in order]
        st.dataframe(disp[order + other], use_container_width=True, hide_index=True)
