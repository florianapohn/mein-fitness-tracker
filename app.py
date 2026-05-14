# ... (dein restlicher Code oben bleibt gleich)

# HAUPTBEREICH: Visualisierung
tab1, tab2 = st.tabs(["Kurven & Trends", "Datentabelle"])

with tab1:
    if not df.empty:
        df_sorted = df.sort_values('Datum')
        
        # Erstellt zwei Spalten für die oberen beiden Diagramme
        col1, col2 = st.columns(2)
        
        with col1:
            # Gewichtskurve (links)
            fig_weight = px.line(df_sorted, x='Datum', y='Gewicht', title="Gewichtsverlauf", markers=True)
            # Wir reduzieren die Höhe ein wenig, damit es kompakter wirkt
            fig_weight.update_layout(height=400)
            st.plotly_chart(fig_weight, use_container_width=True)
            
        with col2:
            # Kalorien Vergleich (rechts)
            fig_cal = px.bar(df_sorted, x='Datum', y=['Kalorien_In', 'Kalorien_Out'], 
                             title="Kalorien: Input vs. Output", barmode='group')
            fig_cal.update_layout(height=400)
            st.plotly_chart(fig_cal, use_container_width=True)
        
        # Horizontaler Trenner (optional für die Optik)
        st.divider()

        # Schritte (darunter, volle Breite)
        fig_steps = px.area(df_sorted, x='Datum', y='Schritte', title="Taegliche Schritte")
        fig_steps.update_layout(height=400)
        st.plotly_chart(fig_steps, use_container_width=True)
        
    else:
        st.info("Noch keine Daten vorhanden. Nutze die Seitenleiste!")

with tab2:
    st.subheader("Alle Eintraege")
    st.dataframe(df.sort_values('Datum', ascending=False), use_container_width=True)
