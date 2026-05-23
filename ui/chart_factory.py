import plotly.graph_objects as go

def render_predictive_forecast_chart(forecast_df):
    """
    Renders a dark-themed Plotly chart showing predictive order volume 
    and a shaded confidence interval area.
    """
    # AI Cyan color palette as requested
    primary_color = "#00E5FF"
    fill_color = "rgba(0, 229, 255, 0.2)"
    
    fig = go.Figure()

    # Add Upper Bound (invisible line to define the top of the fill)
    fig.add_trace(go.Scatter(
        x=forecast_df['Hour'],
        y=forecast_df['Upper_Bound'],
        mode='lines',
        line=dict(width=0),
        showlegend=False,
        name='Upper Bound'
    ))

    # Add Lower Bound (with fill 'tonexty' which fills area up to Upper Bound)
    fig.add_trace(go.Scatter(
        x=forecast_df['Hour'],
        y=forecast_df['Lower_Bound'],
        mode='lines',
        line=dict(width=0),
        fill='tonexty',
        fillcolor=fill_color,
        showlegend=False,
        name='Lower Bound'
    ))

    # Add Primary Prediction Line
    fig.add_trace(go.Scatter(
        x=forecast_df['Hour'],
        y=forecast_df['Predicted_Orders'],
        mode='lines+markers',
        line=dict(color=primary_color, width=3),
        marker=dict(size=6, color=primary_color),
        name='Predicted Demand',
        hovertemplate="<b>Time: %{x}</b><br>Predicted Volume: %{y:.1f}<extra></extra>"
    ))

    # CartoDB Dark Matter / Enterprise aesthetic styling
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hoverlabel=dict(bgcolor="#262730", font_size=14, font_family="Segoe UI"),
        font=dict(color='#E0E0E0'),
        xaxis=dict(
            title="Time of Day",
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)',
            tickangle=-45
        ),
        yaxis=dict(
            title="Predicted Order Volume",
            showgrid=True,
            gridcolor='rgba(255,255,255,0.1)'
        ),
        margin=dict(l=40, r=40, t=40, b=40),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig
