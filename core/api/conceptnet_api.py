import requests


class ConceptNetAPI:
    @staticmethod
    def find_by_token(token: str) -> next:
        obj = requests.get('http://api.conceptnet.io/c/en/' + token).json()
        for edge in obj['edges']:
            yield (str(edge['start']['term']), str(edge['rel']['label']), str(edge['end']['term']))

    @staticmethod
    def find_by_tokens(token1: str, token2: str) -> list:
        obj = requests.get('http://api.conceptnet.io/query?other=/c/en/' + token1 + '&node=/c/en/' + token2).json()
        for edge in obj['edges']:
            yield (str(edge['start']['term']), str(edge['rel']['label']), str(edge['end']['term']))
