import os
import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path
import logging
from typing import List, Dict, Optional

class SECForm4Processor:
    def __init__(self, data_dir: str = "data", output_dir: str = "data/processed"):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        
        # Create output directory if it doesn't exist
        self._ensure_output_directory()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(message)s')
        self.logger = logging.getLogger(__name__)
    
    def _ensure_output_directory(self):
        """Ensure the output directory exists and is actually a directory."""
        try:
            # Check if path exists and is a file (not directory)
            if self.output_dir.exists() and self.output_dir.is_file():
                self.logger.warning(f"Removing file at {self.output_dir} to create directory")
                self.output_dir.unlink()  # Remove the file
            
            # Create directory
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
        except Exception as e:
            # Fallback: use current directory for output
            self.logger.warning(f"Could not create output directory {self.output_dir}: {e}")
            self.logger.warning("Using current directory for output files")
            self.output_dir = Path(".")
        
    def find_xml_files(self) -> List[Path]:
        """Find all XML files in the data directory."""
        xml_files = list(self.data_dir.glob("*.xml"))
        self.logger.info(f"Found {len(xml_files)} XML files to process:")
        for file in xml_files:
            self.logger.info(f"  - {file.name}")
        return xml_files
    
    def parse_form4_xml(self, file_path: Path) -> List[Dict]:
        """Parse SEC Form 4 XML file and extract transaction data."""
        try:
            # Check if file is too small
            if file_path.stat().st_size == 0:
                self.logger.info(f"  SKIPPED: File too small (0 bytes)")
                return []
            
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Define namespaces (SEC forms often use namespaces)
            namespaces = {'': 'http://www.sec.gov/edgar/document/xml'}
            
            transactions = []
            
            # Extract issuer information
            issuer_info = self.extract_issuer_info(root, namespaces)
            
            # Extract reporting owner information
            owner_info = self.extract_owner_info(root, namespaces)
            
            # Extract non-derivative transactions
            non_derivative_transactions = root.findall('.//nonDerivativeTransaction', namespaces)
            for transaction in non_derivative_transactions:
                trans_data = self.extract_transaction_data(transaction, namespaces)
                if trans_data:
                    trans_data.update(issuer_info)
                    trans_data.update(owner_info)
                    trans_data['transaction_type'] = 'non_derivative'
                    transactions.append(trans_data)
            
            # Extract derivative transactions
            derivative_transactions = root.findall('.//derivativeTransaction', namespaces)
            for transaction in derivative_transactions:
                trans_data = self.extract_transaction_data(transaction, namespaces)
                if trans_data:
                    trans_data.update(issuer_info)
                    trans_data.update(owner_info)
                    trans_data['transaction_type'] = 'derivative'
                    transactions.append(trans_data)
            
            return transactions
            
        except ET.ParseError as e:
            self.logger.error(f"  ERROR: XML parsing failed - {e}")
            return []
        except Exception as e:
            self.logger.error(f"  ERROR: Unexpected error - {e}")
            return []
    
    def extract_issuer_info(self, root, namespaces) -> Dict:
        """Extract issuer information from XML."""
        issuer_info = {}
        
        issuer = root.find('.//issuer', namespaces)
        if issuer is not None:
            issuer_name = issuer.find('issuerName', namespaces)
            issuer_cik = issuer.find('issuerCik', namespaces)
            issuer_symbol = issuer.find('issuerTradingSymbol', namespaces)
            
            issuer_info['issuer_name'] = issuer_name.text if issuer_name is not None else ''
            issuer_info['issuer_cik'] = issuer_cik.text if issuer_cik is not None else ''
            issuer_info['issuer_symbol'] = issuer_symbol.text if issuer_symbol is not None else ''
        
        return issuer_info
    
    def extract_owner_info(self, root, namespaces) -> Dict:
        """Extract reporting owner information from XML."""
        owner_info = {}
        
        reporting_owner = root.find('.//reportingOwner', namespaces)
        if reporting_owner is not None:
            owner_name = reporting_owner.find('.//rptOwnerName', namespaces)
            owner_cik = reporting_owner.find('.//rptOwnerCik', namespaces)
            
            owner_info['owner_name'] = owner_name.text if owner_name is not None else ''
            owner_info['owner_cik'] = owner_cik.text if owner_cik is not None else ''
        
        return owner_info
    
    def extract_transaction_data(self, transaction, namespaces) -> Optional[Dict]:
        """Extract transaction data from a transaction element."""
        try:
            trans_data = {}
            
            # Security title
            security_title = transaction.find('.//securityTitle/value', namespaces)
            trans_data['security_title'] = security_title.text if security_title is not None else ''
            
            # Transaction date
            trans_date = transaction.find('.//transactionDate/value', namespaces)
            trans_data['transaction_date'] = trans_date.text if trans_date is not None else ''
            
            # Transaction code
            trans_code = transaction.find('.//transactionCode', namespaces)
            trans_data['transaction_code'] = trans_code.text if trans_code is not None else ''
            
            # Transaction shares
            trans_shares = transaction.find('.//transactionShares/value', namespaces)
            trans_data['transaction_shares'] = trans_shares.text if trans_shares is not None else '0'
            
            # Transaction price per share
            trans_price = transaction.find('.//transactionPricePerShare/value', namespaces)
            trans_data['price_per_share'] = trans_price.text if trans_price is not None else '0'
            
            # Acquired/Disposed code
            acquired_disposed = transaction.find('.//transactionAcquiredDisposedCode/value', namespaces)
            trans_data['acquired_disposed_code'] = acquired_disposed.text if acquired_disposed is not None else ''
            
            # Shares owned following transaction
            shares_owned = transaction.find('.//sharesOwnedFollowingTransaction/value', namespaces)
            trans_data['shares_owned_following'] = shares_owned.text if shares_owned is not None else '0'
            
            # Direct/Indirect ownership
            direct_indirect = transaction.find('.//directOrIndirectOwnership/value', namespaces)
            trans_data['direct_indirect_ownership'] = direct_indirect.text if direct_indirect is not None else ''
            
            return trans_data
            
        except Exception as e:
            self.logger.error(f"    ERROR extracting transaction data: {e}")
            return None
    
    def process_single_file(self, file_path: Path) -> List[Dict]:
        """Process a single XML file and return extracted transactions."""
        self.logger.info(f"Processing {file_path.name}...")
        transactions = self.parse_form4_xml(file_path)
        
        if transactions:
            self.logger.info(f"  SUCCESS: Extracted {len(transactions)} transactions")
        
        return transactions
    
    def process_all_files(self) -> pd.DataFrame:
        """Process all XML files and return consolidated DataFrame."""
        all_transactions = []
        xml_files = self.find_xml_files()
        
        for file_path in xml_files:
            transactions = self.process_single_file(file_path)
            all_transactions.extend(transactions)
        
        if not all_transactions:
            self.logger.warning("No transactions found in any files!")
            # Create empty DataFrame with expected columns
            columns = ['issuer_name', 'issuer_symbol', 'issuer_cik', 'owner_name', 'owner_cik',
                      'security_title', 'transaction_date', 'transaction_code', 'transaction_shares',
                      'price_per_share', 'acquired_disposed_code', 'shares_owned_following',
                      'direct_indirect_ownership', 'transaction_type']
            return pd.DataFrame(columns=columns)
        
        # Create DataFrame
        results_df = pd.DataFrame(all_transactions)
        
        # Save to CSV
        output_file = self.output_dir / "form4_transactions.csv"
        results_df.to_csv(output_file, index=False)
        
        self.logger.info(f"\nProcessing Complete!")
        self.logger.info(f"Total transactions extracted: {len(all_transactions)}")
        self.logger.info(f"Results saved to: {output_file}")
        
        return results_df
    
    def generate_summary_report(self, df: pd.DataFrame) -> None:
        """Generate a summary report of the processed data."""
        if df.empty:
            self.logger.info("No data to summarize.")
            return
        
        summary_file = self.output_dir / "summary_report.txt"
        
        with open(summary_file, 'w') as f:
            f.write("SEC Form 4 Processing Summary Report\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Total Transactions: {len(df)}\n")
            f.write(f"Unique Companies: {df['issuer_symbol'].nunique()}\n")
            f.write(f"Unique Reporting Owners: {df['owner_name'].nunique()}\n\n")
            
            if 'transaction_code' in df.columns:
                f.write("Transaction Codes:\n")
                trans_codes = df['transaction_code'].value_counts()
                for code, count in trans_codes.items():
                    f.write(f"  {code}: {count}\n")
                f.write("\n")
            
            if 'issuer_symbol' in df.columns:
                f.write("Companies with most transactions:\n")
                company_counts = df['issuer_symbol'].value_counts().head(10)
                for symbol, count in company_counts.items():
                    f.write(f"  {symbol}: {count}\n")
        
        self.logger.info(f"Summary report saved to: {summary_file}")

def main():
    """Main execution function."""
    print("SEC Form 4 Batch Processor - FIXED VERSION")
    print("=" * 50)
    
    # Initialize processor
    processor = SECForm4Processor()
    
    # Process all files
    results_df = processor.process_all_files()
    
    # Generate summary report
    processor.generate_summary_report(results_df)
    
    # Display basic info
    if not results_df.empty:
        print(f"\nFirst few records:")
        print(results_df.head())
        print(f"\nDataFrame shape: {results_df.shape}")
        print(f"Columns: {list(results_df.columns)}")
    else:
        print("\nNo valid data found to display.")

if __name__ == "__main__":
    main()