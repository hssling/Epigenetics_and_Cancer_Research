import xml.etree.ElementTree as ET
import csv
import re
import os

def parse_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    articles = []
    
    for article in root.findall(".//PubmedArticle"):
        pmid = article.find(".//PMID").text
        title_elem = article.find(".//ArticleTitle")
        title = "".join(title_elem.itertext()) if title_elem is not None else "No Title"
        
        abstract_elem = article.find(".//Abstract/AbstractText")
        abstract = "".join(abstract_elem.itertext()) if abstract_elem is not None else ""
        
        journal_elem = article.find(".//Journal/Title")
        journal = journal_elem.text if journal_elem is not None else "Unknown"
        
        pubdate_year = article.find(".//PubDate/Year")
        if pubdate_year is None:
             # Fallback for MedlineDate
             medline_date = article.find(".//PubDate/MedlineDate")
             year = medline_date.text[:4] if medline_date is not None else "2024" # Default to 2024 if unknown but in range
        else:
            year = pubdate_year.text
            
        articles.append({
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "journal": journal,
            "year": year
        })
    return articles

def extract_info(text):
    text = text.lower()
    
    # Intervention
    intervention = "Other"
    if any(x in text for x in ["diet", "nutrition", "food", "supplement", "vitamin"]):
        intervention = "Nutritional"
    elif any(x in text for x in ["exercise", "physical activity", "lifestyle", "smoking", "alcohol", "sleep"]):
        intervention = "Behavioural"
    elif any(x in text for x in ["pollution", "environmental", "exposure", "chemical", "toxin"]):
        intervention = "Environmental"
    elif any(x in text for x in ["screening", "early detection", "biomarker"]):
        intervention = "Screening"
        
    # Cancer Type
    cancer = "General/Unspecified"
    cancers = ["breast", "lung", "colorectal", "prostate", "liver", "gastric", "cervical", "ovarian", "pancreatic", "bladder"]
    for c in cancers:
        if c in text:
            cancer = c.capitalize()
            break
            
    # Marker
    marker = "Unspecified"
    if "methylation" in text:
        marker = "DNA Methylation"
    elif "mirna" in text or "microrna" in text:
        marker = "miRNA"
    elif "histone" in text:
        marker = "Histone Modification"
        
    return intervention, cancer, marker

def main():
    start_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(start_dir, "../data")
    xml_file = os.path.join(data_dir, "raw_data.xml")
    csv_file = os.path.join(data_dir, "extracted_data.csv")
    report_file = os.path.join(data_dir, "analysis_results.md")
    
    if not os.path.exists(xml_file):
        print("No raw data found.")
        return

    articles = parse_xml(xml_file)
    print(f"Parsed {len(articles)} articles.")
    
    extracted_data = []
    
    for art in articles:
        interv, cancer, marker = extract_info(art["title"] + " " + art["abstract"])
        extracted_data.append({
            "PMID": art["pmid"],
            "Title": art["title"],
            "Year": art["year"],
            "Intervention": interv,
            "Cancer Type": cancer,
            "Epigenetic Marker": marker,
            "Journal": art["journal"]
        })
        
    # Save to CSV
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["PMID", "Title", "Year", "Intervention", "Cancer Type", "Epigenetic Marker", "Journal"])
        writer.writeheader()
        writer.writerows(extracted_data)
        
    print(f"Extracted data saved to {csv_file}")
    
    # Generate Summary Stats
    intervention_counts = {}
    cancer_counts = {}
    marker_counts = {}
    
    for item in extracted_data:
        intervention_counts[item["Intervention"]] = intervention_counts.get(item["Intervention"], 0) + 1
        cancer_counts[item["Cancer Type"]] = cancer_counts.get(item["Cancer Type"], 0) + 1
        marker_counts[item["Epigenetic Marker"]] = marker_counts.get(item["Epigenetic Marker"], 0) + 1
        
    # Write Report
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# Analysis Results: Factors Influencing Epigenetics in Cancer Prevention (2024-2025)\n\n")
        f.write(f"**Total Studies Analyzed**: {len(extracted_data)}\n\n")
        
        f.write("## Intervention Types\n")
        for k, v in intervention_counts.items():
            f.write(f"- **{k}**: {v} ({v/len(extracted_data)*100:.1f}%)\n")
            
        f.write("\n## Cancer Types\n")
        for k, v in cancer_counts.items():
            f.write(f"- **{k}**: {v}\n")
            
        f.write("\n## Epigenetic Markers\n")
        for k, v in marker_counts.items():
            f.write(f"- **{k}**: {v}\n")
            
        f.write("\n## Detailed Study List\n")
        f.write("| PMID | Year | Cancer Type | Intervention | Marker | Title |\n")
        f.write("|---|---|---|---|---|---|\n")
        for item in extracted_data:
            title_short = (item["Title"][:50] + '..') if len(item["Title"]) > 50 else item["Title"]
            f.write(f"| {item['PMID']} | {item['Year']} | {item['Cancer Type']} | {item['Intervention']} | {item['Epigenetic Marker']} | {title_short} |\n")
            
    print(f"Analysis report saved to {report_file}")

if __name__ == "__main__":
    main()
