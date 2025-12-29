
    # Tabs para diferentes análises
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Análises Gerais",
        "📅 Timeline",
        "📋 Detalhamento",
        "⏱️ Lead Time"
    ])
    
    with tab1:
        st.subheader("Análise por Empreendimento")
        
        if 'Empreendimento' in df.columns:
            analise_empreendimento = df.groupby('Empreendimento').agg({
                'Valor_Total': ['sum', 'mean', 'count'],
                'Desconto': 'sum',
            }).reset_index()
            
            analise_empreendimento.columns = ['Empreendimento', 'Valor_Total', 'Valor_Medio', 'Qtd_Pedidos', 'Total_Desconto']
            analise_empreendimento['%_Desconto'] = (analise_empreendimento['Total_Desconto'] / analise_empreendimento['Valor_Total'] * 100).fillna(0)
            analise_empreendimento = analise_empreendimento.sort_values('Valor_Total', ascending=False)
            
            # Formatação
            analise_empreendimento_display = analise_empreendimento.copy()
            analise_empreendimento_display['Valor_Total'] = analise_empreendimento_display['Valor_Total'].apply(formatar_moeda)
            analise_empreendimento_display['Valor_Medio'] = analise_empreendimento_display['Valor_Medio'].apply(formatar_moeda)
            analise_empreendimento_display['Total_Desconto'] = analise_empreendimento_display['Total_Desconto'].apply(formatar_moeda)
            analise_empreendimento_display['%_Desconto'] = analise_empreendimento_display['%_Desconto'].apply(formatar_percentual)
            
            st.dataframe(
                analise_empreendimento_display,
                use_container_width=True,
                hide_index=True
            )
            
            # Gráfico
            analise_empreendimento_num = analise_empreendimento.head(10)
            
            fig = px.bar(
                analise_empreendimento_num,
                x='Empreendimento',
                y='Valor_Total',
                title='Top 10 Empreendimentos por Valor Total',
                labels={'Valor_Total': 'Valor Total (R$)', 'Empreendimento': 'Empreendimento'}
            )
            fig.update_yaxes(tickformat='$,.2f')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados de empreendimento não disponíveis.")

        st.markdown("---")

        st.subheader("Análise por Comprador")
        
        if 'Comprador' in df.columns:
            analise_comprador = df.groupby('Comprador').agg({
                'Valor_Total': ['sum', 'mean', 'count'],
                'Desconto': 'sum',
            }).reset_index()
            
            analise_comprador.columns = ['Comprador', 'Valor_Total', 'Valor_Medio', 'Qtd_Pedidos', 'Total_Desconto']
            analise_comprador['%_Desconto'] = (analise_comprador['Total_Desconto'] / analise_comprador['Valor_Total'] * 100).fillna(0)
            analise_comprador = analise_comprador.sort_values('Valor_Total', ascending=False)
            
            # Formatação
            analise_comprador_display = analise_comprador.copy()
            analise_comprador_display['Valor_Total'] = analise_comprador_display['Valor_Total'].apply(formatar_moeda)
            analise_comprador_display['Valor_Medio'] = analise_comprador_display['Valor_Medio'].apply(formatar_moeda)
            analise_comprador_display['Total_Desconto'] = analise_comprador_display['Total_Desconto'].apply(formatar_moeda)
            analise_comprador_display['%_Desconto'] = analise_comprador_display['%_Desconto'].apply(formatar_percentual)
            
            st.dataframe(
                analise_comprador_display,
                use_container_width=True,
                hide_index=True
            )
            
            # Gráfico
            analise_comprador_num = analise_comprador.head(10)
            
            fig = px.bar(
                analise_comprador_num,
                x='Comprador',
                y='Valor_Total',
                title='Top 10 Compradores por Valor Total',
                labels={'Valor_Total': 'Valor Total (R$)', 'Comprador': 'Comprador'}
            )
            fig.update_yaxes(tickformat='$,.2f')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados de comprador não disponíveis.")

