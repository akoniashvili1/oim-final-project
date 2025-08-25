"""
SEC Form 4 Batch Processor - FIXED Windows Compatible Version
============================================================
Standalone batch processor that works with your existing XML files.
Fixes the Windows directory creation error and processes all files in data/raw_xml/
"""

import os
import sys
import logging
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import xml.etree.ElementTree as ET

import pandas as pd


class SECForm4Parser:
    """Standalone SEC Form 4 XML parser - based on your working parser"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        
    def _setup_logging(self):
        """Set up logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        return logging.getLogger(__name__)
    
    def safe_find_text(self, element, xpath: str) -> str:
        """Safely find element text"""
        try:
            found = element.find(xpath)
            return found.text.strip() if found is not None and found.text else ""
        except Exception:
            return ""
    
    def safe_findall(self, element, xpath: str) -> List:
        """Safely find all elements"""
        try:
            return element.findall(xpath)
        except Exception:
            return []
    
    def extract_reporting_owner(self, root) -> Dict[str, str]:
        """Extract reporting owner information - using your working logic"""
        owner_info = {"name": "UNKNOWN", "cik": "", "address": ""}
        
        # Try different possible paths for reporting owner
        owner_paths = [
            ".//reportingOwner",
            ".//reportingOwnerId", 
            ".//*[local-name()='reportingOwner']",
            ".//*[local-name()='reportingOwnerId']"
        ]
        
        for path in owner_paths:
            owners = self.safe_findall(root, path)
            if owners:
                owner = owners[0]
                
                # Try to get name from various possible locations
                name_paths = [
                    ".//rptOwnerName",
                    ".//ownerName", 
                    ".//*[local-name()='rptOwnerName']",
                    ".//*[local-name()='ownerName']"
                ]
                
                for name_path in name_paths:
                    name = self.safe_find_text(owner, name_path)
                    if name:
                        owner_info["name"] = name
                        break
                
                # Try to get CIK
                cik_paths = [
                    ".//rptOwnerCik",
                    ".//ownerCik",
                    ".//*[local-name()='rptOwnerCik']"
                ]
                
                for cik_path in cik_paths:
                    cik = self.safe_find_text(owner, cik_path)
                    if cik:
                        owner_info["cik"] = cik
                        break
                break
        
        return owner_info
    
    def extract_issuer_info(self, root) -> Dict[str, str]:
        """Extract company information"""
        issuer_info = {"name": "UNKNOWN", "symbol": "UNKNOWN", "cik": ""}
        
        issuer_paths = [".//issuer", ".//*[local-name()='issuer']"]
        
        for path in issuer_paths:
            issuers = self.safe_findall(root, path)
            if issuers:
                issuer = issuers[0]
                
                name = self.safe_find_text(issuer, ".//issuerName") or self.safe_find_text(issuer, ".//*[local-name()='issuerName']")
                symbol = self.safe_find_text(issuer, ".//issuerTradingSymbol") or self.safe_find_text(issuer, ".//*[local-name()='issuerTradingSymbol']")
                cik = self.safe_find_text(issuer, ".//issuerCik") or self.safe_find_text(issuer, ".//*[local-name()='issuerCik']")
                
                if name: issuer_info["name"] = name
                if symbol: issuer_info["symbol"] = symbol
                if cik: issuer_info["cik"] = cik
                break
                
        return issuer_info
    
    def extract_transactions(self, root) -> List[Dict[str, str]]:
        """Extract all transaction data from the XML - using your working logic"""
        transactions = []
        
        # Look for non-derivative transactions
        transaction_paths = [
            ".//nonDerivativeTransaction",
            ".//*[local-name()='nonDerivativeTransaction']"
        ]
        
        for path in transaction_paths:
            txns = self.safe_findall(root, path)
            if txns:
                for txn in txns:
                    transactions.append(self.parse_transaction(txn))
                break
        
        # Also look for derivative transactions
        derivative_paths = [
            ".//derivativeTransaction", 
            ".//*[local-name()='derivativeTransaction']"
        ]
        
        for path in derivative_paths:
            txns = self.safe_findall(root, path)
            if txns:
                for txn in txns:
                    transactions.append(self.parse_transaction(txn, is_derivative=True))
                break
        
        return transactions
    
    def parse_transaction(self, txn_element, is_derivative: bool = False) -> Dict[str, str]:
        """Parse individual transaction element - using your working logic"""
        transaction = {
            "transaction_type": "derivative" if is_derivative else "non_derivative",
            "date": "",
            "code": "",
            "shares": "",
            "price": "",
            "ownership": "",
            "security_title": ""
        }
        
        # Transaction date
        date_paths = [
            ".//transactionDate/value",
            ".//transactionDate", 
            ".//*[local-name()='transactionDate']/*[local-name()='value']",
            ".//*[local-name()='transactionDate']"
        ]
        
        for path in date_paths:
            date = self.safe_find_text(txn_element, path)
            if date:
                transaction["date"] = date
                break
        
        # Transaction code
        code_paths = [
            ".//transactionCoding/transactionCode",
            ".//transactionCode",
            ".//*[local-name()='transactionCoding']/*[local-name()='transactionCode']"
        ]
        
        for path in code_paths:
            code = self.safe_find_text(txn_element, path)
            if code:
                transaction["code"] = code
                break
        
        # Transaction shares/amount
        shares_paths = [
            ".//transactionShares/value",
            ".//transactionAmounts/transactionShares/value",
            ".//*[local-name()='transactionShares']/*[local-name()='value']"
        ]
        
        for path in shares_paths:
            shares = self.safe_find_text(txn_element, path)
            if shares:
                transaction["shares"] = shares
                break
        
        # Transaction price
        price_paths = [
            ".//transactionAmounts/transactionPricePerShare/value",
            ".//transactionPricePerShare/value",
            ".//pricePerShare/value", 
            ".//*[local-name()='transactionPricePerShare']/*[local-name()='value']"
        ]
        
        for path in price_paths:
            price = self.safe_find_text(txn_element, path)
            if price:
                transaction["price"] = price
                break
        
        # Ownership type
        ownership_paths = [
            ".//directOrIndirectOwnership/value",
            ".//ownershipNature/directOrIndirectOwnership/value",
            ".//*[local-name()='directOrIndirectOwnership']/*[local-name()='value']"
        ]
        
        for path in ownership_paths:
            ownership = self.safe_find_text(txn_element, path)
            if ownership:
                transaction["ownership"] = ownership
                break
        
        # Security title
        title_paths = [
            "../securityTitle/value",
            "../../securityTitle/value",
            ".//*[local-name()='securityTitle']/*[local-name()='value']"
        ]
        
        for path in title_paths:
            title = self.safe_find_text(txn_element, path)
            if title:
                transaction["security_title"] = title
                break
        
        return transaction
    
    def parse_form4_from_file(self, file_path: str) -> List[Dict]:
        """Parse Form 4 from local XML file and return transactions"""
        try:
            # Read file with encoding handling
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    xml_content = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='latin-1') as f:
                    xml_content = f.read()
        
            # Parse XML
            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError as e:
                self.logger.error(f"Failed to parse XML {file_path}: {e}")
                return []
            
            # Extract data using your working parser logic
            owner_info = self.extract_reporting_owner(root)
            issuer_info = self.extract_issuer_info(root)
            transactions = self.extract_transactions(root)
            
            # Build result list
            results = []
            for txn in transactions:
                results.append({
                    "Insider": owner_info["name"],
                    "CIK": owner_info["cik"],
                    "Company": issuer_info["name"],
                    "Symbol": issuer_info["symbol"],
                    "Date": txn["date"],
                    "Code": txn["code"],
                    "Shares": txn["shares"],
                    "Price": txn["price"],
                    "Ownership": txn["ownership"],
                    "Security": txn["security_title"],
                    "Transaction_Type": self._categorize_transaction(txn["code"], txn["shares"])
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            return []
    
    def _categorize_transaction(self, code: str, shares: str) -> str:
        """Categorize transaction for trading signals"""
        if not code:
            return 'Unknown'
        
        code = code.upper().strip()
        
        if code == 'A':
            return 'BUY'
        elif code == 'D':
            return 'SELL'
        elif code == 'P':
            return 'BUY'
        elif code == 'S':
            return 'SELL'
        elif code in ['F', 'I', 'L', 'W']:
            return 'OTHER'
        else:
            return f'OTHER_{code}'


class BatchProcessor:
    """Batch processor for XML files - FIXED for Windows"""
    
    def __init__(self, input_dir: str = 'data/raw_xml', output_dir: str = 'data/processed'):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.parser = SECForm4Parser()
        
        # FIXED: Windows-safe directory creation
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
        except FileExistsError:
            pass  # Directory already exists, that's fine
        except Exception as e:
            print(f"Warning: Could not create output directory {self.output_dir}: {e}")
            
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'skipped_files': 0,
            'total_transactions': 0,
            'error_files': 0
        }
    
    def is_valid_xml_file(self, file_path: str) -> Tuple[bool, str]:
        """Check if file is valid for processing"""
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        file_size = os.path.getsize(file_path)
        if file_size < 100:
            return False, f"File too small ({file_size} bytes)"
        
        if not file_path.lower().endswith(('.xml', '.txt')):
            return False, "Not an XML file"
        
        return True, "Valid"
    
    def process_all_files(self) -> pd.DataFrame:
        """Process all XML files in the input directory"""
        print("SEC Form 4 Batch Processor - FIXED VERSION")
        print("=" * 50)
        
        if not os.path.exists(self.input_dir):
            print(f"ERROR: Input directory '{self.input_dir}' does not exist!")
            print("Please create the directory and put your XML files there.")
            return pd.DataFrame()
        
        # Find XML files
        xml_files = []
        for filename in os.listdir(self.input_dir):
            if filename.lower().endswith(('.xml', '.txt')):
                xml_files.append(filename)
        
        self.stats['total_files'] = len(xml_files)
        
        if not xml_files:
            print(f"No XML files found in '{self.input_dir}'")
            return pd.DataFrame()
        
        print(f"Found {len(xml_files)} XML files to process:")
        for f in xml_files:
            print(f"  - {f}")
        print()
        
        all_transactions = []
        processed_files = []
        skipped_files = []
        
        for filename in xml_files:
            file_path = os.path.join(self.input_dir, filename)
            print(f"Processing {filename}...")
            
            # Check if file is valid
            is_valid, reason = self.is_valid_xml_file(file_path)
            if not is_valid:
                print(f"  SKIPPED: {reason}")
                skipped_files.append((filename, reason))
                self.stats['skipped_files'] += 1
                continue
            
            # Process file
            try:
                transactions = self.parser.parse_form4_from_file(file_path)
                if transactions:
                    all_transactions.extend(transactions)
                    processed_files.append(filename)
                    self.stats['processed_files'] += 1
                    self.stats['total_transactions'] += len(transactions)
                    print(f"  SUCCESS: Extracted {len(transactions)} transactions")
                else:
                    skipped_files.append((filename, "No transactions found"))
                    self.stats['skipped_files'] += 1
                    print(f"  WARNING: No transactions found")
                    
            except Exception as e:
                print(f"  ERROR: {e}")
                skipped_files.append((filename, f"Processing error: {str(e)}"))
                self.stats['error_files'] += 1
        
        # Create results DataFrame
        results_df = pd.DataFrame()
        if all_transactions:
            results_df = pd.DataFrame(all_transactions)
            
            # Add trading signals
            results_df = self._add_trading_signals(results_df)
            
            # Save to CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.output_dir, f'insider_trades_{timestamp}.csv')
            results_df.to_csv(output_file, index=False)
            print(f"\nSaved {len(results_df)} transactions to: {output_file}")
            
            # Save high-conviction signals
            high_conviction = results_df[results_df['Conviction_Score'] >= 7]
            if not high_conviction.empty:
                signals_file = os.path.join(self.output_dir, f'high_conviction_signals_{timestamp}.csv')
                high_conviction.to_csv(signals_file, index=False)
                print(f"Saved {len(high_conviction)} high-conviction signals to: {signals_file}")
        
        # Print summary
        self._print_summary(processed_files, skipped_files)
        
        return results_df
    
    def _add_trading_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add trading signal analysis"""
        if df.empty:
            return df
        
        # Convert shares and price to numeric
        df['Shares_Numeric'] = pd.to_numeric(df['Shares'], errors='coerce').fillna(0)
        df['Price_Numeric'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0)
        df['Total_Value'] = df['Shares_Numeric'] * df['Price_Numeric']
        
        # Calculate conviction scores
        df['Conviction_Score'] = 0
        
        for idx, row in df.iterrows():
            score = 0
            
            # Large transaction value
            if row['Total_Value'] > 1000000:  # $1M+
                score += 3
            elif row['Total_Value'] > 100000:  # $100k+
                score += 2
            elif row['Total_Value'] > 10000:  # $10k+
                score += 1
            
            # Direct ownership
            if row['Ownership'] == 'D':
                score += 1
            
            # Transaction type
            if row['Transaction_Type'] == 'BUY':
                score += 3  # Insider buying is significant
            elif row['Transaction_Type'] == 'SELL':
                score += 1
            
            # Multiple transactions by same insider
            same_insider_count = len(df[df['Insider'] == row['Insider']])
            if same_insider_count > 1:
                score += 1
            
            df.at[idx, 'Conviction_Score'] = score
        
        # Add signal categories
        df['Signal_Strength'] = pd.cut(
            df['Conviction_Score'],
            bins=[-1, 2, 5, 8, 15],
            labels=['Low', 'Medium', 'High', 'Very_High']
        )
        
        return df
    
    def _print_summary(self, processed_files: List[str], skipped_files: List[Tuple[str, str]]):
        """Print processing summary"""
        print("\n" + "=" * 60)
        print("BATCH PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Total files found: {self.stats['total_files']}")
        print(f"Successfully processed: {self.stats['processed_files']}")
        print(f"Skipped files: {self.stats['skipped_files']}")
        print(f"Error files: {self.stats['error_files']}")
        print(f"Total transactions: {self.stats['total_transactions']}")
        
        if processed_files:
            print(f"\nPROCESSED FILES:")
            for filename in processed_files:
                print(f"  ✓ {filename}")
        
        if skipped_files:
            print(f"\nSKIPPED FILES:")
            for filename, reason in skipped_files:
                print(f"  ✗ {filename}: {reason}")
        
        print("\n" + "=" * 60)
        
        if self.stats['total_transactions'] > 0:
            print("SUCCESS: Ready for insider trading analysis!")
            print("Check the CSV files in the 'data/processed' directory")
        else:
            print("No transactions extracted - check your XML files")


def main():
    """Main function - Fixed for your setup"""
    processor = BatchProcessor()
    results_df = processor.process_all_files()
    
    # Show results
    if not results_df.empty:
        print(f"\nSAMPLE DATA (first 5 rows):")
        print(results_df[['Insider', 'Symbol', 'Date', 'Transaction_Type', 'Shares', 'Price']].head())
        
        # Show high-conviction signals
        high_signals = results_df[results_df['Conviction_Score'] >= 7]
        if not high_signals.empty:
            print(f"\nHIGH-CONVICTION SIGNALS ({len(high_signals)} found):")
            print(high_signals[['Insider', 'Symbol', 'Transaction_Type', 'Total_Value', 'Conviction_Score']].head())
    
    print("\nBatch processing complete!")


if __name__ == "__main__":
    main()