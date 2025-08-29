"""
Earnings Call Transcript Sentiment Analysis Module
Scrapes earnings call transcripts and performs NLP sentiment analysis
"""
import os
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

# NLP Libraries
try:
    from textblob import TextBlob
    from nltk.sentiment import SentimentIntensityAnalyzer
    import nltk
    
    # Download required NLTK data
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    
    try:
        nltk.data.find('vader_lexicon')
    except LookupError:
        nltk.download('vader_lexicon')
        
except ImportError:
    print("Warning: Some NLP libraries not installed. Run: pip install textblob nltk")

@dataclass
class TranscriptData:
    """Data class for earnings call transcript"""
    ticker: str
    company_name: str
    quarter: str
    year: int
    date: str
    transcript_text: str
    url: str

@dataclass
class SentimentScore:
    """Data class for sentiment analysis results"""
    ticker: str
    date: str
    textblob_polarity: float  # -1 to 1
    textblob_subjectivity: float  # 0 to 1
    vader_compound: float  # -1 to 1
    vader_positive: float
    vader_negative: float
    vader_neutral: float
    financial_sentiment: str  # Bullish/Bearish/Neutral
    confidence: float
    key_phrases: List[str]

class EarningsTranscriptScraper:
    """Scrapes earnings call transcripts from various sources"""
    
    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_seeking_alpha(self, ticker: str, num_quarters: int = 4) -> List[TranscriptData]:
        """
        Scrape earnings call transcripts from Seeking Alpha
        Note: This is a simplified example - actual implementation may need adjustments
        based on website structure changes
        """
        transcripts = []
        base_url = f"https://seekingalpha.com/symbol/{ticker}/earnings/transcripts"
        
        try:
            response = self.session.get(base_url)
            if response.status_code != 200:
                print(f"Failed to access Seeking Alpha for {ticker}: {response.status_code}")
                return transcripts
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find transcript links (simplified selector - may need adjustment)
            transcript_links = soup.find_all('a', href=re.compile(r'/article/\d+-.*-earnings'))
            
            for i, link in enumerate(transcript_links[:num_quarters]):
                if i >= num_quarters:
                    break
                    
                transcript_url = "https://seekingalpha.com" + link['href']
                transcript_data = self._scrape_single_transcript(transcript_url, ticker)
                
                if transcript_data:
                    transcripts.append(transcript_data)
                    
                time.sleep(self.delay)  # Rate limiting
                
        except Exception as e:
            print(f"Error scraping Seeking Alpha for {ticker}: {e}")
            
        return transcripts
    
    def _scrape_single_transcript(self, url: str, ticker: str) -> Optional[TranscriptData]:
        """Scrape a single earnings call transcript"""
        try:
            response = self.session.get(url)
            if response.status_code != 200:
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title for quarter/year info
            title_elem = soup.find('h1')
            title = title_elem.get_text() if title_elem else ""
            
            # Extract transcript text (simplified selector)
            content_divs = soup.find_all('div', {'data-module': 'ArticleViewer'})
            if not content_divs:
                content_divs = soup.find_all('div', class_=re.compile(r'article-content'))
            
            transcript_text = ""
            for div in content_divs:
                transcript_text += div.get_text() + " "
            
            if not transcript_text.strip():
                return None
            
            # Parse quarter and year from title
            quarter_match = re.search(r'Q([1-4])\s+(\d{4})', title)
            quarter = f"Q{quarter_match.group(1)}" if quarter_match else "Unknown"
            year = int(quarter_match.group(2)) if quarter_match else datetime.now().year
            
            # Extract company name
            company_match = re.search(r'^([^(]+)', title)
            company_name = company_match.group(1).strip() if company_match else ticker
            
            return TranscriptData(
                ticker=ticker,
                company_name=company_name,
                quarter=quarter,
                year=year,
                date=datetime.now().strftime('%Y-%m-%d'),  # Simplified
                transcript_text=transcript_text.strip(),
                url=url
            )
            
        except Exception as e:
            print(f"Error scraping transcript from {url}: {e}")
            return None
    
    def scrape_mock_data(self, ticker: str) -> List[TranscriptData]:
        """
        Generate mock earnings call data for testing purposes
        Use this when web scraping isn't available
        """
        mock_transcripts = {
            'AAPL': [
                "We're thrilled to report record revenue this quarter. iPhone sales exceeded expectations with strong demand in international markets. Our services business continues to show remarkable growth. We're optimistic about the upcoming product launches and see strong momentum continuing into the next quarter.",
                "This quarter presented some challenges with supply chain constraints, but our team executed well. Mac sales were solid despite market headwinds. We remain cautious about the near-term economic environment but are confident in our long-term strategy and innovation pipeline.",
                "Outstanding quarter with double-digit growth across all product categories. Customer satisfaction remains at all-time highs. We're investing heavily in AI and machine learning capabilities. The market opportunity ahead of us is enormous, and we're well-positioned to capitalize on it."
            ],
            'GOOGL': [
                "Search revenue grew significantly this quarter, driven by mobile and video advertising. Our cloud business is gaining serious traction with enterprise customers. AI investments are paying off with improved ad targeting and user engagement. We're bullish on the digital transformation trend.",
                "YouTube advertising revenue was exceptional this quarter. Google Cloud is showing strong momentum with major enterprise wins. We're seeing good recovery in small business advertising spend. Our AI capabilities continue to differentiate us in the market.",
                "Solid performance across all segments. Search remains robust with healthy click-through rates. Cloud infrastructure revenue exceeded expectations. We're cautiously optimistic about advertising spend recovery and see strong growth opportunities ahead."
            ]
        }
        
        transcripts = []
        mock_data = mock_transcripts.get(ticker, [mock_transcripts['AAPL'][0]])  # Default to AAPL data
        
        for i, text in enumerate(mock_data):
            transcripts.append(TranscriptData(
                ticker=ticker,
                company_name=f"{ticker} Inc.",
                quarter=f"Q{(i % 4) + 1}",
                year=2024,
                date=f"2024-0{(i % 4) + 1}-15",
                transcript_text=text,
                url=f"https://mock-transcript-{ticker.lower()}-q{(i % 4) + 1}.com"
            ))
        
        return transcripts

