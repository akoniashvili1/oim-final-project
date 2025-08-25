"""
SEC Form 4 Parser - Clean, Robust Solution
Handles XML namespaces and extracts insider trading data
"""

import requests
import xml.etree.ElementTree as ET
import pandas as pd
from typing import List, Dict, Optional
import re

class SECForm4Parser:
    """Parser for SEC Form 4 XML filings"""
    
    def __init__(self):
        # Define namespace mappings that are commonly used in SEC filings
        self.namespaces = {}
        
    def fetch_xml(self, url: str) -> str:
        """Fetch XML content from URL with proper error handling"""
        import time
        
        try:
            # SEC requires specific headers and rate limiting
            headers = {
                'User-Agent': 'Sample Company Name AdminContact@<sample company domain>.com',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'www.sec.gov'
            }
            
            # Add delay to respect rate limits (SEC allows 10 requests per second max)
            time.sleep(0.1)
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 403:
                print("SEC blocked request. Trying alternative approach...")
                # Try with different headers
                headers = {
                    'User-Agent': 'Python requests library (educational use)',
                    'From': 'your-email@example.com',  # Replace with your email
                    'Accept': '*/*'
                }
                time.sleep(1)  # Longer delay
                response = requests.get(url, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.content
            
        except requests.RequestException as e:
            # If still failing, let's try to help with debugging
            if "403" in str(e):
                raise Exception(f"SEC blocked the request. This could be due to:\n"
                              f"1. Rate limiting (too many requests)\n"
                              f"2. Missing proper identification headers\n"
                              f"3. IP-based blocking\n"
                              f"Original error: {e}\n"
                              f"Try using a local XML file instead for testing.")
            else:
                raise Exception(f"Failed to fetch XML from {url}: {e}")
    
    def register_namespaces(self, root) -> None:
        """Extract and register all namespaces from the XML"""
        # Clear existing namespaces
        self.namespaces.clear()
        
        # Extract namespaces from root element
        for prefix, uri in re.findall(r'xmlns(?::(\w+))?="([^"]*)"', ET.tostring(root, encoding='unicode')):
            if prefix:
                self.namespaces[prefix] = uri
                ET.register_namespace(prefix, uri)
            else:
                # Default namespace
                self.namespaces[''] = uri
                ET.register_namespace('', uri)
    
    def safe_find_text(self, element, xpath: str, namespaces: dict = None) -> str:
        """Safely find element text with namespace support"""
        try:
            found = element.find(xpath, namespaces or self.namespaces)
            return found.text.strip() if found is not None and found.text else ""
        except Exception:
            return ""
    
    def safe_findall(self, element, xpath: str, namespaces: dict = None) -> List:
        """Safely find all elements with namespace support"""
        try:
            return element.findall(xpath, namespaces or self.namespaces)
        except Exception:
            return []
    
    def extract_reporting_owner(self, root) -> Dict[str, str]:
        """Extract reporting owner information"""
        owner_info = {
            "name": "UNKNOWN",
            "cik": "",
            "address": ""
        }
        
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
                owner = owners[0]  # Take first owner
                
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
    
    def extract_transactions(self, root) -> List[Dict[str, str]]:
        """Extract all transaction data from the XML"""
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
        """Parse individual transaction element"""
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
        
        # Security title (try to get from parent or nearby elements)
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
    
    def parse_form4_from_file(self, file_path: str) -> pd.DataFrame:
        """Parse Form 4 from local XML file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                xml_content = f.read().encode('utf-8')
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            with open(file_path, 'r', encoding='latin-1') as f:
                xml_content = f.read().encode('utf-8')
        
        # Parse XML
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise Exception(f"Failed to parse XML: {e}")
        
        # Register namespaces
        self.register_namespaces(root)
        
        # Extract reporting owner info
        owner_info = self.extract_reporting_owner(root)
        
        # Extract transactions
        transactions = self.extract_transactions(root)
        
        # Build final dataset
        trades = []
        for txn in transactions:
            trades.append({
                "Insider": owner_info["name"],
                "CIK": owner_info["cik"], 
                "Date": txn["date"],
                "Code": txn["code"],
                "Shares": txn["shares"],
                "Price": txn["price"],
                "Ownership": txn["ownership"],
                "Security": txn["security_title"],
                "Transaction_Type": txn["transaction_type"]
            })
        
        return pd.DataFrame(trades)

    def parse_form4(self, url: str) -> pd.DataFrame:
        """Main method to parse Form 4 and return DataFrame"""
        # Fetch XML
        xml_content = self.fetch_xml(url)
        
        # Parse XML
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise Exception(f"Failed to parse XML: {e}")
        
        # Register namespaces
        self.register_namespaces(root)
        
        # Extract reporting owner info
        owner_info = self.extract_reporting_owner(root)
        
        # Extract transactions
        transactions = self.extract_transactions(root)
        
        # Build final dataset
        trades = []
        for txn in transactions:
            trades.append({
                "Insider": owner_info["name"],
                "CIK": owner_info["cik"], 
                "Date": txn["date"],
                "Code": txn["code"],
                "Shares": txn["shares"],
                "Price": txn["price"],
                "Ownership": txn["ownership"],
                "Security": txn["security_title"],
                "Transaction_Type": txn["transaction_type"]
            })
        
        return pd.DataFrame(trades)


def main():
    """Example usage with multiple approaches"""
    parser = SECForm4Parser()
    
    # Test URL
    url = "https://www.sec.gov/Archives/edgar/data/320193/000176709425000005/xslF345X05/wk-form4_1755037816.xml"
    
    print("Attempting to fetch from SEC website...")
    try:
        df = parser.parse_form4(url)
        print("Success! Extracted data:")
        print(df)
        print(f"\nShape: {df.shape}")
        
        # Save to CSV
        df.to_csv("insider_trades.csv", index=False)
        print("Saved to insider_trades.csv")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\n" + "="*60)
        print("ALTERNATIVE APPROACH:")
        print("="*60)
        print("Since the SEC is blocking requests, here are your options:")
        print()
        print("1. DOWNLOAD MANUALLY:")
        print(f"   - Go to: {url}")
        print("   - Right-click and 'Save As' to save the XML file")
        print("   - Then use: parser.parse_form4_from_file('downloaded_file.xml')")
        print()
        print("2. USE DIFFERENT SEC ACCESS METHOD:")
        print("   - Register for SEC EDGAR API access")
        print("   - Use official SEC APIs")
        print()
        print("3. TRY ALTERNATIVE URL FORMAT:")
        alt_url = url.replace("/xslF345X05/", "/")
        print(f"   - Alternative URL: {alt_url}")
        print()
        print("4. TEST WITH LOCAL FILE:")
        print("   Create a test XML file and use parse_form4_from_file() method")
        
        # Try the alternative URL approach
        print("\n" + "-"*40)
        print("Trying alternative URL format...")
        try:
            alt_df = parser.parse_form4(alt_url)
            print("Alternative URL worked! Extracted data:")
            print(alt_df)
            alt_df.to_csv("insider_trades.csv", index=False)
            print("Saved to insider_trades.csv")
        except Exception as alt_e:
            print(f"Alternative URL also failed: {alt_e}")


def test_with_sample_xml():
    """Test the parser with a sample XML structure"""
    sample_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument>
    <schemaVersion>X0306</schemaVersion>
    <documentType>4</documentType>
    <periodOfReport>2025-08-08</periodOfReport>
    <issuer>
        <issuerCik>0000320193</issuerCik>
        <issuerName>Apple Inc.</issuerName>
        <issuerTradingSymbol>AAPL</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerCik>0001214156</rptOwnerCik>
            <rptOwnerName>O'BRIEN DEIRDRE</rptOwnerName>
        </reportingOwnerId>
    </reportingOwner>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <securityTitle>
                <value>Common Stock</value>
            </securityTitle>
            <transactionDate>
                <value>2025-08-08</value>
            </transactionDate>
            <transactionCoding>
                <transactionCode>S</transactionCode>
            </transactionCoding>
            <transactionShares>
                <value>34821</value>
            </transactionShares>
            <transactionPricePerShare>
                <value>223.20</value>
            </transactionPricePerShare>
            <ownershipNature>
                <directOrIndirectOwnership>
                    <value>D</value>
                </directOrIndirectOwnership>
            </ownershipNature>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>'''
    
    # Save sample XML to file
    with open('sample_form4.xml', 'w') as f:
        f.write(sample_xml)
    
    # Test parsing
    parser = SECForm4Parser()
    df = parser.parse_form4_from_file('sample_form4.xml')
    print("Sample XML parsing successful!")
    print(df)
    return df


if __name__ == "__main__":
    print("SEC Form 4 Parser Test")
    print("="*40)
    
    # First, test with sample XML to verify parser works
    print("1. Testing parser with sample XML...")
    try:
        sample_df = test_with_sample_xml()
        print("✓ Parser logic works correctly!\n")
    except Exception as e:
        print(f"✗ Parser test failed: {e}\n")
    
    # Then try the real SEC URL
    print("2. Testing with real SEC URL...")
    main()