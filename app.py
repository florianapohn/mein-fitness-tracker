# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
import os

# App Konfiguration
st.set_page_config(page_title="My Fitness Hub", layout="wide")
st.title("My All-in-One Fitness Tracker")

# Datei für Daten
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
    st.rerun() # Seite neu laden, um Diagramme zu aktualisieren

# HAUPTBEREICH: Visualisierung
tab1, tab2 = st.tabs(["Kurven & Trends", "Datentabelle"])

with tab1:
    if not df.empty:
        # Daten sortieren für saubere Graphen
        df_plot = df.sort_values('Datum')

        # ERSTE REIHE: Zwei Spalten
        col1, col2 = st.columns(2)
        
        with col1:
            fig_weight = px.line(df_plot, x='Datum', y='Gewicht', title="Gewichtsverlauf", markers=True)
            fig_weight.update_layout(height=350)
            st.plotly_chart(fig_weight, use_container_width=True)
            
        with col2:
            fig_cal = px.bar(df_plot, x='Datum', y=['Kalorien_In', 'Kalorien_Out'], 
                             title="Kalorien: In vs. Out", barmode='group')
            fig_cal.update_layout(height=350)
            st.plotly_chart(fig_cal, use_container_width=True)
        
        # ZWEITE REIHE: Volle Breite
        st.markdown("---") # Trennlinie
        fig_steps = px.area(df_plot, x='Datum', y='Schritte', title="Taegliche Schritte")
        fig_steps.update_layout(height=350)
        st.plotly_chart(fig_steps, use_container_width=True)
        
    else:
        st.info("Noch keine Daten vorhanden. Nutze die Seitenleiste!")

with tab2:
    st.subheader("Alle Eintraege")
    st.dataframe(df.sort_values('Datum', ascending=False), use_container_width=True)
# DRITTE REIHE: Körpermaße (Silhouetten-Ersatz durch Metriken)
        st.markdown("---")
        st.subheader("Körpermaße & Fortschritt")
        
        if len(df) >= 1:
            # Hol dir den aktuellsten und den vorletzten Eintrag für den Vergleich
            latest = df_plot.iloc[-1]
            
            # Check, ob es einen vorherigen Eintrag gibt
            if len(df_plot) > 1:
                previous = df_plot.iloc[-2]
                delta_hals = float(latest['Hals'] - previous['Hals'])
                delta_brust = float(latest['Brust'] - previous['Brust'])
                delta_bauch = float(latest['Bauch'] - previous['Bauch'])
                delta_bein = float(latest['Oberschenkel'] - previous['Oberschenkel'])
            else:
                delta_hals = delta_brust = delta_bauch = delta_bein = 0

            # Layout: 4 Spalten für die Maße
            m1, m2, m3, m4 = st.columns(4)
            
            # Anzeige mit Pfeilen (Delta)
            # label_visibility="visible" sorgt für saubere Beschriftung
            m1.metric("Hals", f"{latest['Hals']} cm", delta=f"{delta_hals:+.1f} cm", delta_color="inverse")
            m2.metric("Brust", f"{latest['Brust']} cm", delta=f"{delta_brust:+.1f} cm", delta_color="inverse")
            m3.metric("Bauch", f"{latest['Bauch']} cm", delta=f"{delta_bauch:+.1f} cm", delta_color="inverse")
            m4.metric("Oberschenkel", f"{latest['Oberschenkel']} cm", delta=f"{delta_bein:+.1f} cm", delta_color="inverse")
            
            st.info("💡 Das Delta zeigt die Veränderung zum letzten Eintrag an.")
