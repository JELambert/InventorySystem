"""
Advanced visualization components for the Home Inventory System.

This module provides enhanced charts, graphs, and interactive visualizations
for better data representation and user insights.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from utils.helpers import get_location_type_display, safe_strip


def _parse_datetime_safe(dt_string):
    """Parse datetime string and make timezone naive (module-level helper)."""
    if not dt_string:
        return pd.NaT
    try:
        dt = pd.to_datetime(dt_string)
        if dt.tz is not None:
            dt = dt.tz_convert('UTC').tz_localize(None)
        return dt
    except Exception:
        return pd.NaT


class LocationVisualizationBuilder:
    """Builder class for creating location-related visualizations."""
    
    def __init__(self, locations: List[Dict[str, Any]]):
        """Initialize with location data."""
        self.locations = locations
        self.df = self._create_dataframe()
    
    def _create_dataframe(self) -> pd.DataFrame:
        """Create pandas DataFrame from location data."""
        if not self.locations:
            return pd.DataFrame()
        
        data = []
        for loc in self.locations:
            data.append({
                'id': loc.get('id'),
                'name': loc.get('name'),
                'type': loc.get('location_type', '').lower(),
                'type_display': get_location_type_display(loc.get('location_type', '')),
                'parent_id': loc.get('parent_id'),
                'depth': loc.get('depth', 0),
                'full_path': loc.get('full_path', ''),
                'created_at': self._parse_datetime(loc.get('created_at')),
                'description_length': len(loc.get('description', '') or ''),
                'has_description': bool(safe_strip(loc.get('description', ''))),
                'path_length': len(loc.get('full_path', '').split('/')),
                'is_root': loc.get('parent_id') is None
            })
        
        return pd.DataFrame(data)
    
    def _parse_datetime(self, dt_string):
        """Parse datetime string and make timezone naive."""
        if not dt_string:
            return pd.NaT
        try:
            dt = pd.to_datetime(dt_string)
            if dt.tz is not None:
                dt = dt.tz_convert('UTC').tz_localize(None)
            return dt
        except Exception:
            return pd.NaT
    
    def create_type_distribution_pie(self, **kwargs) -> go.Figure:
        """Create enhanced pie chart for location type distribution."""
        if self.df.empty:
            return self._create_empty_chart("No location data available")
        
        # Count by type
        type_counts = self.df['type_display'].value_counts()
        
        # Enhanced color scheme
        colors = {
            '🏠 House': '#2E86AB',
            '🚪 Room': '#A23B72', 
            '📦 Container': '#F18F01',
            '📚 Shelf': '#C73E1D'
        }
        
        chart_colors = [colors.get(t, '#7FCDCD') for t in type_counts.index]
        
        fig = go.Figure(data=[go.Pie(
            labels=type_counts.index,
            values=type_counts.values,
            hole=0.4,
            marker_colors=chart_colors,
            textinfo='label+percent+value',
            texttemplate='%{label}<br>%{value} (%{percent})',
            hovertemplate='<b>%{label}</b><br>' +
                         'Count: %{value}<br>' +
                         'Percentage: %{percent}<br>' +
                         '<extra></extra>',
            pull=[0.05 if i == 0 else 0 for i in range(len(type_counts))]  # Highlight largest
        )])
        
        fig.update_layout(
            title={
                'text': f"Location Distribution ({len(self.locations)} total)",
                'x': 0.5,
                'font': {'size': 18}
            },
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05
            ),
            margin=dict(t=60, b=20, l=20, r=120),
            **kwargs
        )
        
        return fig
    
    def create_hierarchy_depth_bar(self, **kwargs) -> go.Figure:
        """Create bar chart showing location hierarchy depth distribution."""
        if self.df.empty:
            return self._create_empty_chart("No location data available")
        
        # Count by depth
        depth_counts = self.df['depth'].value_counts().sort_index()
        
        # Create depth labels
        depth_labels = [f"Level {d}" if d > 0 else "Root" for d in depth_counts.index]
        
        fig = go.Figure(data=[go.Bar(
            x=depth_labels,
            y=depth_counts.values,
            marker_color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#7FCDCD'][:len(depth_counts)],
            text=depth_counts.values,
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>' +
                         'Count: %{y}<br>' +
                         '<extra></extra>'
        )])
        
        fig.update_layout(
            title={
                'text': "Location Hierarchy Depth Distribution",
                'x': 0.5,
                'font': {'size': 16}
            },
            xaxis_title="Hierarchy Level",
            yaxis_title="Number of Locations",
            showlegend=False,
            margin=dict(t=60, b=40, l=40, r=20),
            **kwargs
        )
        
        return fig
    
    def create_creation_timeline(self, **kwargs) -> go.Figure:
        """Create timeline chart showing location creation over time."""
        if self.df.empty:
            return self._create_empty_chart("No location data available")
        
        # Group by date
        daily_counts = self.df.groupby(self.df['created_at'].dt.date).size()
        
        # Create cumulative count
        cumulative_counts = daily_counts.cumsum()
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Daily Location Creation', 'Cumulative Location Count'),
            row_heights=[0.4, 0.6],
            vertical_spacing=0.12
        )
        
        # Daily creation bar chart
        fig.add_trace(
            go.Bar(
                x=daily_counts.index,
                y=daily_counts.values,
                name="Daily Creation",
                marker_color='#2E86AB',
                hovertemplate='<b>%{x}</b><br>Created: %{y}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Cumulative line chart
        fig.add_trace(
            go.Scatter(
                x=cumulative_counts.index,
                y=cumulative_counts.values,
                mode='lines+markers',
                name="Cumulative Total",
                line=dict(color='#F18F01', width=3),
                marker=dict(size=6),
                hovertemplate='<b>%{x}</b><br>Total: %{y}<extra></extra>'
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            title={
                'text': "Location Creation Timeline",
                'x': 0.5,
                'font': {'size': 16}
            },
            showlegend=True,
            height=500,
            margin=dict(t=80, b=40, l=40, r=20),
            **kwargs
        )
        
        return fig
    
    def create_hierarchy_tree_chart(self, max_depth: int = 3, **kwargs) -> go.Figure:
        """Create hierarchical tree visualization using treemap."""
        if self.df.empty:
            return self._create_empty_chart("No location data available")
        
        # Filter by depth for better visualization
        filtered_df = self.df[self.df['depth'] <= max_depth].copy()
        
        if filtered_df.empty:
            return self._create_empty_chart("No data for selected depth levels")
        
        # Create hierarchical data for treemap
        treemap_data = []
        
        # Add root level
        root_locations = filtered_df[filtered_df['is_root']]
        for _, root in root_locations.iterrows():
            treemap_data.append({
                'ids': str(root['id']),
                'labels': root['name'],
                'parents': '',
                'values': 1,
                'type': root['type_display']
            })
            
            # Add children
            children = filtered_df[filtered_df['parent_id'] == root['id']]
            for _, child in children.iterrows():
                treemap_data.append({
                    'ids': str(child['id']),
                    'labels': child['name'],
                    'parents': str(child['parent_id']),
                    'values': 1,
                    'type': child['type_display']
                })
        
        if not treemap_data:
            return self._create_empty_chart("No hierarchical data available")
        
        treemap_df = pd.DataFrame(treemap_data)
        
        # Color mapping
        color_map = {
            '🏠 House': '#2E86AB',
            '🚪 Room': '#A23B72',
            '📦 Container': '#F18F01',
            '📚 Shelf': '#C73E1D'
        }
        
        colors = [color_map.get(t, '#7FCDCD') for t in treemap_df['type']]
        
        fig = go.Figure(go.Treemap(
            ids=treemap_df['ids'],
            labels=treemap_df['labels'],
            parents=treemap_df['parents'],
            values=treemap_df['values'],
            branchvalues="total",
            marker=dict(
                colors=colors,
                line=dict(width=2, color='white')
            ),
            hovertemplate='<b>%{label}</b><br>' +
                         'Type: %{customdata}<br>' +
                         '<extra></extra>',
            customdata=treemap_df['type'],
            maxdepth=max_depth + 1
        ))
        
        fig.update_layout(
            title={
                'text': f"Location Hierarchy Tree (Max Depth: {max_depth})",
                'x': 0.5,
                'font': {'size': 16}
            },
            margin=dict(t=60, b=20, l=20, r=20),
            height=500,
            **kwargs
        )
        
        return fig
    
    def create_location_metrics_dashboard(self, **kwargs) -> go.Figure:
        """Create comprehensive metrics dashboard."""
        if self.df.empty:
            return self._create_empty_chart("No location data available")
        
        # Calculate metrics
        total_locations = len(self.df)
        avg_depth = self.df['depth'].mean()
        max_depth = self.df['depth'].max()
        locations_with_desc = self.df['has_description'].sum()
        desc_percentage = (locations_with_desc / total_locations) * 100
        
        # Create subplot figure
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Type Distribution', 
                'Depth Distribution',
                'Description Coverage',
                'Path Complexity'
            ),
            specs=[[{"type": "pie"}, {"type": "bar"}],
                   [{"type": "indicator"}, {"type": "histogram"}]]
        )
        
        # Type distribution pie
        type_counts = self.df['type_display'].value_counts()
        fig.add_trace(
            go.Pie(
                labels=type_counts.index,
                values=type_counts.values,
                name="Types"
            ),
            row=1, col=1
        )
        
        # Depth distribution bar
        depth_counts = self.df['depth'].value_counts().sort_index()
        fig.add_trace(
            go.Bar(
                x=depth_counts.index,
                y=depth_counts.values,
                name="Depth"
            ),
            row=1, col=2
        )
        
        # Description coverage indicator
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=desc_percentage,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "With Descriptions (%)"},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "#2E86AB"},
                    'steps': [
                        {'range': [0, 50], 'color': "#ffcccc"},
                        {'range': [50, 80], 'color': "#ffffcc"},
                        {'range': [80, 100], 'color': "#ccffcc"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ),
            row=2, col=1
        )
        
        # Path complexity histogram
        fig.add_trace(
            go.Histogram(
                x=self.df['path_length'],
                name="Path Length",
                nbinsx=10
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            title={
                'text': "Location Analytics Dashboard",
                'x': 0.5,
                'font': {'size': 18}
            },
            height=600,
            showlegend=False,
            margin=dict(t=80, b=40, l=40, r=40),
            **kwargs
        )
        
        return fig
    
    def _create_empty_chart(self, message: str) -> go.Figure:
        """Create empty chart with message."""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False),
            margin=dict(t=40, b=40, l=40, r=40)
        )
        return fig


def create_location_statistics_cards(locations: List[Dict[str, Any]]) -> None:
    """Create statistical overview cards."""
    if not locations:
        st.info("No location data available for statistics")
        return
    
    df = pd.DataFrame([{
        'type': loc.get('location_type', ''),
        'depth': loc.get('depth', 0),
        'has_description': bool(loc.get('description', '').strip()),
        'created_at': _parse_datetime_safe(loc.get('created_at')),
        'is_root': loc.get('parent_id') is None
    } for loc in locations])
    
    # Calculate statistics
    total_count = len(locations)
    avg_depth = df['depth'].mean()
    max_depth = df['depth'].max()
    root_count = df['is_root'].sum()
    desc_percentage = (df['has_description'].sum() / total_count) * 100
    
    # Recent creation (last 7 days)
    recent_cutoff = pd.Timestamp.now().tz_localize(None) - timedelta(days=7)
    recent_count = (df['created_at'] > recent_cutoff).sum()
    
    # Display cards
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Total Locations",
            f"{total_count:,}",
            help="Total number of locations in the system"
        )
    
    with col2:
        st.metric(
            "Average Depth",
            f"{avg_depth:.1f}",
            help="Average hierarchy depth of all locations"
        )
    
    with col3:
        st.metric(
            "Max Depth",
            f"{max_depth}",
            help="Maximum hierarchy depth in the system"
        )
    
    with col4:
        st.metric(
            "Root Locations",
            f"{root_count}",
            help="Number of top-level locations"
        )
    
    with col5:
        st.metric(
            "With Descriptions",
            f"{desc_percentage:.1f}%",
            help="Percentage of locations with descriptions"
        )


def create_advanced_search_metrics(search_results: List[Dict[str, Any]], 
                                 total_locations: int) -> None:
    """Create metrics for search results."""
    if not search_results:
        st.info("No search results to analyze")
        return
    
    result_count = len(search_results)
    percentage = (result_count / total_locations) * 100 if total_locations > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Search Results",
            f"{result_count:,}",
            f"{percentage:.1f}% of total"
        )
    
    with col2:
        if search_results:
            avg_depth = sum(loc.get('depth', 0) for loc in search_results) / result_count
            st.metric(
                "Avg Depth",
                f"{avg_depth:.1f}",
                help="Average depth of search results"
            )
    
    with col3:
        if search_results:
            types = [loc.get('location_type', '') for loc in search_results]
            unique_types = len(set(types))
            st.metric(
                "Location Types",
                f"{unique_types}",
                help="Number of different location types in results"
            )