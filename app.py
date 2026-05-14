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

if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    df['Datum'] = pd.to_datetime(df['Datum'])
    if 'Uhrzeit' not in df.columns: df['Uhrzeit'] = "00:00"
    if 'Bemerkung' not in df.columns: df['Bemerkung'] = ""
else:
    columns = ['Datum', 'Uhrzeit', 'Gewicht', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Bemerkung']
    df = pd.DataFrame(columns=columns)

if os.path.exists(SETTINGS_FILE):
    try: settings = pd.read_csv(SETTINGS_FILE).iloc[0].to_dict()
    except: settings = {"email": "", "reminder_active": False, "weight_daily": True, "measures_day": "Donnerstag", "height": 180}
else:
    settings = {"email": "", "reminder_active": False, "weight_daily": True, "measures_day": "Donnerstag", "height": 180}

# 3. SEITENLEISTE: Dateneingabe
st.sidebar.header("📥 Neue Daten eintragen")
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
    hals, brust = h1.number_input("Hals", format="%.1f"), h2.number_input("Brust", format="%.1f")
    bauch, bein = h1.number_input("Bauch", format="%.1f"), h2.number_input("Oberschenkel", format="%.1f")
    submit = st.form_submit_button("Speichern ✨")

if submit:
    now_t, in_d = datetime.now().strftime("%H:%M"), pd.to_datetime(d)
    same_d = df[df['Datum'] == in_d]
    if not same_d.empty and (same_d['Gewicht'].astype(float).sum() == 0):
        idx = same_d.index[0]
        for val, col in zip([gew, step, akt, k_in, k_out, hals, brust, bauch, bein, note, now_t], ['Gewicht', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Bemerkung', 'Uhrzeit']):
            df.at[idx, col] = val
    else:
        new_row = {'Datum': in_d, 'Uhrzeit': now_t, 'Gewicht': gew, 'Schritte': step, 'Aktivzeit': akt, 'Kalorien_In': k_in, 'Kalorien_Out': k_out, 'Hals': hals, 'Brust': brust, 'Bauch': bauch, 'Oberschenkel': bein, 'Bemerkung': note}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    st.rerun()

# 4. SEITENLEISTE: Einstellungen
st.sidebar.markdown("---")
with st.sidebar.expander("⚙️ Profil & Erinnerungen"):
    cur_h = st.number_input("Größe (cm)", value=int(settings.get("height", 180)), step=1)
    u_mail = st.text_input("E-Mail", value=settings.get("email", ""))
    r_on = st.checkbox("E-Mail Aktiv", value=settings.get("reminder_active", False))
    m_d = st.selectbox("Maße-Tag", ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"], index=3)
    if st.button("Speichern 💾"):
        pd.DataFrame([{"email": u_mail, "reminder_active": r_on, "measures_day": m_d, "height": cur_h, "weight_daily": True}]).to_csv(SETTINGS_FILE, index=False)
        st.rerun()

# 5. HAUPTBEREICH
t1, t2 = st.tabs(["Kurven & Trends 📈", "Datentabelle 📋"])

with t1:
    if not df.empty:
        df_p = df.sort_values(['Datum', 'Uhrzeit'])
        latest = df_p.iloc[-1]
        
        # BMI
        h_m = float(settings.get("height", 180)) / 100
        bmi_val = float(latest['Gewicht']) / (h_m ** 2)
        if bmi_val < 18.5: bmi_cat = "Untergewicht"
        elif 18.5 <= bmi_val < 25: bmi_cat = "Normalgewicht"
        elif 25 <= bmi_val < 30: bmi_cat = "Übergewicht"
        else: bmi_cat = "Adipositas"
        
        col_charts, col_bmi = st.columns([0.8, 0.2])
        with col_charts:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("⚖️ Gewicht")
                fig_w = go.Figure()
                fig_w.add_trace(go.Scatter(x=df_p['Datum'], y=df_p['Gewicht'], fill='tozeroy', mode='lines+markers', line=dict(width=2, color='#0288D1', shape='spline'), fillcolor='rgba(2, 136, 209, 0.1)'))
                fig_w.update_layout(height=350, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig_w, use_container_width=True)
            with c2:
                st.subheader("🔥 Kalorien")
                fig_c = px.bar(df_p, x='Datum', y=['Kalorien_In', 'Kalorien_Out'], barmode='group')
                fig_c.update_layout(height=350, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig_c, use_container_width=True)

        with col_bmi:
            st.markdown(f"<h3 style='text-align: center;'>🧬 {bmi_cat}</h3>", unsafe_allow_html=True)
            fig_bmi = go.Figure(go.Indicator(
                mode = "gauge+number", value = bmi_val,
                number = {'font': {'size': 20}, 'valueformat': ".1f"},
                gauge = {
                    'axis': {'range': [15, 40]},
                    'bar': {'color': "white", 'thickness': 0.25},
                    'steps': [
                        {'range': [15, 18.5], 'color': "#3498db"},
                        {'range': [18.5, 25], 'color': "#2ecc71"},
                        {'range': [25, 30], 'color': "#f1c40f"},
                        {'range': [30, 40], 'color': "#e74c3c"}]
                }
            ))
            fig_bmi.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_bmi, use_container_width=True)

        # REIHE 2: Schritte mit Werten auf den Balken
        st.markdown("---")
        st.subheader("👣 Tägliche Schritte (Ziel: 10.000)")
        def get_step_color(s):
            if s >= 10000: return 'green'
            if s >= 9000:  return 'lightblue'
            if s >= 5000:  return 'orange'
            return 'red'
        
        df_p['Step_Color'] = df_p['Schritte'].apply(get_step_color)
        
        fig_s = go.Figure(go.Bar(
            x=df_p['Datum'], 
            y=df_p['Schritte'], 
            marker_color=df_p['Step_Color'],
            text=df_p['Schritte'],           # Der Text, der angezeigt werden soll
            textposition='outside',          # Text ÜBER den Balken schreiben
            name="Schritte"
        ))
        fig_s.add_hline(y=10000, line_dash="dash", line_color="white", annotation_text="Ziel 10k")
        fig_s.update_layout(height=400, margin=dict(l=0,r=0,t=30,b=0), uniformtext_minsize=8, uniformtext_mode='hide')
        st.plotly_chart(fig_s, use_container_width=True)
        
        # REIHE 3: Maße
        st.markdown("---")
        st.subheader("📏 Aktuelle Maße")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Hals", f"{latest['Hals']} cm")
        m2.metric("Brust", f"{latest['Brust']} cm")
        m3.metric("Bauch", f"{latest['Bauch']} cm")
        m4.metric("Beine", f"{latest['Oberschenkel']} cm")
    else:
        st.info("Noch keine Daten vorhanden.")

with t2:
    if not df.empty:
        disp = df.sort_values(['Datum', 'Uhrzeit'], ascending=[False, False]).copy()
        disp['Datum'] = disp['Datum'].dt.strftime('%d.%m.%Y')
        # Tabelle schöner sortiert
        cols = ['Datum', 'Uhrzeit', 'Schritte', 'Gewicht', 'Bemerkung', 'Kalorien_In', 'Kalorien_Out']
        st.dataframe(disp[cols + [c for c in disp.columns if c not in cols]], use_container_width=True, hide_index=True)
