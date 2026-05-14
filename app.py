# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    
    st.subheader("Körpermaße (cm)")
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
tab1, tab2 = st.tabs(["Kurven & Trends 📈", "Datentabelle 📋"])

with tab1:
    if not df.empty:
        df_plot = df.sort_values('Datum').copy()

        # REIHE 1: Diagramme
        col1, col2 = st.columns(2)
        
        with col1:
            df_plot['Diff'] = df_plot['Gewicht'].diff().fillna(0)
            df_plot['Farbe'] = df_plot['Diff'].apply(lambda x: 'red' if x > 0 else ('green' if x < 0 else 'gray'))
            
            fig_weight = go.Figure()
            fig_weight.add_trace(go.Scatter(
                x=df_plot['Datum'], y=df_plot['Gewicht'],
                fill='tozeroy', mode='lines',
                line=dict(width=2, color='#0288D1', shape='spline'),
                fillcolor='rgba(2, 136, 209, 0.1)', name='Gewicht'
            ))
            fig_weight.add_trace(go.Scatter(
                x=df_plot['Datum'], y=df_plot['Gewicht'],
                mode='markers',
                marker=dict(color=df_plot['Farbe'], size=10, line=dict(width=1, color='white')),
                name='Tendenz'
            ))
            fig_weight.update_layout(title="Gewichtsverlauf", height=350, showlegend=False)
            fig_weight.update_yaxes(range=[df_plot['Gewicht'].min()-2, df_plot['Gewicht'].max()+2])
            st.plotly_chart(fig_weight, use_container_width=True)
        
        with col2:
            fig_cal = px.bar(df_plot, x='Datum', y=['Kalorien_In', 'Kalorien_Out'], 
                             title="Kalorien: Input vs. Output", barmode='group')
            fig_cal.update_layout(height=350)
            st.plotly_chart(fig_cal, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Körpermaße & Fortschritt")
        
        latest = df_plot.iloc[-1]
        if len(df_plot) > 1:
            previous = df_plot.iloc[-2]
            d_hals = float(latest['Hals'] - previous['Hals'])
            d_brust = float(latest['Brust'] - previous['Brust'])
            d_bauz = float(latest['Bauch'] - previous['Bauch'])
            d_bein = float(latest['Oberschenkel'] - previous['Oberschenkel'])
        else:
            d_hals = d_brust = d_bauz = d_bein = 0.0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Hals", f"{latest['Hals']} cm", delta=f"{d_hals:+.1f} cm", delta_color="inverse")
        m2.metric("Brust", f"{latest['Brust']} cm", delta=f"{d_brust:+.1f} cm", delta_color="inverse")
        m3.metric("Bauch", f"{latest['Bauch']} cm", delta=f"{d_bauz:+.1f} cm", delta_color="inverse")
        m4.metric("Oberschenkel", f"{latest['Oberschenkel']} cm", delta=f"{d_bein:+.1f} cm", delta_color="inverse")
        
        st.markdown("---")
        fig_steps = px.area(df_plot, x='Datum', y='Schritte', title="Tägliche Schritte")
        fig_steps.update_layout(height=300)
        st.plotly_chart(fig_steps, use_container_width=True)
        
    else:
        st.info("Noch keine Daten vorhanden.")

with tab2:
    st.subheader("Deine Historie 🗓️")
    if not df.empty:
        # Kopie für die Anzeige erstellen und Datum formatieren
        display_df = df.copy()
        display_df['Datum'] = display_df['Datum'].dt.strftime('%d.%m.%Y')
        
        # Spalten umbenennen für Emojis
        display_df = display_df.rename(columns={
            'Datum': '📅 Datum',
            'Gewicht': '⚖️ Gewicht (kg)',
            'Schritte': '👣 Schritte',
            'Aktivzeit': '⏱️ Min',
            'Kalorien_In': '🥗 In',
            'Kalorien_Out': '🔥 Out',
            'Hals': '🦒 Hals',
            'Brust': '🦍 Brust',
            'Bauch': '🍕 Bauch',
            'Oberschenkel': '🍗 Bein'
        })

        # Styling: Balken für Kalorien und Schritte direkt in der Tabelle
        styled_df = display_df.sort_values('📅 Datum', ascending=False).style\
            .bar(subset=['👣 Schritte'], color='#FFA000', vmin=0)\
            .bar(subset=['🥗 In'], color='#4CAF50', vmin=0)\
            .bar(subset=['🔥 Out'], color='#FF5722', vmin=0)\
            .format(precision=1)

        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # Kleiner Export-Button als Bonus
        st.download_button(
            label="Daten als CSV herunterladen 📥",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name='fitness_daten_backup.csv',
            mime='text/csv',
        )
    else:
        st.info("Noch keine Daten zum Anzeigen da.")
