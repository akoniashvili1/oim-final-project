# File 1: insider_parser.py
"""
SEC Form 4 Parser - MVP Implementation
Handles real XML files and extracts insider trading data
"""

import os
import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path
import re
from typing import List, Dict, Optional
from datetime import datetime
import json

class InsiderTradingParser:
    """Robust parser for SEC Form 4 XML files"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_xml_dir = self.data_dir / "raw_xml"
        
    def process_all_files(self) -> pd.DataFrame:
        """Main method to process all XML files"""
        print("Insider Trading Intelligence System - MVP")
        print("=" * 50)
        
        # Check directory
        if not self.raw_xml_dir.exists():
            print(f"Directory {self.raw_xml_dir} not found!")
            return pd.DataFrame()
        
        xml_files = list(self.raw_xml_dir.glob("*.xml"))
        print(f"Found {len(xml_files)} XML files")
        
        all_transactions = []
        successful_files = 0
        
        for xml_file in xml_files:
            print(f"\nProcessing {xml_file.name}...")
            
            # Check file size first
            if xml_file.stat().st_size == 0:
                print("  SKIP: Empty file")
                continue
            
            transactions = self._parse_single_file(xml_file)
            if transactions:
                all_transactions.extend(transactions)
                successful_files += 1
                print(f"  SUCCESS: {len(transactions)} transactions found")
            else:
                print("  SKIP: No transactions found")
        
        print(f"\n" + "=" * 50)
        print(f"Processing Summary:")
        print(f"Files processed: {successful_files}/{len(xml_files)}")
        print(f"Total transactions: {len(all_transactions)}")
        
        if all_transactions:
            df = pd.DataFrame(all_transactions)
            df = self._add_analysis_columns(df)
            
            # Save results
            output_file = self.data_dir / "insider_analysis.csv"
            df.to_csv(output_file, index=False)
            print(f"Results saved to: {output_file}")
            
            return df
        else:
            print("No transactions found in any files!")
            return pd.DataFrame()
    
    def _parse_single_file(self, file_path: Path) -> List[Dict]:
        """Parse a single XML file using multiple strategies"""
        transactions = []
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if not content.strip():
                return transactions
            
            # Parse XML
            root = ET.fromstring(content)
            
            # Strategy 1: Direct element search
            transactions = self._extract_by_direct_search(root, file_path.name)
            
            # Strategy 2: If no transactions found, try pattern matching
            if not transactions:
                transactions = self._extract_by_pattern_matching(content, file_path.name)
            
            return transactions
            
        except Exception as e:
            print(f"  ERROR: {e}")
            return transactions
    
    def _extract_by_direct_search(self, root, filename: str) -> List[Dict]:
        """Extract data by searching through all elements"""
        transactions = []
        
        # Find company info
        company_info = self._find_company_info(root)
        
        # Find all transaction containers
        transaction_containers = []
        for elem in root.iter():
            tag_name = elem.tag.split('}')[-1].lower()
            if 'transaction' in tag_name and ('nonderivative' in tag_name or 'derivative' in tag_name):
                transaction_containers.append(elem)
        
        print(f"  Found {len(transaction_containers)} transaction containers")
        
        # Extract data from each container
        for container in transaction_containers:
            trans_data = self._extract_transaction_data(container)
            if trans_data and trans_data.get('shares', 0) > 0:
                trans_data.update(company_info)
                trans_data['source_file'] = filename
                transactions.append(trans_data)
        
        return transactions
    
    def _find_company_info(self, root) -> Dict[str, str]:
        """Find company and insider information"""
        info = {
            'company_name': 'Unknown',
            'ticker': 'UNK', 
            'insider_name': 'Unknown',
            'insider_cik': ''
        }
        
        # Search all elements
        for elem in root.iter():
            if elem.text:
                tag_name = elem.tag.split('}')[-1].lower()
                text = elem.text.strip()
                
                if 'issuername' in tag_name:
                    info['company_name'] = text
                elif 'issuertradingsymbol' in tag_name:
                    info['ticker'] = text
                elif 'rptownername' in tag_name:
                    info['insider_name'] = text
                elif 'rptownercik' in tag_name:
                    info['insider_cik'] = text
        
        return info
    
    def _extract_transaction_data(self, container) -> Optional[Dict]:
        """Extract transaction data from a container element"""
        data = {
            'transaction_date': '',
            'transaction_code': '',
            'shares': 0,
            'price_per_share': 0,
            'acquired_disposed': 'A'
        }
        
        # Build a map of all text values with their context
        value_map = {}
        
        def collect_values(element, path=""):
            tag_name = element.tag.split('}')[-1].lower()
            current_path = f"{path}/{tag_name}" if path else tag_name
            
            if element.text and element.text.strip():
                value_map[current_path] = element.text.strip()
            
            for child in element:
                collect_values(child, current_path)
        
        collect_values(container)
        
        # Extract values using path patterns
        for path, value in value_map.items():
            if 'date' in path and 'value' in path:
                data['transaction_date'] = value
            elif 'code' in path and len(value) == 1:
                data['transaction_code'] = value
            elif 'shares' in path and 'value' in path:
                data['shares'] = self._clean_number(value)
            elif 'price' in path and 'value' in path:
                data['price_per_share'] = self._clean_number(value)
            elif 'acquired' in path or 'disposed' in path:
                if value in ['A', 'D']:
                    data['acquired_disposed'] = value
        
        # Calculate total value
        data['total_value'] = data['shares'] * data['price_per_share']
        
        return data if data['shares'] > 0 else None
    
    def _extract_by_pattern_matching(self, content: str, filename: str) -> List[Dict]:
        """Fallback: extract using regex patterns"""
        transactions = []
        
        try:
            # Extract basic info using regex
            company_match = re.search(r'<issuerName[^>]*>([^<]+)', content)
            ticker_match = re.search(r'<issuerTradingSymbol[^>]*>([^<]+)', content)
            insider_match = re.search(r'<rptOwnerName[^>]*>([^<]+)', content)
            
            company_name = company_match.group(1) if company_match else 'Unknown'
            ticker = ticker_match.group(1) if ticker_match else 'UNK'
            insider_name = insider_match.group(1) if insider_match else 'Unknown'
            
            # Find transaction patterns
            date_pattern = r'<transactionDate[^>]*>.*?<value[^>]*>([^<]+)'
            code_pattern = r'<transactionCode[^>]*>([A-Z])'
            shares_pattern = r'<transactionShares[^>]*>.*?<value[^>]*>([0-9,.-]+)'
            price_pattern = r'<transactionPricePerShare[^>]*>.*?<value[^>]*>([0-9,.-]+)'
            
            dates = re.findall(date_pattern, content)
            codes = re.findall(code_pattern, content)
            shares = re.findall(shares_pattern, content)
            prices = re.findall(price_pattern, content)
            
            # Match them up
            min_length = min(len(dates), len(codes), len(shares), len(prices))
            
            for i in range(min_length):
                shares_num = self._clean_number(shares[i])
                price_num = self._clean_number(prices[i])
                
                if shares_num > 0:
                    transactions.append({
                        'company_name': company_name,
                        'ticker': ticker,
                        'insider_name': insider_name,
                        'insider_cik': '',
                        'transaction_date': dates[i],
                        'transaction_code': codes[i],
                        'shares': shares_num,
                        'price_per_share': price_num,
                        'total_value': shares_num * price_num,
                        'acquired_disposed': 'A',
                        'source_file': filename
                    })
            
            print(f"  Pattern matching found {len(transactions)} transactions")
            
        except Exception as e:
            print(f"  Pattern matching failed: {e}")
        
        return transactions
    
    def _clean_number(self, value: str) -> float:
        """Clean and convert string to number"""
        try:
            if not value:
                return 0.0
            # Remove everything except digits, dots, and minus
            cleaned = re.sub(r'[^\d.-]', '', str(value))
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0
    
    def _add_analysis_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add analysis and scoring columns"""
        # Transaction descriptions
        code_descriptions = {
            'P': 'Purchase',
            'S': 'Sale',
            'A': 'Grant/Award',
            'D': 'Disposition',
            'F': 'Tax Payment',
            'M': 'Exercise/Conversion',
            'C': 'Conversion'
        }
        
        df['transaction_description'] = df['transaction_code'].map(code_descriptions).fillna('Unknown')
        
        # Conviction scoring
        def calculate_conviction(row):
            score = 0.0
            
            # Transaction type
            if row['transaction_code'] == 'P':  # Purchase
                score += 3.0
            elif row['transaction_code'] == 'S':  # Sale
                score -= 1.0
            elif row['transaction_code'] == 'A':  # Award
                score += 0.5
            
            # Size factor
            if row['total_value'] > 1000000:
                score += 2.0
            elif row['total_value'] > 100000:
                score += 1.0
            elif row['total_value'] > 10000:
                score += 0.5
            
            # Acquired vs disposed
            if row['acquired_disposed'] == 'A':
                score += 1.0
            else:
                score -= 0.5
            
            return max(0, min(5, score))
        
        df['conviction_score'] = df.apply(calculate_conviction, axis=1)
        
        # Signal generation
        def generate_signal(score):
            if score >= 4.0:
                return 'Strong Buy'
            elif score >= 3.0:
                return 'Buy'
            elif score >= 2.0:
                return 'Weak Buy'
            elif score <= 1.0:
                return 'Sell'
            else:
                return 'Hold'
        
        df['signal'] = df['conviction_score'].apply(generate_signal)
        
        # Days since transaction
        def days_since(date_str):
            try:
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        return (datetime.now() - date_obj).days
                    except ValueError:
                        continue
                return 999
            except:
                return 999
        
        df['days_since_transaction'] = df['transaction_date'].apply(days_since)
        
        return df.sort_values('conviction_score', ascending=False)