class FinancialSentimentAnalyzer:
    """Advanced sentiment analysis for financial texts"""
    
    def __init__(self):
        try:
            self.sia = SentimentIntensityAnalyzer()
        except:
            print("VADER analyzer not available")
            self.sia = None
        
        # Financial keywords for domain-specific analysis
        self.positive_financial_keywords = {
            'revenue', 'growth', 'profit', 'strong', 'excellent', 'outstanding', 'record',
            'bullish', 'optimistic', 'exceed', 'beat', 'momentum', 'expansion', 'opportunity',
            'confident', 'robust', 'solid', 'improving', 'increase', 'rise', 'gain',
            'successful', 'positive', 'upside', 'breakthrough', 'innovation'
        }
        
        self.negative_financial_keywords = {
            'loss', 'decline', 'weak', 'poor', 'disappointing', 'bearish', 'pessimistic',
            'miss', 'below', 'concern', 'challenge', 'risk', 'uncertainty', 'volatility',
            'decrease', 'drop', 'fall', 'struggle', 'difficulty', 'headwind', 'pressure',
            'cautious', 'conservative', 'downside', 'slowdown', 'contraction'
        }
    
    def analyze_sentiment(self, transcript: TranscriptData) -> SentimentScore:
        """Perform comprehensive sentiment analysis on transcript"""
        
        text = transcript.transcript_text.lower()
        
        # TextBlob sentiment
        blob = TextBlob(transcript.transcript_text)
        textblob_polarity = blob.sentiment.polarity
        textblob_subjectivity = blob.sentiment.subjectivity
        
        # VADER sentiment
        if self.sia:
            vader_scores = self.sia.polarity_scores(transcript.transcript_text)
            vader_compound = vader_scores['compound']
            vader_positive = vader_scores['pos']
            vader_negative = vader_scores['neg']
            vader_neutral = vader_scores['neu']
        else:
            vader_compound = vader_positive = vader_negative = vader_neutral = 0.0
        
        # Financial-specific sentiment
        financial_sentiment, confidence = self._analyze_financial_sentiment(text)
        
        # Extract key phrases
        key_phrases = self._extract_key_phrases(transcript.transcript_text)
        
        return SentimentScore(
            ticker=transcript.ticker,
            date=transcript.date,
            textblob_polarity=textblob_polarity,
            textblob_subjectivity=textblob_subjectivity,
            vader_compound=vader_compound,
            vader_positive=vader_positive,
            vader_negative=vader_negative,
            vader_neutral=vader_neutral,
            financial_sentiment=financial_sentiment,
            confidence=confidence,
            key_phrases=key_phrases
        )
    
    def _analyze_financial_sentiment(self, text: str) -> Tuple[str, float]:
        """Analyze sentiment using financial domain keywords"""
        positive_count = sum(1 for word in self.positive_financial_keywords if word in text)
        negative_count = sum(1 for word in self.negative_financial_keywords if word in text)
        
        total_financial_words = positive_count + negative_count
        
        if total_financial_words == 0:
            return "Neutral", 0.5
        
        positive_ratio = positive_count / total_financial_words
        
        if positive_ratio > 0.6:
            return "Bullish", positive_ratio
        elif positive_ratio < 0.4:
            return "Bearish", 1 - positive_ratio
        else:
            return "Neutral", 0.5
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key financial phrases from text"""
        # Simple keyword extraction (can be enhanced with more sophisticated NLP)
        key_phrases = []
        
        # Look for patterns like "revenue grew X%", "profit increased", etc.
        growth_patterns = re.findall(r'(revenue|profit|sales|earnings)[^.]*?(grew|increased|rose|jumped|surged)[^.]*?(\d+%|\d+\.\d+%)', text, re.IGNORECASE)
        decline_patterns = re.findall(r'(revenue|profit|sales|earnings)[^.]*?(fell|declined|dropped|decreased)[^.]*?(\d+%|\d+\.\d+%)', text, re.IGNORECASE)
        
        for pattern in growth_patterns:
            key_phrases.append(f"{pattern[0]} {pattern[1]} {pattern[2]}")
        
        for pattern in decline_patterns:
            key_phrases.append(f"{pattern[0]} {pattern[1]} {pattern[2]}")
        
        # Look for outlook statements
        outlook_patterns = re.findall(r'(outlook|guidance|expect|anticipate|forecast)[^.]*?[.]', text, re.IGNORECASE)
        key_phrases.extend([phrase.strip() for phrase in outlook_patterns[:3]])  # Limit to 3
        
        return key_phrases[:10]  # Limit to 10 key phrases

class InsiderSentimentCorrelator:
    """Correlate sentiment analysis with insider trading data"""
    
    def __init__(self, insider_data_path: str = "data/insider_analysis.csv"):
        self.insider_data_path = insider_data_path
    
    def correlate_sentiment_with_trades(self, sentiment_scores: List[SentimentScore]) -> pd.DataFrame:
        """Correlate sentiment scores with insider trading activity"""
        
        # Load insider trading data
        try:
            insider_df = pd.read_csv(self.insider_data_path)
            insider_df['transaction_date'] = pd.to_datetime(insider_df['transaction_date'])
        except FileNotFoundError:
            print(f"Insider trading data not found at {self.insider_data_path}")
            return pd.DataFrame()
        
        # Convert sentiment scores to DataFrame
        sentiment_data = []
        for score in sentiment_scores:
            sentiment_data.append({
                'ticker': score.ticker,
                'sentiment_date': score.date,
                'textblob_polarity': score.textblob_polarity,
                'vader_compound': score.vader_compound,
                'financial_sentiment': score.financial_sentiment,
                'confidence': score.confidence,
                'key_phrases': ', '.join(score.key_phrases)
            })
        
        sentiment_df = pd.DataFrame(sentiment_data)
        sentiment_df['sentiment_date'] = pd.to_datetime(sentiment_df['sentiment_date'])
        
        # Merge with insider data based on ticker and date proximity
        correlations = []
        
        for _, sentiment_row in sentiment_df.iterrows():
            ticker = sentiment_row['ticker']
            sentiment_date = sentiment_row['sentiment_date']
            
            # Find insider trades within 30 days of earnings call
            ticker_trades = insider_df[insider_df['ticker'] == ticker].copy()
            
            if not ticker_trades.empty:
                # Calculate days between sentiment date and trade dates
                ticker_trades['days_from_earnings'] = (ticker_trades['transaction_date'] - sentiment_date).dt.days
                
                # Filter trades within reasonable timeframe (-30 to +30 days)
                relevant_trades = ticker_trades[
                    (ticker_trades['days_from_earnings'] >= -30) & 
                    (ticker_trades['days_from_earnings'] <= 30)
                ]
                
                for _, trade_row in relevant_trades.iterrows():
                    correlations.append({
                        'ticker': ticker,
                        'sentiment_date': sentiment_date,
                        'transaction_date': trade_row['transaction_date'],
                        'days_from_earnings': trade_row['days_from_earnings'],
                        'textblob_polarity': sentiment_row['textblob_polarity'],
                        'vader_compound': sentiment_row['vader_compound'],
                        'financial_sentiment': sentiment_row['financial_sentiment'],
                        'confidence': sentiment_row['confidence'],
                        'insider_name': trade_row.get('insider_name', 'Unknown'),
                        'transaction_code': trade_row.get('transaction_code', 'Unknown'),
                        'total_value': trade_row.get('total_value', 0),
                        'conviction_score': trade_row.get('conviction_score', 0),
                        'signal': trade_row.get('signal', 'Unknown'),
                        'key_phrases': sentiment_row['key_phrases']
                    })
        
        correlation_df = pd.DataFrame(correlations)
        
        if not correlation_df.empty:
            # Add correlation insights
            correlation_df['sentiment_trade_alignment'] = correlation_df.apply(
                self._assess_alignment, axis=1
            )
        
        return correlation_df
    
    def _assess_alignment(self, row) -> str:
        """Assess alignment between sentiment and insider trading activity"""
        sentiment_positive = (
            row['textblob_polarity'] > 0.1 or 
            row['vader_compound'] > 0.1 or 
            row['financial_sentiment'] == 'Bullish'
        )
        
        trade_positive = row['signal'] in ['Strong Buy', 'Buy', 'Weak Buy']
        
        if sentiment_positive and trade_positive:
            return "Aligned Positive"
        elif not sentiment_positive and not trade_positive:
            return "Aligned Negative"
        elif sentiment_positive and not trade_positive:
            return "Contrarian (Positive Sentiment, Negative Trade)"
        elif not sentiment_positive and trade_positive:
            return "Contrarian (Negative Sentiment, Positive Trade)"
        else:
            return "Neutral"

def main():
    """Main function to demonstrate the sentiment analysis pipeline"""
    
    # Initialize components
    scraper = EarningsTranscriptScraper()
    analyzer = FinancialSentimentAnalyzer()
    correlator = InsiderSentimentCorrelator()
    
    # Example tickers to analyze
    tickers = ['AAPL', 'GOOGL', 'MSFT']
    
    all_sentiment_scores = []
    
    print("Starting sentiment analysis pipeline...")
    
    for ticker in tickers:
        print(f"\nAnalyzing {ticker}...")
        
        # Scrape transcripts (using mock data for demo)
        transcripts = scraper.scrape_mock_data(ticker)
        
        # Analyze sentiment for each transcript
        for transcript in transcripts:
            sentiment_score = analyzer.analyze_sentiment(transcript)
            all_sentiment_scores.append(sentiment_score)
            
            print(f"  {ticker} {transcript.quarter}: {sentiment_score.financial_sentiment} "
                  f"(Confidence: {sentiment_score.confidence:.2f})")
    
    # Save sentiment scores
    sentiment_data = []
    for score in all_sentiment_scores:
        sentiment_data.append({
            'ticker': score.ticker,
            'date': score.date,
            'textblob_polarity': score.textblob_polarity,
            'textblob_subjectivity': score.textblob_subjectivity,
            'vader_compound': score.vader_compound,
            'financial_sentiment': score.financial_sentiment,
            'confidence': score.confidence,
            'key_phrases': ', '.join(score.key_phrases)
        })
    
    sentiment_df = pd.DataFrame(sentiment_data)
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Save sentiment analysis results
    sentiment_df.to_csv('data/sentiment_analysis.csv', index=False)
    print(f"\nSentiment analysis saved to data/sentiment_analysis.csv")
    
    # Correlate with insider trading data
    print("\nCorrelating with insider trading data...")
    correlation_df = correlator.correlate_sentiment_with_trades(all_sentiment_scores)
    
    if not correlation_df.empty:
        correlation_df.to_csv('data/sentiment_insider_correlation.csv', index=False)
        print(f"Correlation analysis saved to data/sentiment_insider_correlation.csv")
        
        # Display summary
        print("\nCorrelation Summary:")
        alignment_counts = correlation_df['sentiment_trade_alignment'].value_counts()
        for alignment, count in alignment_counts.items():
            print(f"  {alignment}: {count}")
    else:
        print("No correlations found (insider trading data may not be available)")

if __name__ == "__main__":
    main()