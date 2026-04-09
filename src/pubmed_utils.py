import requests
import xml.etree.ElementTree as ET
from typing import List, Dict
import logging

log = logging.getLogger(__name__)

base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

def pubmed_search(query: str) -> str:
    url = base_url+"/esearch.fcgi"
    params = {
        'db': 'pubmed',
        'term': query
    }

    response = requests.get(url=url, params=params)
    if response.status_code == 200:
        indices = []
        et = ET.fromstring(response.text)
        ids = et.findall('.//IdList/Id')
        for id in ids:
            indices.append(id.text)
        return{ "status_code": response.status_code, "indices": indices}
    else:
        log.error("An error occurred when calling pubmed_search: " + response[:1000])
        return{ "status_code": response.status_code, "response": response.text[:1000]}


def get_pubmed_summaries(ids: List[int]) -> List[object]:
    pass

def get_pubmed_contents(ids: List[int]) -> Dict[str, object]:
    content_dict = {}
    url = base_url + "esummary.fcgi"
    params = {
        'db': 'pubmed',
        'id': ",".join(ids)
    }
    response = requests.get(url=url, params=params)
    if response.status_code == 200:
        et = ET.fromstring(response.content.decode())
        docs = et.findall('DocSum')
        for summary in docs:
            id = summary.find('Id').text
            title = ''
            pmid = ''
            doi = ''
            try:
                title = summary.find("Item[@Name='Title']").text
            except KeyError:
                title = 'Untitled'
            try:
                pmid = summary.find("Item[@Name='ArticleIds']/Item[@Name='pubmed']").text
            except:
                pass
            try:
                doi = summary.find("Item[@Name='ArticleIds']/Item[@Name='doi']").text
            except:
                pass
            content_dict[id] = [{"title": title, "PMID": pmid, "doi": doi}]
        return {"status_code": response.status_code, "contents": content_dict}
    else:
        log.error("An error occurred when calling get_pubmed_contents: " + response[:1000])
        return {"status_code": response.status_code, "response": response.text[:1000]}

if __name__ == '__main__':
    response = pubmed_search("The usage of mRNA vaccines for influenza")
    if response['status_code'] == 200:
        res = get_pubmed_contents(response['indices'])
        print(res['response'].content.decode())
    else:
        print("unexpected results")