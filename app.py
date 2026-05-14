# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import os

# App Konfiguration
st.set_page_config(page_title="My Fitness Hub", layout="wide")
st.title("My All-in-One Fitness Tracker")

# Datei fŸr Daten
DATA_FILE = "fitness_data.csv"

# Daten laden oder neu erstellen
if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    df['Datum'] = pd.to_datetime(df['Datum'])
else:
    columns = ['Datum', 'Gewicht', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel']
    df = pd.DataFrame(columns=columns)

# SEITENLEISTE: Dateneingabe
st.sidebar.header("Neue Daten eintragen")
with st.sidebar.form("entry_form", clear_on_submit=True):
    d = st.date_input("Datum", date.today())
    gew = st.number_input("Gewicht (kg)", format="%.1f")
    step = st.number_input("Schritte", step=100)
    akt = st.number_input("Aktivzeit (Min)", step=5)
    k_in = st.number_input("Kalorien (Gegessen)", step=50)
    k_out = st.number_input("Kalorien (Verbrannt)", step=50)
    
    st.subheader("Koerpermasse (cm)")
    hals = st.number_input("Hals", format="%.1f")
    brust = st.number_input("Brust", format="%.1f")
    bauch = st.number_input("Bauch", format="%.1f")
    bein = st.number_input("Oberschenkel", format="%.1f")
    
    submit = st.form_submit_button("Speichern")

if submit:
    new_data = {
        'Datum': pd.to_datetime(d), 'Gewicht': gew, 'Schritte': step, 
        'Aktivzeit': akt, 'Kalorien_In': k_in, 'Kalorien_Out': k_out,
        'Hals': hals, 'Brust': brust, 'Bauch': bauch, 'Oberschenkel': bein
    }
    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    df.to_csv(DATA_FILE, index=False)
    st.sidebar.success("Daten gespeichert!")

# HAUPTBEREICH: Visualisierung
tab1, tab2 = st.tabs(["?? Kurven & Trends", "?? Datentabelle"])

with tab1:
    if not df.empty:
        # Gewichtskurve
        fig_weight = px.line(df.sort_values('Datum'), x='Datum', y='Gewicht', title="Gewichtsverlauf", markers=True)
        st.plotly_chart(fig_weight, use_container_width=True)
        
        # Kalorien Vergleich
        fig_cal = px.bar(df.sort_values('Datum'), x='Datum', y=['Kalorien_In', 'Kalorien_Out'], 
                         title="Kalorien: Input vs. Output", barmode='group')
        st.plotly_chart(fig_cal, use_container_width=True)
        
        # Schritte
        fig_steps = px.area(df.sort_values('Datum'), x='Datum', y='Schritte', title="TŠgliche Schritte")
        st.plotly_chart(fig_steps, use_container_width=True)
    else:
        st.info("Noch keine Daten vorhanden. Nutze die Seitenleiste!")

with tab2:
    st.subheader("Alle EintrŠge")
    st.dataframe(df.sort_values('Datum', ascending=False), use_container_width=True)
