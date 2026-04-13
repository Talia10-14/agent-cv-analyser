"""
Utility functions for CV Analyzer.
Contains helpers for scoring, visualization, and UI components.
"""

from typing import Dict, Any, Optional
import plotly.graph_objects as go


def score_class(score: int) -> str:
    """
    Determine CSS class for score display based on value.
    
    Args:
        score: Numerical score (0-100)
        
    Returns:
        str: CSS class name ("high", "mid", "low")
    """
    if score >= 75:
        return "high"
    if score >= 50:
        return "mid"
    return "low"


def score_label(score: int) -> str:
    """
    Determine color value for score display.
    
    Args:
        score: Numerical score (0-100)
        
    Returns:
        str: CSS variable reference for color
    """
    if score >= 75:
        return "var(--green)"
    if score >= 50:
        return "var(--warn)"
    return "var(--danger)"


def create_radar_chart(
    score_global: int,
    score_tech: int,
    score_exp: int
) -> go.Figure:
    """
    Create a professional radar chart for CV analysis scores.
    
    Args:
        score_global: Global competency score (0-100)
        score_tech: Technical skills score (0-100)
        score_exp: Experience score (0-100)
        
    Returns:
        go.Figure: Plotly radar chart figure with professional styling
    """
    # Validate and normalize scores
    score_global = max(0, min(100, score_global or 0))
    score_tech = max(0, min(100, score_tech or 0))
    score_exp = max(0, min(100, score_exp or 0))

    fig = go.Figure(data=go.Scatterpolar(
        r=[score_global, score_tech, score_exp, score_global],
        theta=['Global', 'Technical', 'Experience', 'Global'],
        fill='toself',
        fillcolor='rgba(57,255,20,0.10)',
        line=dict(color='#39FF14', width=2),
        marker=dict(color='#39FF14', size=6),
    ))
    
    fig.update_layout(
        polar=dict(
            bgcolor='rgba(0,0,0,0)',
            radialaxis=dict(
                visible=True, range=[0, 100],
                tickcolor='#2D4A2D', gridcolor='#1A2A1A',
                tickfont=dict(size=9, color='#4A6A4A', family='DM Mono'),
                ticksuffix='%'
            ),
            angularaxis=dict(
                tickfont=dict(size=11, color='#7A9A7A', family='Syne'),
                gridcolor='#1A2A1A', linecolor='#2D4A2D'
            ),
        ),
        showlegend=False,
        margin=dict(l=40, r=40, t=40, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=280,
        font=dict(family='Syne', color='#7A9A7A')
    )
    
    return fig
