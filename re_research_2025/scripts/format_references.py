import xml.etree.ElementTree as ET

target_pmids = [
    "41299324", "40663150", "40869316", "41108343", 
    "40545531", "40805232", "39312452", "39537414"
]

def get_text(element):
    return element.text if element is not None else ""

def format_references():
    file_path = r"d:\research-automation\Epigenetics research\re_research_2025\data\raw_data.xml"
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    formatted_refs = {}
    
    for article in root.findall(".//PubmedArticle"):
        pmid = article.find(".//PMID").text
        if pmid in target_pmids:
            # Authors
            author_list = []
            authors = article.findall(".//Author")
            for author in authors:
                lastname = get_text(author.find("LastName"))
                initials = get_text(author.find("Initials"))
                if lastname:
                    author_list.append(f"{lastname} {initials}")
            
            if len(author_list) > 6:
                authors_str = ", ".join(author_list[:6]) + ", et al"
            else:
                authors_str = ", ".join(author_list)
                
            # Title
            title = get_text(article.find(".//ArticleTitle"))
            
            # Journal
            journal = article.find(".//Journal")
            journal_title = get_text(journal.find("ISOAbbreviation"))
            if not journal_title:
                journal_title = get_text(journal.find("Title"))
                
            # Date
            pubdate = journal.find("JournalIssue/PubDate")
            year = get_text(pubdate.find("Year"))
            
            # Vol/Issue
            volume = get_text(journal.find("JournalIssue/Volume"))
            issue = get_text(journal.find("JournalIssue/Issue"))
            
            # Pages
            pagination = article.find(".//Pagination/MedlinePgn")
            pages = get_text(pagination)
            
            # Construct Vancouver string
            ref = f"{authors_str}. {title} {journal_title}. {year}"
            if volume:
                ref += f";{volume}"
            if issue:
                ref += f"({issue})"
            if pages:
                ref += f":{pages}"
            ref += "."
            
            formatted_refs[pmid] = ref

    with open("references.txt", "w", encoding="utf-8") as f:
        # Print in order
        for i, pmid in enumerate(target_pmids, 1):
            if pmid in formatted_refs:
                f.write(f"{i}. {formatted_refs[pmid]}\n")
            else:
                f.write(f"{i}. PMID {pmid} (Details not found in raw_data.xml)\n")
    print("Done writing references.txt")

if __name__ == "__main__":
    print("Starting format_references.py...")
    try:
        format_references()
    except Exception as e:
        print(f"Error: {e}")
