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
    # Neue Spalten 'Uhrzeit' und 'Bemerkung' hinzugefügt
    columns = ['Datum', 'Uhrzeit', 'Gewicht', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel', 'Bemerkung']
    df = pd.DataFrame(columns=columns)

# Sicherstellen, dass die neuen Spalten auch in alten Dateien existieren
for col in ['Uhrzeit', 'Bemerkung']:
    if col not in df.columns:
        df[col] = ""

# 3. SEITENLEISTE: Dateneingabe
st.sidebar.header("📥 Neue Daten eintragen")
with st.sidebar.form("entry_form", clear_on_submit=True):
    d = st.date_input("Datum auswählen", date.today())
    
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        gew = st.number_input("Gewicht (kg)", format="%.1f", min_value=0.0)
        step = st.number_input("Schritte", step=100, min_value=0)
    with col_input2:
        k_in = st.number_input("Kalorien (In)", step=50, min_value=0)
        k_out = st.number_input("Kalorien (Out)", step=50, min_value=0)
    
    akt = st.number_input("Aktivzeit (Min)", step=5, min_value=0)
    
    # NEU: Bemerkungsfeld
    note = st.text_input("Bemerkung (z.B. Urlaub, Krank, Feier)", placeholder="Was war heute besonders?")
    
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
    
    # Logik: Gibt es heute schon einen Eintrag?
    same_day = df[df['Datum'] == input_date]
    
    # Wenn ein Eintrag existiert UND dieser Tag bisher nur Nullen hatte (oder leer war), aktualisieren wir
    # Wir prüfen das am Gewicht (oft der Hauptwert)
    if not same_day.empty and (same_day['Gewicht'].sum() == 0):
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
        # Sonst: Neue Zeile anlegen (für 2. Messung am Tag)
        new_data = {
            'Datum': input_date, 'Uhrzeit': now_time, 'Gewicht': gew, 'Schritte': step, 
            'Aktivzeit': akt, 'Kalorien_In': k_in, 'Kalorien_Out': k_out,
            'Hals': hals, 'Brust': brust, 'Bauch': bauch, 'Oberschenkel': bein,
            'Bemerkung': note
        }
        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    
    df.to_csv(DATA_FILE, index=False)
    st.sidebar.success("Daten verarbeitet! ✅")
    st.rerun()

# (Der Rest des Codes für Benachrichtigungen und Trends bleibt gleich...)
# ... [Teil 4 & 5 gekürzt für die Übersicht, aber identisch zum vorherigen Stand] ...

# 5. HAUPTBEREICH: Visualisierung
tab1, tab2 = st.tabs(["Kurven & Trends 📈", "Datentabelle 📋"])

with tab1:
    if not df.empty:
        df_plot = df.sort_values(['Datum', 'Uhrzeit']).copy()
        # Visualisierungen wie bisher...
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("⚖️ Gewichtsverlauf")
            fig_weight = go.Figure()
            fig_weight.add_trace(go.Scatter(x=df_plot['Datum'], y=df_plot['Gewicht'], fill='tozeroy', mode='lines+markers', line=dict(width=2, color='#0288D1', shape='spline')))
            fig_weight.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_weight, use_container_width=True)
        with col2:
            st.subheader("🔥 Kalorien")
            fig_cal = px.bar(df_plot, x='Datum', y=['Kalorien_In', 'Kalorien_Out'], barmode='group')
            st.plotly_chart(fig_cal, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📏 Maße & Schritte")
        # Metriken...
        latest = df_plot.iloc[-1]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Hals", f"{latest['Hals']} cm")
        m2.metric("Brust", f"{latest['Brust']} cm")
        m3.metric("Bauch", f"{latest['Bauch']} cm")
        m4.metric("Beine", f"{latest['Oberschenkel']} cm")

with tab2:
    st.subheader("🗓️ Deine Historie")
    if not df.empty:
        display_df = df.copy()
        display_df = display_df.sort_values(['Datum', 'Uhrzeit'], ascending=[False, False])
        display_df['Datum'] = display_df['Datum'].dt.strftime('%d.%m.%Y')
        
        # Spalten-Mapping mit Emojis inkl. der neuen Felder
        display_df = display_df.rename(columns={
            'Datum': '📅 Datum', 'Uhrzeit': '🕒 Zeit', 'Gewicht': '⚖️ kg', 
            'Schritte': '👣 Schritte', 'Bemerkung': '📝 Info'
        })
        
        # Nur relevante Spalten anzeigen für die Übersicht
        cols_to_show = ['📅 Datum', '🕒 Zeit', '⚖️ kg', '👣 Schritte', '📝 Info', 'Kalorien_In', 'Kalorien_Out']
        st.dataframe(display_df[cols_to_show + [c for c in display_df.columns if c not in cols_to_show]], use_container_width=True, hide_index=True)
