import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import os

# Page configuration
st.set_page_config(
    page_title="Insider Trading Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_data():
    """Load and cache the insider trading data"""
    csv_path = "data/insider_analysis.csv"
    if not os.path.exists(csv_path):
        st.error(f"Data file not found: {csv_path}")
        st.info("Please run your MVP parser first to generate the data file.")
        return None
    
    try:
        df = pd.read_csv(csv_path)
        # Convert date column to datetime
        if 'transaction_date' in df.columns:
            df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def display_key_metrics(df):
    """Display key performance indicators"""
    if df is None or df.empty:
        return
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_transactions = len(df)
        st.metric("Total Transactions", f"{total_transactions:,}")
    
    with col2:
        total_value = df['total_value'].sum() if 'total_value' in df.columns else 0
        st.metric("Total Transaction Value", f"${total_value:,.0f}")
    
    with col3:
        avg_conviction = df['conviction_score'].mean() if 'conviction_score' in df.columns else 0
        st.metric("Avg Conviction Score", f"{avg_conviction:.2f}")
    
    with col4:
        unique_companies = df['company_name'].nunique() if 'company_name' in df.columns else 0
        st.metric("Companies Tracked", unique_companies)
    
    with col5:
        strong_buy_count = len(df[df['signal'] == 'Strong Buy']) if 'signal' in df.columns else 0
        st.metric("Strong Buy Signals", strong_buy_count)

def create_signal_distribution_chart(df):
    """Create signal distribution pie chart"""
    if 'signal' in df.columns:
        signal_counts = df['signal'].value_counts()
        
        fig = px.pie(
            values=signal_counts.values,
            names=signal_counts.index,
            title="Trading Signal Distribution",
            color_discrete_map={
                'Strong Buy': '#00CC96',
                'Buy': '#19D3F3',
                'Weak Buy': '#FFA500',
                'Hold': '#FFFF00',
                'Sell': '#FF6692'
            }
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        return fig
    return None

def create_conviction_score_distribution(df):
    """Create conviction score histogram"""
    if 'conviction_score' in df.columns:
        fig = px.histogram(
            df,
            x='conviction_score',
            nbins=20,
            title="Conviction Score Distribution",
            color_discrete_sequence=['#636EFA']
        )
        fig.update_layout(
            xaxis_title="Conviction Score",
            yaxis_title="Number of Transactions"
        )
        return fig
    return None

def create_transaction_timeline(df):
    """Create transaction timeline chart"""
    if 'transaction_date' in df.columns and df['transaction_date'].notna().any():
        # Group by date and signal
        timeline_data = df.groupby(['transaction_date', 'signal']).size().reset_index(name='count')
        
        fig = px.bar(
            timeline_data,
            x='transaction_date',
            y='count',
            color='signal',
            title="Transaction Timeline by Signal Type",
            color_discrete_map={
                'Strong Buy': '#00CC96',
                'Buy': '#19D3F3',
                'Weak Buy': '#FFA500',
                'Hold': '#FFFF00',
                'Sell': '#FF6692'
            }
        )
        fig.update_layout(
            xaxis_title="Transaction Date",
            yaxis_title="Number of Transactions"
        )
        return fig
    return None

def create_top_companies_chart(df, metric='total_value'):
    """Create top companies chart by selected metric"""
    if metric in df.columns and 'company_name' in df.columns:
        company_data = df.groupby('company_name')[metric].sum().sort_values(ascending=False).head(10)
        
        fig = px.bar(
            x=company_data.values,
            y=company_data.index,
            orientation='h',
            title=f"Top 10 Companies by {metric.replace('_', ' ').title()}",
            color=company_data.values,
            color_continuous_scale='viridis'
        )
        fig.update_layout(
            xaxis_title=metric.replace('_', ' ').title(),
            yaxis_title="Company"
        )
        return fig
    return None

def create_insider_activity_heatmap(df):
    """Create heatmap of insider activity by transaction type and acquired/disposed"""
    if 'transaction_code' in df.columns and 'acquired_disposed' in df.columns:
        heatmap_data = df.groupby(['transaction_code', 'acquired_disposed']).size().reset_index(name='count')
        heatmap_pivot = heatmap_data.pivot(index='transaction_code', columns='acquired_disposed', values='count').fillna(0)
        
        fig = px.imshow(
            heatmap_pivot.values,
            labels=dict(x="Acquired/Disposed", y="Transaction Code", color="Count"),
            x=heatmap_pivot.columns,
            y=heatmap_pivot.index,
            title="Insider Activity Heatmap: Transaction Type vs Acquired/Disposed",
            color_continuous_scale='Blues'
        )
        return fig
    return None

def display_top_transactions_table(df, n=10):
    """Display top transactions table"""
    st.subheader(f"Top {n} Transactions by Value")
    
    if 'total_value' in df.columns:
        top_transactions = df.nlargest(n, 'total_value')[
            ['transaction_date', 'company_name', 'ticker', 'insider_name', 
             'transaction_code', 'shares', 'price_per_share', 'total_value', 
             'conviction_score', 'signal']
        ].copy()
        
        # Format the display
        if 'transaction_date' in top_transactions.columns:
            top_transactions['transaction_date'] = top_transactions['transaction_date'].dt.strftime('%Y-%m-%d')
        
        st.dataframe(
            top_transactions,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("Total value data not available")

def main():
    st.title("🔍 Insider Trading Intelligence Dashboard")
    st.markdown("---")
    
    # Load data
    df = load_data()
    
    if df is None:
        st.stop()

    # Simple ticker search
    if 'ticker' in df.columns:
        ticker_input = st.sidebar.text_input("Search by Ticker (Optional)")
    if ticker_input:
        df = df[df['ticker'].str.upper() == ticker_input.strip().upper()]
    
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Date range filter
    if 'transaction_date' in df.columns and df['transaction_date'].notna().any():
        min_date = df['transaction_date'].min().date()
        max_date = df['transaction_date'].max().date()
        
        date_range = st.sidebar.date_input(
            "Select Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        if len(date_range) == 2:
            df = df[
                (df['transaction_date'].dt.date >= date_range[0]) &
                (df['transaction_date'].dt.date <= date_range[1])
            ]
    
    # Signal filter
    if 'signal' in df.columns:
        available_signals = df['signal'].unique()
        selected_signals = st.sidebar.multiselect(
            "Select Trading Signals",
            options=available_signals,
            default=available_signals
        )
        df = df[df['signal'].isin(selected_signals)]
    
    # Company filter
    if 'company_name' in df.columns:
        companies = df['company_name'].unique()
        if len(companies) > 1:
            selected_companies = st.sidebar.multiselect(
                "Select Companies (Optional)",
                options=sorted(companies),
                default=[]
            )
            if selected_companies:
                df = df[df['company_name'].isin(selected_companies)]
    
    # Display metrics
    display_key_metrics(df)
    st.markdown("---")
    
    # Main dashboard layout
    col1, col2 = st.columns(2)
    
    with col1:
        # Signal distribution
        fig_signals = create_signal_distribution_chart(df)
        if fig_signals:
            st.plotly_chart(fig_signals, use_container_width=True)
        
        # Conviction score distribution
        fig_conviction = create_conviction_score_distribution(df)
        if fig_conviction:
            st.plotly_chart(fig_conviction, use_container_width=True)
    
    with col2:
        # Transaction timeline
        fig_timeline = create_transaction_timeline(df)
        if fig_timeline:
            st.plotly_chart(fig_timeline, use_container_width=True)
        
        # Top companies
        metric_choice = st.selectbox(
            "Select metric for top companies:",
            options=['total_value', 'conviction_score', 'shares'],
            format_func=lambda x: x.replace('_', ' ').title()
        )
        fig_companies = create_top_companies_chart(df, metric_choice)
        if fig_companies:
            st.plotly_chart(fig_companies, use_container_width=True)
    
    # Full-width charts
    st.markdown("---")
    
    # Insider activity heatmap
    fig_heatmap = create_insider_activity_heatmap(df)
    if fig_heatmap:
        st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # Top transactions table
    st.markdown("---")
    display_top_transactions_table(df)
    
    # Raw data section
    if st.checkbox("Show Raw Data"):
        st.subheader("Raw Transaction Data")
        st.dataframe(df, use_container_width=True)
    
    # Data summary in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("Data Summary")
    st.sidebar.info(f"""
    **Filtered Data:**
    - {len(df)} transactions
    - {df['company_name'].nunique() if 'company_name' in df.columns else 0} companies
    - {df['insider_name'].nunique() if 'insider_name' in df.columns else 0} insiders
    """)

if __name__ == "__main__":
    main()