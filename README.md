# BIA 810 Project
### Team: 
* Mick Twohig 
* Matt Kelly
* Brian Hasselbeck

# Project Overview
The aim of the project is to provide an application for researchers that will allow
* the researcher to enter a search criteria,
* the system will query PubMed for any pertinent documentation,
* the system will fetch any relevant PDF copies of these papers,
* the system will generate a summary and create an output document of this summary,
* source documents will be cited accordingly.

## Tools used
We will implement the solution as a locally running agent. We will use [Ollama](https://ollama.com/)
as the runtime for the LLM models, Langchain and Langgraph for the orchestration,  [Streamlit](https://streamlit.io/) 
for UI, and some of the common python libraries.


### PyPaperRetriever
[PyPaperRetriever](https://joss.theoj.org/papers/10.21105/joss.08135) is a Python library that will attempt to find 
and download papers. It can start from Digital Object Identifier(doi) or PubMedID.
It will search a variety of sources, and prioritizes getting the papers using legitimate means.
##### Installation
```
pip install git+https://github.com/josephisaacturner/pypaperretriever.git
```

*NOTE TO TEAM: We're looking at putting RAG into the mix, so if we go with that will need a little text contented added here for this*

# Usage
The project relies on a local [Ollama](https://ollama.com/) instance. Installation of this is outside of our current scope, 
but is fortunately a well-documented process on the project website.

The project requires the following local models, all of which can be pulled via Ollama:
```console
$ ollama pull qwen3:8b
$ ollama pull llama3:8b
$ ollama pull gpt-oss:latest
```

## Setup

### Python Version
**Python 3.13 is required.** The `audioop-lts` dependency is a backport of the `audioop` module
that was removed in Python 3.13, and is only needed (and only compatible) with Python 3.13+.

### Install dependencies
```console
$ pip install -r requirements.txt
```

## Running the Application

Our application provides a [Streamlit](https://streamlit.io/) user interface. To run the application,
navigate to the project root and point Streamlit at the `src` directory:
```console
$ streamlit run src/main.py
```
