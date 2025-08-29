"""
Dashboard helper functions for the Insider Trading Intelligence System
Separate utilities to keep dashboard.py clean and modular
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

def calculate_advanced_metrics(df: pd.DataFrame) -> Dict:
    """Calculate advanced metrics for dashboard display"""
    metrics = {}
    
    if df.empty:
        return metrics
    
    # Basic metrics
    metrics['total_transactions'] = len(df)
    metrics['unique_companies'] = df['company_name'].nunique() if 'company_name' in df.columns else 0
    metrics['unique_insiders'] = df['insider_name'].nunique() if 'insider_name' in df.columns else 0
    
    # Value metrics
    if 'total_value' in df.columns:
        metrics['total_value'] = df['total_value'].sum()
        metrics['avg_transaction_value'] = df['total_value'].mean()
        metrics['median_transaction_value'] = df['total_value'].median()
        metrics['max_transaction_value'] = df['total_value'].max()
    
    # Conviction metrics
    if 'conviction_score' in df.columns:
        metrics['avg_conviction'] = df['conviction_score'].mean()
        metrics['high_conviction_count'] = len(df[df['conviction_score'] >= 8])
        metrics['low_conviction_count'] = len(df[df['conviction_score'] <= 3])
    
    # Signal metrics
    if 'signal' in df.columns:
        signal_counts = df['signal'].value_counts()
        for signal, count in signal_counts.items():
            metrics[f'{signal.lower().replace(" ", "_")}_count'] = count
    
    # Time-based metrics
    if 'transaction_date' in df.columns and df['transaction_date'].notna().any():
        metrics['date_range'] = {
            'start': df['transaction_date'].min(),
            'end': df['transaction_date'].max()
        }
        
        # Recent activity (last 30 days from max date)
        max_date = df['transaction_date'].max()
        recent_cutoff = max_date - timedelta(days=30)
        recent_df = df[df['transaction_date'] >= recent_cutoff]
        metrics['recent_transactions'] = len(recent_df)
    
    return metrics

def get_top_performers(df: pd.DataFrame, metric: str = 'total_value', n: int = 10) -> pd.DataFrame:
    """Get top performing companies/insiders by specified metric"""
    if df.empty or metric not in df.columns:
        return pd.DataFrame()
    
    if metric in ['total_value', 'conviction_score', 'shares']:
        # Group by company for these metrics
        grouped = df.groupby('company_name').agg({
            metric: 'sum' if metric != 'conviction_score' else 'mean',
            'transaction_date': 'count',  # Number of transactions
            'signal': lambda x: x.mode().iloc[0] if not x.empty else 'N/A'  # Most common signal
        }).round(2)
        
        grouped.columns = [metric, 'transaction_count', 'primary_signal']
        return grouped.sort_values(metric, ascending=False).head(n)
    
    return pd.DataFrame()

def filter_data_by_criteria(df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
    """Apply multiple filters to the dataframe"""
    filtered_df = df.copy()
    
    # Date range filter
    if 'date_range' in filters and len(filters['date_range']) == 2:
        start_date, end_date = filters['date_range']
        if 'transaction_date' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['transaction_date'].dt.date >= start_date) &
                (filtered_df['transaction_date'].dt.date <= end_date)
            ]
    
    # Signal filter
    if 'signals' in filters and filters['signals']:
        if 'signal' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['signal'].isin(filters['signals'])]
    
    # Companies filter
    if 'companies' in filters and filters['companies']:
        if 'company_name' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['company_name'].isin(filters['companies'])]
    
    # Conviction score range
    if 'conviction_range' in filters:
        min_conviction, max_conviction = filters['conviction_range']
        if 'conviction_score' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['conviction_score'] >= min_conviction) &
                (filtered_df['conviction_score'] <= max_conviction)
            ]
    
    # Transaction value range
    if 'value_range' in filters:
        min_value, max_value = filters['value_range']
        if 'total_value' in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df['total_value'] >= min_value) &
                (filtered_df['total_value'] <= max_value)
            ]
    
    return filtered_df

def generate_insights(df: pd.DataFrame) -> List[str]:
    """Generate automatic insights from the data"""
    insights = []
    
    if df.empty:
        return ["No data available for analysis."]
    
    # Signal distribution insights
    if 'signal' in df.columns:
        signal_counts = df['signal'].value_counts()
        total_signals = len(df)
        
        if 'Strong Buy' in signal_counts:
            strong_buy_pct = (signal_counts['Strong Buy'] / total_signals) * 100
            if strong_buy_pct > 20:
                insights.append(f"🚀 High bullish sentiment: {strong_buy_pct:.1f}% of transactions are Strong Buy signals.")
        
        if 'Sell' in signal_counts:
            sell_pct = (signal_counts['Sell'] / total_signals) * 100
            if sell_pct > 15:
                insights.append(f"⚠️ Caution: {sell_pct:.1f}% of transactions are Sell signals.")
    
    # Value insights
    if 'total_value' in df.columns:
        avg_value = df['total_value'].mean()
        if avg_value > 1000000:
            insights.append(f"💰 High-value activity: Average transaction value is ${avg_value:,.0f}.")
    
    # Conviction insights
    if 'conviction_score' in df.columns:
        avg_conviction = df['conviction_score'].mean()
        if avg_conviction >= 7:
            insights.append(f"🎯 High conviction trades: Average conviction score is {avg_conviction:.1f}/10.")
        elif avg_conviction <= 4:
            insights.append(f"📉 Low conviction environment: Average conviction score is {avg_conviction:.1f}/10.")
    
    # Company concentration
    if 'company_name' in df.columns:
        top_company_pct = (df['company_name'].value_counts().iloc[0] / len(df)) * 100
        if top_company_pct > 25:
            top_company = df['company_name'].value_counts().index[0]
            insights.append(f"🏢 Concentrated activity: {top_company} represents {top_company_pct:.1f}% of all transactions.")
    
    # Recent activity
    if 'transaction_date' in df.columns and df['transaction_date'].notna().any():
        max_date = df['transaction_date'].max()
        recent_cutoff = max_date - timedelta(days=7)
        recent_count = len(df[df['transaction_date'] >= recent_cutoff])
        if recent_count > len(df) * 0.3:  # More than 30% of activity in last week
            insights.append(f"📈 Recent surge: {recent_count} transactions ({recent_count/len(df)*100:.1f}%) occurred in the last 7 days.")
    
    if not insights:
        insights.append("📊 Data loaded successfully. Explore the charts and filters for detailed insights.")
    
    return insights

def export_filtered_data(df: pd.DataFrame, filename: str = None) -> str:
    """Export filtered data to CSV and return the filename"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"filtered_insider_data_{timestamp}.csv"
    
    export_path = f"data/exports/{filename}"
    
    # Create exports directory if it doesn't exist
    import os
    os.makedirs("data/exports", exist_ok=True)
    
    # Export the data
    df.to_csv(export_path, index=False)
    return export_path

