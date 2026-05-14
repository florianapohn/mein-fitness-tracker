# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import os

# 1. App Konfiguration
st.set_page_config(page_title="My Fitness Hub", layout="wide")
st.title("My All-in-One Fitness Tracker")

# 2. Datei-Handling
DATA_FILE = "fitness_data.csv"

if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE)
    df['Datum'] = pd.to_datetime(df['Datum'])
else:
    columns = ['Datum', 'Gewicht', 'Schritte', 'Aktivzeit', 'Kalorien_In', 'Kalorien_Out', 'Hals', 'Brust', 'Bauch', 'Oberschenkel']
    df = pd.DataFrame(columns=columns)

# 3. SEITENLEISTE: Dateneingabe
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
    st.rerun()

# 4. HAUPTBEREICH: Visualisierung
tab1, tab2 = st.tabs(["Kurven & Trends", "Datentabelle"])

with tab1:
    if not df.empty:
        # Daten für die Graphen sortieren
        df_plot = df.sort_values('Datum')

        # REIHE 1: Zwei Diagramme nebeneinander
        col1, col2 = st.columns(2)
        with col1:
            fig_weight = px.line(df_plot, x='Datum', y='Gewicht', title="Gewichtsverlauf", markers=True)
            fig_weight.update_layout(height=350)
            st.plotly_chart(fig_weight, use_container_width=True)
        
        with col2:
            fig_cal = px.bar(df_plot, x='Datum', y=['Kalorien_In', 'Kalorien_Out'], 
                             title="Kalorien: Input vs. Output", barmode='group')
            fig_cal.update_layout(height=350)
            st.plotly_chart(fig_cal, use_container_width=True)
        
        # REIHE 2: Körpermaße (Fortschrittsanzeige)
        st.markdown("---")
        st.subheader("Körpermaße & Fortschritt")
        
        latest = df_plot.iloc[-1]
        if len(df_plot) > 1:
            previous = df_plot.iloc[-2]
            # Berechnung der Differenz
            d_hals = float(latest['Hals'] - previous['Hals'])
            d_brust = float(latest['Brust'] - previous['Brust'])
            d_bauch = float(latest['Bauch'] - previous['Bauch'])
            d_bein = float(latest['Oberschenkel'] - previous['Oberschenkel'])
        else:
            d_hals = d_brust = d_bauch = d_bein = 0.0

        # Vier Spalten für die Maße
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Hals", f"{latest['Hals']} cm", delta=f"{d_hals:+.1f} cm", delta_color="inverse")
        m2.metric("Brust", f"{latest['Brust']} cm", delta=f"{d_brust:+.1f} cm", delta_color="inverse")
        m3.metric("Bauch", f"{latest['Bauch']} cm", delta=f"{d_bauch:+.1f} cm", delta_color="inverse")
        m4.metric("Oberschenkel", f"{latest['Oberschenkel']} cm", delta=f"{d_bein:+.1f} cm", delta_color="inverse")
        
        # REIHE 3: Schritte über volle Breite
        st.markdown("---")
        fig_steps = px.area(df_plot, x='Datum', y='Schritte', title="Tägliche Schritte")
        fig_steps.update_layout(height=350)
        st.plotly_chart(fig_steps, use_container_width=True)
        
    else:
        st.info("Noch keine Daten vorhanden. Nutze die Seitenleiste links, um deine ersten Werte einzutragen!")

with tab2:
    st.subheader("Historische Daten")
    # Anzeige der Tabelle, neueste Einträge oben
    st.dataframe(df.sort_values('Datum', ascending=False), use_container_width=True)
