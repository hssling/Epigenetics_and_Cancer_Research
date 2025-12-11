import xml.etree.ElementTree as ET
import os

target_pmids = [
    "40663150", 
    "41108343", 
    "40869316", 
    "40805232", 
    "39312452", 
    "39537414",
    "41299324",
    "40545531"
]

file_path = r"d:\research-automation\Epigenetics research\re_research_2025\data\raw_data.xml"

try:
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    output_file = r"d:\research-automation\Epigenetics research\re_research_2025\data\extracted_abstracts.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        found_count = 0
        for article in root.findall(".//PubmedArticle"):
            pmid_elem = article.find(".//PMID")
            if pmid_elem is not None and pmid_elem.text in target_pmids:
                found_count += 1
                title = article.find(".//ArticleTitle").text
                abstract_elem = article.find(".//Abstract/AbstractText")
                
                # abstract might be a list of elements or text
                if abstract_elem is not None:
                    # Sometimes AbstractText has labels, handle that if needed or just get all text
                    # Ideally itertext() to get all nested text
                    abstract = "".join(article.find(".//Abstract").itertext())
                else:
                    abstract = "No Abstract"
                    
                f.write(f"--- PMID: {pmid_elem.text} ---\n")
                f.write(f"TITLE: {title}\n")
                f.write(f"ABSTRACT: {abstract}\n\n")

        if found_count == 0:
            f.write("No articles found with those PMIDs.\n")
            
    print(f"Data saved to {output_file}")

except Exception as e:
    print(f"Error: {e}")
