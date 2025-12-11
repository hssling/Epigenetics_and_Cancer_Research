import urllib.request
import urllib.parse
import json
import time
import os

# Create data directory if not exists
os.makedirs("../data", exist_ok=True)

# Base URL for E-utilities
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# Search Query
TERM = "((epigenetics[Title/Abstract]) AND (cancer prevention[Title/Abstract])) AND (2024/01/01:2025/12/31[Date - Publication])"

def search_pubmed(term, retmax=100):
    params = {
        "db": "pubmed",
        "term": term,
        "retmode": "json",
        "retmax": retmax,
        "sort": "date"
    }
    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/esearch.fcgi?{query_string}"
    
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode())

def fetch_details(id_list):
    ids = ",".join(id_list)
    params = {
        "db": "pubmed",
        "id": ids,
        "retmode": "xml",
        "rettype": "abstract"
    }
    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/efetch.fcgi?{query_string}"
    
    with urllib.request.urlopen(url) as response:
        return response.read().decode()

print(f"Searching for: {TERM}")
try:
    search_results = search_pubmed(TERM)
    id_list = search_results.get("esearchresult", {}).get("idlist", [])

    print(f"Found {len(id_list)} papers.")

    if id_list:
        print("Fetching abstracts...")
        xml_data = fetch_details(id_list)
        
        # Save raw XML
        with open("../data/raw_data.xml", "w", encoding="utf-8") as f:
            f.write(xml_data)
            
        print("Data saved to ../data/raw_data.xml")
    else:
        print("No papers found.")
except Exception as e:
    print(f"Error: {e}")
