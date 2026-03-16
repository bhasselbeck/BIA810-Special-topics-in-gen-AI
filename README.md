# Chad Gippity output
## What the Agent Does

User asks something like:

“Find evidence supporting the use of mRNA vaccines for respiratory viruses.”

The agent:
* Searches research databases
* Retrieves papers
* Extracts relevant results
* Summarizes findings
* Generates a structured report

## Tool Calling

The agent can call tools like:

* Paper Search Tool
* Query PubMed API
* PDF Reader Tool
* Extract text from downloaded papers
* Table Extractor
* Pull clinical results
* Citation Generator
* Format references

Example tool chain:

`query_papers() → download_pdf() → extract_text() → summarize()`
## Why Pharma Cares

Companies like Pfizer constantly analyze research when designing:

vaccines

oncology drugs

clinical trials

This project demonstrates automated scientific literature review.

## Local Stack

You can run it locally with:

* LLM: Llama 3 or Mistral
* Framework: LangChain or AutoGen
* Embeddings: SentenceTransformers
* Vector DB: Chroma
* Paper source: PubMed API


# PubMed API

To query PubMed API, a suite of 9 server side programs known as the **Entrez Programming Utilities (E-Utilities)** is
provided by the National Center for BioTechnology.

The typical workflow involves two main steps: using `ESearch` to find relevant article ID's, and then using `EFetch` or
`ESummary` to retrieve the actual data.

### Base url
All E-utilities start with the base url `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`

# Steps
## Step 1. Searching for articles with ESearch
* Endpoint `esearch.gcgi`
#### Parameters
  * `db`: The database to search (e.g. `pubmed`)
  * `term`: your search query
  * `api_key`: optional API key (we are limited to 3 requests per second without API key)
  * `retmax`: The maximum number of UID's to return. Default is 20, max is 10,000.

## Step 2. Retrieving details with EFetch or ESummary
### Retrieving summaries with ESummary
* Endpoint: `esummary.fcgi`
#### Parameters
    * `db`: `pubmed`
    * `id`: a comma-separated list of PMID's
    * `api_key`: optional API key

### Retrieving full records with EFetch
* Endpoint: `efetch.fcgi`
#### Parameters
    * `id`: `pubmed`
    * `id`: A comma-separated list of PMID's
    * `retmode`: The output format, typically `xml` or `text`
    * `api_key`: optional API key