from __future__ import annotations

import datetime
import json
import logging
import random
import string
from dataclasses import dataclass
from pathlib import Path
from typing import List

import streamlit as st
from fpdf import FPDF
from langchain_classic.tools import tool
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from concurrent.futures import ThreadPoolExecutor, as_completed
from pubmed_utils import pubmed_search, get_pubmed_contents
from pypdf import PdfReader
from pypaperretriever import PaperRetriever

log = logging.getLogger(__name__)

# Absolute paths anchored to this file — immune to working-directory changes
_SRC_DIR     = Path(__file__).parent.resolve()
_REPO_ROOT   = _SRC_DIR.parent.resolve()
_PDF_DIR     = _SRC_DIR / "PDF"
_RESULTS_DIR = _SRC_DIR / "results"
_LOGO_PATH   = _REPO_ROOT / "images" / "Pfizer_Logo.png"

references: list = []

# Injected by create_agent so tools can use the same LLM for summarisation
_llm: ChatOllama | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _unique_stem() -> str:
    ts   = datetime.datetime.now().strftime("%Y-%m-%d-%H_%M_%S")
    rand = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{ts}_{rand}"


def _resolve_download_path(download) -> Path | None:
    """Resolve the full path of a downloaded file from a PaperRetriever object."""
    if not download.is_downloaded:
        return None

    filepath = Path(download.filepath) if download.filepath else None
    filename = Path(download.filename) if download.filename else None

    if filepath and filepath.is_file():
        return filepath
    if filepath and filename:
        candidate = filepath / filename.name
        if candidate.exists():
            return candidate
    if filename and filename.exists():
        return filename
    if filename:
        candidate = _PDF_DIR / filename.name
        if candidate.exists():
            return candidate

    log.error(f"Could not resolve download path: filepath={download.filepath!r}, filename={download.filename!r}")
    return None


def _summarise_for_question(full_text: str, question: str) -> str:
    """Use the LLM to compress a full paper into a focused summary.

    This is the key step that lets the agent work with complete paper content
    without blowing up the ReAct scratchpad context window.
    """
    if _llm is None:
        # Fallback: return first 4000 chars if no LLM is wired up yet
        return full_text[:4000]

    prompt = (
        f"You are a biomedical research assistant. "
        f"A researcher asked: \"{question}\"\n\n"
        f"Below is the full text of a scientific paper. "
        f"Write a concise summary (300-500 words) that captures everything relevant to answering the question. "
        f"Include key findings, methods, conclusions, and any statistics. "
        f"Do not add commentary, licensing notes, or offers to help.\n\n"
        f"PAPER TEXT:\n{full_text}"
    )
    try:
        response = _llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as exc:
        log.warning(f"_summarise_for_question failed: {exc} — returning raw excerpt")
        return full_text[:4000]


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def search_pubmed(query: str) -> List[object]:
    """Search research papers related to a pharmaceutical query.
    Returns a dict keyed by PMID; each value contains title, PMID and DOI."""
    results = _search_pubmed_cached(query)
    # Trigger parallel prefetch of all returned PMIDs in the background
    if isinstance(results, dict):
        pmids = list(results.keys())
        if pmids and callable(_on_search_done):
            try:
                _on_search_done(pmids)
            except Exception as exc:
                log.warning(f"prefetch trigger failed: {exc}")
    return results


_on_search_done = None  # injected by main.py after each search


@st.cache_data(show_spinner=False, ttl=3600)
def _search_pubmed_cached(query: str):
    """Cached PubMed search — identical queries within 1 hour skip the API call."""
    results = pubmed_search(query)
    if results["status_code"] == 200:
        contents = get_pubmed_contents(results["indices"])
        if contents["status_code"] == 200:
            return contents["contents"]
        return ["no data"]
    log.error("Failed to fetch query results from PubMed")
    return []


def prefetch_papers(pmids: list[str]) -> dict[str, Path | None]:
    """Download up to the first 2 papers in parallel with a polite delay.

    Limiting concurrency avoids 429 rate-limit errors from Unpaywall/Crossref.
    Only prefetches the top 2 results — the agent rarely reads more than that.
    """
    _PDF_DIR.mkdir(parents=True, exist_ok=True)

    def _fetch(pmid: str):
        import time
        time.sleep(0.5)  # small stagger to avoid simultaneous API hits
        return pmid, fetch_paper_by_pubmed_id(pmid)

    results = {}
    # Cap at 2 — no point downloading papers the agent won't reach
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(_fetch, pmid): pmid for pmid in pmids[:2]}
        for future in as_completed(futures):
            pmid, path = future.result()
            results[pmid] = path
            log.info(f"prefetch_papers: {pmid} → {path}")
    return results


# Cache of pre-fetched paths so read_pdf can skip re-downloading
_prefetch_cache: dict[str, Path | None] = {}


