from langchain_classic.tools import tool
import lorem
from pypdf import PdfReader
import logging
from typing import List
from pubmed_utils import pubmed_search, get_pubmed_contents
from pypaperretriever import PaperRetriever
import os
import string
import random
from fpdf import FPDF
import datetime
import streamlit as st
import json

log = logging.getLogger(__name__)

references = []

@tool
def search_pubmed(query:str)->List[object]:
    """Search research papers related to a pharmaceutical query. The query will return a title, a pmid and a doi"""
    results = pubmed_search(query)
    if results['status_code'] == 200:
        # we have a field 'indices' that will be one or more PubMed ID's
        contents = get_pubmed_contents(results['indices'])
        if contents['status_code'] == 200:
            # content_dict has the pubmedID as the key; value is the related metadata
            content_dict = contents['contents']
            return content_dict
        else:
            return ["no data"]
    else:
        logging.error("Failed to fetch query results from PubMed")
        return ""


@tool
def read_pdf(pmid:str = None, doi:str = None) -> str:
    """Extract text from a scientific paper. We can use either PMID or DOI"""
    logging.info(f"In read_pdf with pmid: '{pmid}' doi: '{doi}'")
    content = None
    if pmid is None and doi is None:
        logging.error("read_pdf call with no parameters")
        raise RuntimeError("Missing parameters")
    if doi is not None:
        content = fetch_paper_by_doi(doi=doi)
    if pmid is not None:
        content = fetch_paper_by_pubmed_id(pmid=pmid)
    text = ""
    try:
        if content:
            reader = PdfReader(content)
            for page in reader.pages:
                text += page.extract_text() or ""
    except FileNotFoundError:
        logging.error(f"PDF file not found at path: {content}")
    except Exception as e:
        logging.error(f"Error reading PDF at {content}: {e}")
    return text

@tool
def summarize_research(text: str) -> str:
    """Summarize pharmaceutical research findings and output as a PDF file. The function takes text content that is
     output into the pdf, and the references are taken from the references global."""
    filename = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{filename}.pdf"
    pdf = FPDF()
    pdf.add_page()
    # Logo
    pdf.image("../images/Pfizer_Logo.png", w=40, keep_aspect_ratio=True)
    pdf.set_font("Times", size=12 )

    # Question
    if 'question' in st.session_state:
        question = st.session_state.question
    pdf.set_x(10)
    pdf.set_font("Helvetica", style='B', size=16)
    pdf.multi_cell(0, 10, align='L', text='Entered Question')
    pdf.set_x(10)
    pdf.set_font("Times", size=12)
    pdf.multi_cell(0, 5, text=question)

    # Discussion
    pdf.set_x(10)
    pdf.set_font("Helvetica", style='B', size=16)
    pdf.multi_cell(0, 10, align='L', text='Discussion')
    pdf.set_x(10)
    pdf.set_font("Times", size=12)
    pdf.multi_cell(0, 5, text=text)

    # References
    pdf.set_x(10)
    pdf.set_font("Helvetica", style='B', size=16)
    pdf.multi_cell(0, 10, align='L', text='References')
    pdf.set_x(10)
    pdf.set_font("Times", size=12)
    references_text = ""
    for reference in references:
        # references_text = (f"{references_text}\n,{reference.identifier} {reference.name}")
        new_references_text = ""
        for k, v in reference.items():
            new_references_text = f"{new_references_text}\n{k}: {v}"
        references_text = f"{new_references_text}\n\n"
    if references_text == "":
        references_text = "References not listed out"
    pdf.multi_cell(0, 5, text=references_text)

    # Disclaimer
    disclaimer = """This generated output is strictly for educational purposes only and it produces does not constitute medical advice nor should it be construed as viable scientific research. Always consult a qualified healthcare professional before starting, changing, or stopping any treatment. Homeopathic, supplemental and alternative therapies should be discussed with your physician."""
    pdf.set_x(10)
    pdf.set_font("Helvetica", style='B', size=16)
    pdf.set_text_color(255,0,0)
    pdf.multi_cell(0, 10, align='L', text='Important Disclaimer')
    pdf.set_text_color(0, 0, 0)
    pdf.set_x(10)
    pdf.set_font("Times", size=12)
    pdf.multi_cell(0, 5, text=disclaimer)


    pdf.output(f"results/{filename}")
    return f"Wrote pdf file {filename}"

#@tool
def fetch_paper_by_doi(doi: str) -> object:
    """Fetch paper using Digital Object ID (DOI)"""
    doi = str(doi).strip().strip('"').strip("'")
    if not doi or doi.lower() == "none":
        log.error("fetch_paper_by_doi called with empty/None doi")
        return ""
    log.info(f"fetch_paper_by_doi: doi = {doi}")
    filename = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
    retriever = PaperRetriever(
        email='test@mail.com',
        doi=doi,
        download_directory="PDF",
        filename=f"{filename}.pdf",
        allow_scihub=True
    )
    download = retriever.download()
    return os.path.join(download.filepath, download.filename)

from dataclasses import  dataclass
@dataclass()
class ReferenceInfo:
    identifier: str
    name: str
    authors: List[str]

@tool
def store_reference_information(referenceInfo: object):
    """This function will store a document reference. The document reference will have an identifier and a document
    name. The document reference will have a list of one or more authors."""
    references.append(referenceInfo)
    # try:
    #     references[referenceInfo.identifier] = {
    #         "identifier": referenceInfo.identifier,
    #         "name": referenceInfo.name,
    #         "authors": referenceInfo.authors
    #     }
    # except KeyError:
    #     log.error(f"Key error in store_reference_information. Received: {referenceInfo}")

#@tool
def fetch_paper_by_pubmed_id(pmid: object) -> object:
    """Fetch paper using PubMed ID. Accepts a plain PMID string, or a JSON object with a 'pmid' or 'doi' key."""
    pm_id = None

    # Normalise: strip whitespace and quotes the agent sometimes wraps around values
    raw = str(pmid).strip().strip('"').strip("'")

    # Try JSON first (agent occasionally passes {"pmid": "..."})
    if raw.startswith("{"):
        try:
            parsed = json.loads(raw)
            pm_id = str(parsed.get("pmid", "")).strip() or None
            if pm_id is None:
                doi = str(parsed.get("doi", "")).strip() or None
                if doi:
                    return fetch_paper_by_doi(doi)
        except (json.JSONDecodeError, AttributeError):
            pass

    # Fall back to treating the raw value as a plain PMID
    if pm_id is None:
        pm_id = raw

    if not pm_id or pm_id.lower() == "none":
        log.error(f"fetch_paper_by_pubmed_id: could not resolve a PMID from input: {pmid!r}")
        return ""

    log.info(f"fetch_paper_by_pubmed_id: pmid = {pm_id}")
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"

    retriever = PaperRetriever(
        email='test@mail.com',
        pmid=pm_id,
        download_directory="PDF",
        filename=f"{filename}.pdf",
        allow_scihub=True
    )
    download = retriever.download()
    if download.is_downloaded:
        return os.path.join(download.filepath, download.filename)
    else:
        log.warning(f"fetch_paper_by_pubmed_id - failed to download pmid {pm_id}")
        return ""

