# ... (vorheriger Code bleibt gleich) ...

    with tab2:
        st.header("📊 Deine Langzeit-Entwicklung")
        if not df.empty:
            now = pd.Timestamp.now()
            periods = {
                "Diese Woche": now - pd.Timedelta(days=7),
                "Dieser Monat": now - pd.Timedelta(days=30),
                "Dieses Quartal": now - pd.Timedelta(days=90),
                "Dieses Jahr": now - pd.Timedelta(days=365)
            }

            for title, start_date in periods.items():
                mask = df['Datum'] >= start_date
                p_df = df[mask].sort_values('Datum')
                
                if not p_df.empty:
                    st.subheader(title)
                    # Wir teilen das Layout jetzt auf: 3 Spalten für Basis, 1 Spalte für Details
                    col_base, col_details = st.columns([3, 1])
                    
                    with col_base:
                        c1, c2, c3 = st.columns(3)
                        # Schritte & KM
                        t_steps = int(p_df['Schritte'].sum())
                        t_km = t_steps / 1400
                        c1.metric("👣 Schritte", f"{t_steps:,}", f"{t_km:.1f} km")
                        
                        # Kalorien
                        c2.metric("🔥 Kalorien Out", f"{int(p_df['Kalorien_Out'].sum()):,} kcal")
                        
                        # Gewicht
                        w_diff = p_df.iloc[-1]['Gewicht'] - p_df.iloc[0]['Gewicht']
                        c3.metric("⚖️ Gewicht", f"{p_df.iloc[-1]['Gewicht']:.1f} kg", f"{w_diff:+.1f} kg", delta_color="inverse")
                    
                    with col_details:
                        # Hier listen wir jetzt die Maße einzeln untereinander auf
                        st.markdown("**📏 Maße (Diff):**")
                        m_list = {
                            "Hals": "Hals", 
                            "Brust": "Brust", 
                            "Bauch": "Bauch", 
                            "Beine": "Oberschenkel"
                        }
                        
                        for label, key in m_list.items():
                            diff = p_df.iloc[-1][key] - p_df.iloc[0][key]
                            # Farbe bestimmen: Abnahme = Grün (gut), Zunahme = Rot
                            color = "green" if diff <= 0 else "red"
                            st.markdown(f"{label}: <span style='color:{color}; font-weight:bold;'>{diff:+.1f} cm</span>", unsafe_allow_html=True)
                    
                    st.markdown("---")

# ... (Rest des Codes bleibt gleich) ...
