import requests


class ConceptNetAPI:
    @staticmethod
    def find_by_token(token):
        relations = []
        obj = requests.get('http://api.conceptnet.io/c/en/' + token).json()
        for edge in obj['edges']:
            relations += (edge['start']['term'], edge['rel']['label'], edge['end']['term'])
        return relations

    @staticmethod
    def find_by_tokens(token1, token2):
        relations = []
        obj = requests.get('http://api.conceptnet.io/query?other=/c/en/' + token1 + '&node=/c/en/' + token2).json()
        for edge in obj['edges']:
            relations += (edge['start']['term'], edge['rel']['label'], edge['end']['term'])
        return relations