@tool
def read_pdf(pmid: str = None, doi: str = None) -> str:
    """Download and extract a scientific paper by PMID or DOI.
    Returns a focused summary of the paper relevant to the current research question,
    or an ERROR: string if the paper could not be retrieved."""
    log.info(f"read_pdf called — pmid={pmid!r}  doi={doi!r}")

    if pmid is None and doi is None:
        return "ERROR: read_pdf requires either a pmid or doi argument."

    pdf_path: Path | None = None
    if doi:
        pdf_path = fetch_paper_by_doi(doi)
    if pmid and pdf_path is None:
        # Check prefetch cache before downloading
        pdf_path = _prefetch_cache.get(pmid) or fetch_paper_by_pubmed_id(pmid)

    if not pdf_path or not pdf_path.exists():
        return f"ERROR: Could not download PDF for pmid={pmid!r} doi={doi!r}. Do not summarise this paper."

    log.info(f"read_pdf: extracting text from {pdf_path}")
    try:
        reader = PdfReader(str(pdf_path))
        full_text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as exc:
        log.error(f"read_pdf: failed to parse {pdf_path}: {exc}")
        return f"ERROR: Could not parse PDF ({exc}). Do not summarise this paper."

    if not full_text:
        return f"ERROR: PDF at {pdf_path} contained no extractable text."

    log.info(f"read_pdf: extracted {len(full_text)} chars, summarising for question context")
    question = st.session_state.get("question", "")
    return _summarise_for_question(full_text, question)



@tool
def summarize_research(text: str) -> str:
    """Summarize pharmaceutical research findings and write a PDF report.

    The text argument should be the research content to summarise.
    Returns the path of the generated PDF, or an error string.
    """
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    out_path = _RESULTS_DIR / f"{_unique_stem()}.pdf"

    pdf = FPDF()
    pdf.add_page()

    # Logo — skip gracefully if the asset is missing
    if _LOGO_PATH.exists():
        pdf.image(str(_LOGO_PATH), w=40, keep_aspect_ratio=True)
    else:
        log.warning(f"summarize_research: logo not found at {_LOGO_PATH}, skipping.")

    # Question
    question = st.session_state.get("question", "(question not recorded)")
    pdf.set_x(10)
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.multi_cell(0, 10, align="L", text="Entered Question")
    pdf.set_x(10)
    pdf.set_font("Times", size=12)
    pdf.multi_cell(0, 5, text=question)

    # Discussion
    pdf.set_x(10)
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.multi_cell(0, 10, align="L", text="Discussion")
    pdf.set_x(10)
    pdf.set_font("Times", size=12)
    pdf.multi_cell(0, 5, text=text)

    # References
    pdf.set_x(10)
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.multi_cell(0, 10, align="L", text="References")
    pdf.set_x(10)
    pdf.set_font("Times", size=12)
    if references:
        refs_text = ""
        for ref in references:
            entry = "\n".join(f"{k}: {v}" for k, v in ref.items()) if isinstance(ref, dict) else str(ref)
            refs_text += entry + "\n\n"
    else:
        refs_text = "References not listed."
    pdf.multi_cell(0, 5, text=refs_text)

    # Disclaimer
    pdf.set_x(10)
    pdf.set_font("Helvetica", style="B", size=16)
    pdf.set_text_color(255, 0, 0)
    pdf.multi_cell(0, 10, align="L", text="Important Disclaimer")
    pdf.set_text_color(0, 0, 0)
    pdf.set_x(10)
    pdf.set_font("Times", size=12)
    pdf.multi_cell(0, 5, text=(
        "This generated output is strictly for educational purposes only and does not "
        "constitute medical advice nor should it be construed as viable scientific research. "
        "Always consult a qualified healthcare professional before starting, changing, or "
        "stopping any treatment."
    ))

    pdf.output(str(out_path))
    log.info(f"summarize_research: wrote report to {out_path}")
    return f"Report written to {out_path}"


# ── Internal download helpers (not exposed as agent tools) ────────────────────

def fetch_paper_by_doi(doi: str) -> Path | None:
    """Download a paper by DOI. Returns the resolved Path or None on failure."""
    doi = str(doi).strip().strip('"').strip("'")
    if not doi or doi.lower() == "none":
        log.error("fetch_paper_by_doi: called with empty/None doi")
        return None

    log.info(f"fetch_paper_by_doi: doi={doi}")
    _PDF_DIR.mkdir(parents=True, exist_ok=True)

    retriever = PaperRetriever(
        email="test@mail.com",
        doi=doi,
        download_directory=str(_PDF_DIR),
        filename=f"{_unique_stem()}.pdf",
        allow_scihub=True,
    )
    download = retriever.download()
    path = _resolve_download_path(download)
    if path is None:
        log.warning(f"fetch_paper_by_doi: download failed for doi={doi}")
    return path


def fetch_paper_by_pubmed_id(pmid: object) -> Path | None:
    """Download a paper by PMID. Returns the resolved Path or None on failure.

    Accepts a plain PMID string or a JSON object with 'pmid'/'doi' keys.
    """
    raw = str(pmid).strip().strip('"').strip("'")

    # Handle JSON input from the agent
    pm_id: str | None = None
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

    if pm_id is None:
        pm_id = raw

    if not pm_id or pm_id.lower() == "none":
        log.error(f"fetch_paper_by_pubmed_id: cannot resolve PMID from {pmid!r}")
        return None

    log.info(f"fetch_paper_by_pubmed_id: pmid={pm_id}")
    _PDF_DIR.mkdir(parents=True, exist_ok=True)

    retriever = PaperRetriever(
        email="test@mail.com",
        pmid=pm_id,
        download_directory=str(_PDF_DIR),
        filename=f"{_unique_stem()}.pdf",
        allow_scihub=True,
    )
    download = retriever.download()
    path = _resolve_download_path(download)
    if path is None:
        log.warning(f"fetch_paper_by_pubmed_id: download failed for pmid={pm_id}")
    return path


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class ReferenceInfo:
    identifier: str
    name: str
    authors: List[str]


@tool
def store_reference_information(referenceInfo: object) -> str:
    """Store a document reference (identifier, name, authors) for inclusion in reports."""
    references.append(referenceInfo)
    return "Reference stored."