def generate_summary_report(df: pd.DataFrame):
    """Generate comprehensive summary report"""
    if df.empty:
        print("No data to analyze!")
        return
    
    print("\n" + "=" * 60)
    print("INSIDER TRADING INTELLIGENCE REPORT")
    print("=" * 60)
    
    # Basic stats
    print(f"Total Transactions: {len(df)}")
    print(f"Unique Companies: {df['ticker'].nunique()}")
    print(f"Unique Insiders: {df['insider_name'].nunique()}")
    print(f"Total Dollar Volume: ${df['total_value'].sum():,.2f}")
    print(f"Average Conviction Score: {df['conviction_score'].mean():.2f}")
    
    # Signal distribution
    print(f"\nSignal Distribution:")
    signals = df['signal'].value_counts()
    for signal, count in signals.items():
        pct = (count / len(df)) * 100
        print(f"  {signal}: {count} ({pct:.1f}%)")
    
    # Top conviction trades
    print(f"\nTop 10 Highest Conviction Trades:")
    print("-" * 60)
    top_trades = df.nlargest(10, 'conviction_score')
    for _, trade in top_trades.iterrows():
        print(f"{trade['ticker']:4} | {trade['insider_name'][:15]:15} | "
              f"{trade['transaction_description']:8} | "
              f"${trade['total_value']:>10,.0f} | "
              f"Score: {trade['conviction_score']:.1f} | {trade['signal']}")
    
    # Company activity
    print(f"\nMost Active Companies:")
    print("-" * 40)
    company_activity = df.groupby('ticker').agg({
        'total_value': 'sum',
        'conviction_score': 'mean',
        'ticker': 'count'
    }).rename(columns={'ticker': 'transaction_count'})
    
    top_companies = company_activity.nlargest(10, 'total_value')
    for ticker, row in top_companies.iterrows():
        print(f"{ticker:4} | {row['transaction_count']:2} trades | "
              f"${row['total_value']:>12,.0f} | "
              f"Avg Score: {row['conviction_score']:.1f}")
    
    # Recent activity
    recent_trades = df[df['days_since_transaction'] <= 30]
    print(f"\nRecent Activity (Last 30 days): {len(recent_trades)} trades")
    
    if len(recent_trades) > 0:
        recent_signals = recent_trades['signal'].value_counts()
        for signal, count in recent_signals.items():
            print(f"  {signal}: {count}")

def main():
    """Main execution"""
    parser = InsiderTradingParser()
    df = parser.process_all_files()
    
    if not df.empty:
        generate_summary_report(df)
        
        print(f"\n" + "=" * 60)
        print("MVP COMPLETE - Your data is processed and analyzed!")
        print("=" * 60)
        print(f"CSV file created: data/insider_analysis.csv")
        print(f"Total records: {len(df)}")
        
        # Show sample of data
        print(f"\nSample of processed data:")
        display_cols = ['ticker', 'insider_name', 'transaction_date', 
                       'transaction_description', 'total_value', 'conviction_score', 'signal']
        print(df[display_cols].head().to_string(index=False))
        
    else:
        print("No transactions were successfully extracted from your XML files.")
        print("This could be due to:")
        print("- Files being empty or corrupted")
        print("- Different XML structure than expected")
        print("- Files not containing transaction data")

if __name__ == "__main__":
    main()