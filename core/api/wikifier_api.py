import requests


class WikifierAPI:
    @staticmethod
    def find_entities(input_text: str, user_key: str, include_pos_tags: bool = True) -> object:
        """
    Generate an object that can be passed to Wikifier to get the generated response
        :param include_pos_tags: Default value is True. Returns POS tagged words if set to True
        :param input_text: Text to find entities in
        :param user_key: API key for accessing wikifier
        :return: object containing list of annotations, spaces, words, ranges, [optionally VB, NN, JJ, RB]
        :rtype: object
        """
        data = {
            'userKey': user_key,
            'text': input_text,
            'lang': 'en',
            'wikiDataClasses': True,
            'partsOfSpeech': include_pos_tags
        }
        headers = {'Content-type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}
        result = requests.post('http://www.wikifier.org/annotate-article', data, headers=headers).json()
        return result['annotations']
