import requests

import xml.etree.ElementTree as ET

from typing import List

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
        print(f"Len indicates = {len(indices)}")
        for id in ids:
            indices.append(id.text)
        return{ "status_code": response.status_code, "indices": indices}
    else:
        return{ "status_code": response.status_code, "response": response.text[:1000]}


def get_pubmed_content(ids: List[int]) -> str:
    url = base_url + "esummary.fcgi"
    params = {
        'db': 'pubmed',
        'id': ",".join(ids)
    }
    response = requests.get(url=url, params=params)
    if response.status_code == 200:
        return {"status_code": response.status_code, "response": response}
    else:
        return {"status_code": response.status_code, "response": response.text[:1000]}


if __name__ == '__main__':
    response = pubmed_search("The usage of mRNA vaccines for influenza")
    if response['status_code'] == 200:
        res = get_pubmed_content(response['indices'])
        print(res['response'].content.decode())
    else:
        print("unexpected results")