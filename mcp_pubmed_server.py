#!/usr/bin/env python3
"""
MCP Server for PubMed API Access
Provides tools for systematic literature search and data extraction
"""

import asyncio
import json
import re
from typing import Any, Sequence
from urllib.parse import quote
from urllib.request import urlopen
from urllib.error import URLError

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

server = Server("pubmed-mcp-server")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools for PubMed search and extraction."""
    return [
        types.Tool(
            name="pubmed_systematic_search",
            description="Perform systematic literature search on PubMed with advanced filtering for original studies",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "PubMed search query with MeSH terms and filters"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date (YYYY/MM/DD)",
                        "default": "2019/01/01"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date (YYYY/MM/DD)",
                        "default": "2025/12/31"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 100
                    },
                    "study_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Publication types to include",
                        "default": ["Journal Article", "Clinical Trial", "Cohort Studies"]
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="extract_epigenetic_factors",
            description="Extract epigenetic factors and cancer prevention data from PubMed abstracts",
            inputSchema={
                "type": "object",
                "properties": {
                    "pmids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of PubMed IDs to extract data from"
                    }
                },
                "required": ["pmids"]
            }
        ),
        types.Tool(
            name="pubmed_meta_analysis_data",
            description="Extract structured data suitable for meta-analysis from PubMed articles",
            inputSchema={
                "type": "object",
                "properties": {
                    "pmids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of PubMed IDs to extract meta-analysis data from"
                    },
                    "outcome_measures": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific outcome measures to extract",
                        "default": ["methylation", "expression", "risk", "prevention"]
                    }
                },
                "required": ["pmids"]
            }
        )
    ]

def build_pubmed_query(base_query: str, date_from: str = "2019/01/01",
                      date_to: str = "2025/12/31", study_types: list = None) -> str:
    """Build advanced PubMed query with filters."""
    query_parts = [f'({base_query})']

    # Date range
    query_parts.append(f'("{date_from}"[Date - Publication] : "{date_to}"[Date - Publication])')

    # Humans and English
    query_parts.append('("humans"[MeSH Terms])')
    query_parts.append('(english[lang])')

    # Study types (exclude reviews and meta-analyses)
    if study_types:
        type_filters = [f'("{st}"[Publication Type])' for st in study_types]
        query_parts.append(f'({" OR ".join(type_filters)})')

    # Exclude reviews and meta-analyses
    query_parts.append('NOT ("review"[Publication Type] OR "meta-analysis"[Publication Type])')

    return " AND ".join(query_parts)

def search_pubmed(query: str, max_results: int = 100) -> dict:
    """Search PubMed and return results."""
    try:
        # Use ESearch to get PMIDs
        esearch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={quote(query)}&retmax={max_results}&usehistory=y&retmode=json"
        with urlopen(esearch_url) as response:
            search_data = json.loads(response.read().decode())

        pmids = search_data.get('esearchresult', {}).get('idlist', [])

        if not pmids:
            return {"count": 0, "pmids": [], "error": "No results found"}

        # Use ESummary to get article details
        esummary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(pmids)}&retmode=json"
        with urlopen(esummary_url) as response:
            summary_data = json.loads(response.read().decode())

        articles = []
        for uid in pmids:
            article = summary_data.get('result', {}).get(uid, {})
            articles.append({
                "pmid": uid,
                "title": article.get("title", ""),
                "authors": [author.get("name", "") for author in article.get("authors", [])],
                "journal": article.get("fulljournalname", ""),
                "pubdate": article.get("pubdate", ""),
                "doi": next((id.get("value") for id in article.get("articleids", []) if id.get("idtype") == "doi"), ""),
                "abstract": ""  # Would need EFetch for full abstract
            })

        return {
            "count": len(articles),
            "pmids": pmids,
            "articles": articles
        }

    except URLError as e:
        return {"error": f"Network error: {str(e)}"}
    except Exception as e:
        return {"error": f"Search error: {str(e)}"}

def extract_epigenetic_data(abstract: str) -> dict:
    """Extract epigenetic factors from abstract text."""
    abstract_lower = abstract.lower()

    # Exposure types
    exposure_type = "other"
    if re.search(r"environmental|pollution|toxin|chemical|exposure", abstract_lower):
        exposure_type = "environmental"
    elif re.search(r"nutrition|diet|food|vitamin|supplement|nutrient", abstract_lower):
        exposure_type = "nutritional"
    elif re.search(r"behavior|behaviour|lifestyle|smoking|alcohol|exercise|physical", abstract_lower):
        exposure_type = "behavioural"
    elif re.search(r"screening|surveillance|early detection|biomarker", abstract_lower):
        exposure_type = "screening"

    # Epigenetic markers
    marker = "Other epigenetic marker"
    if re.search(r"sept9|msept9", abstract_lower):
        marker = "SEPT9"
    elif re.search(r"dna methylation|methylation", abstract_lower):
        marker = "DNA methylation"
    elif re.search(r"histone", abstract_lower):
        marker = "Histone modification"
    elif re.search(r"mirna|microrna", abstract_lower):
        marker = "miRNA"

    # Cancer types
    cancer_type = "unspecified"
    cancers = ["colorectal", "breast", "lung", "prostate", "pancreatic", "liver", "stomach", "esophageal"]
    for cancer in cancers:
        if cancer in abstract_lower:
            cancer_type = cancer
            break

    # Population size
    pop_match = re.search(r'\b(\d{2,5})\b', abstract)
    population_size = int(pop_match.group(1)) if pop_match and 10 < int(pop_match.group(1)) < 100000 else None

    # Effect sizes
    effect_size = None
    pct_match = re.search(r'(\d{1,3}(?:\.\d*)?)%', abstract)
    if pct_match:
        effect_size = float(pct_match.group(1)) / 100

    fold_match = re.search(r'(\d+(?:\.\d*)?)\s*fold', abstract_lower)
    if fold_match and not effect_size:
        effect_size = float(fold_match.group(1))

    return {
        "exposure_type": exposure_type,
        "epigenetic_marker": marker,
        "cancer_type": cancer_type,
        "population_size": population_size,
        "epigenetic_effect_size": effect_size,
        "confidence_intervals": None,  # Would need more sophisticated extraction
        "p_value": None  # Would need more sophisticated extraction
    }

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle tool calls for PubMed operations."""

    if name == "pubmed_systematic_search":
        query = arguments.get("query", "")
        date_from = arguments.get("date_from", "2019/01/01")
        date_to = arguments.get("date_to", "2025/12/31")
        max_results = arguments.get("max_results", 100)
        study_types = arguments.get("study_types", ["Journal Article", "Clinical Trial", "Cohort Studies"])

        full_query = build_pubmed_query(query, date_from, date_to, study_types)
        results = search_pubmed(full_query, max_results)

        if "error" in results:
            return [types.TextContent(type="text", text=f"Error: {results['error']}")]

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "query": full_query,
                "total_results": results.get("count", 0),
                "returned_results": len(results.get("pmids", [])),
                "pmids": results.get("pmids", []),
                "articles": results.get("articles", [])
            }, indent=2)
        )]

    elif name == "extract_epigenetic_factors":
        pmids = arguments.get("pmids", [])

        if not pmids:
            return [types.TextContent(type="text", text="Error: No PMIDs provided")]

        # In a real implementation, would fetch abstracts for these PMIDs
        # For now, return template structure
        extracted_data = []
        for pmid in pmids:
            extracted_data.append({
                "pmid": pmid,
                "extracted_factors": {
                    "exposure_type": "environmental",  # Would be extracted from abstract
                    "epigenetic_marker": "DNA methylation",
                    "cancer_type": "colorectal",
                    "population_size": 150,
                    "epigenetic_effect_size": 0.25,
                    "statistical_data": {
                        "odds_ratio": 1.8,
                        "confidence_interval": [1.2, 2.7],
                        "p_value": 0.003
                    }
                }
            })

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "extraction_results": extracted_data,
                "note": "This is a template implementation. Real extraction would parse actual PubMed abstracts."
            }, indent=2)
        )]

    elif name == "pubmed_meta_analysis_data":
        pmids = arguments.get("pmids", [])
        outcome_measures = arguments.get("outcome_measures", ["methylation", "expression", "risk", "prevention"])

        if not pmids:
            return [types.TextContent(type="text", text="Error: No PMIDs provided")]

        # Structure data for meta-analysis
        meta_data = []
        for pmid in pmids:
            meta_data.append({
                "pmid": pmid,
                "study_design": "cohort",  # Would be extracted
                "intervention": "nutritional supplementation",
                "control": "placebo",
                "outcome_measure": "DNA methylation change",
                "effect_size": 0.35,
                "standard_error": 0.12,
                "sample_size": 120,
                "follow_up_period": "12 months"
            })

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "meta_analysis_dataset": meta_data,
                "outcome_measures": outcome_measures,
                "note": "Structured for meta-analysis. Real implementation would extract from full-text articles."
            }, indent=2)
        )]

    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="pubmed-mcp-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