def calculate_portfolio_impact(df: pd.DataFrame, portfolio_tickers: List[str]) -> Dict:
    """Calculate impact on a theoretical portfolio"""
    if 'ticker' not in df.columns or not portfolio_tickers:
        return {}
    
    portfolio_df = df[df['ticker'].isin(portfolio_tickers)]
    
    if portfolio_df.empty:
        return {'message': 'No insider activity found for portfolio tickers'}
    
    impact = {
        'total_signals': len(portfolio_df),
        'companies_with_activity': portfolio_df['ticker'].nunique(),
        'signal_breakdown': portfolio_df['signal'].value_counts().to_dict() if 'signal' in portfolio_df.columns else {},
        'avg_conviction': portfolio_df['conviction_score'].mean() if 'conviction_score' in portfolio_df.columns else 0,
        'total_value': portfolio_df['total_value'].sum() if 'total_value' in portfolio_df.columns else 0
    }
    
    return impact

def validate_data_quality(df: pd.DataFrame) -> Dict:
    """Check data quality and return summary"""
    quality_report = {
        'total_rows': len(df),
        'missing_data': {},
        'data_types': {},
        'warnings': []
    }
    
    if df.empty:
        quality_report['warnings'].append("Dataset is empty")
        return quality_report
    
    # Check for missing data
    for col in df.columns:
        missing_count = df[col].isnull().sum()
        missing_pct = (missing_count / len(df)) * 100
        quality_report['missing_data'][col] = {
            'count': missing_count,
            'percentage': round(missing_pct, 2)
        }
        
        if missing_pct > 50:
            quality_report['warnings'].append(f"Column '{col}' has {missing_pct:.1f}% missing data")
    
    # Check data types
    for col in df.columns:
        quality_report['data_types'][col] = str(df[col].dtype)
    
    # Check for potential data issues
    if 'total_value' in df.columns:
        if (df['total_value'] < 0).any():
            quality_report['warnings'].append("Negative transaction values detected")
    
    if 'conviction_score' in df.columns:
        out_of_range = ((df['conviction_score'] < 0) | (df['conviction_score'] > 10)).sum()
        if out_of_range > 0:
            quality_report['warnings'].append(f"{out_of_range} conviction scores are outside expected range (0-10)")
    
    return quality_report