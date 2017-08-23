from core.nlptools import (MessageParser as _MessageParser, TextParser as _TextParser)


class MessageEngine:
    def __init__(self, api) -> None:
        super().__init__()
        self.message_parser = _MessageParser()
        self.text_parser = _TextParser()
        self.api = api

    @staticmethod
    def extract_entities(pos_tagged_tokens: list, n_tuple: tuple = ('N', 'P')):
        n = ['']
        n.extend([x[0] for x in pos_tagged_tokens if str(x[1]).startswith(n_tuple)])
        return " ".join(n).strip()

    def process(self, input: str) -> str:
        """

        :param input:
        :return:
        :rtype: object
        """
        default_fallback = 'Sorry. I do not know the answer for that.'

        # get a list of tuples in the form (sentence_text, pos_tagged_tokens, is_question)
        parsed_sentences = list(self.message_parser.parse(input))

        for parsed_sentence in parsed_sentences:
            sentence_text = parsed_sentence[0]
            pos_tagged_tokens = parsed_sentence[1]
            is_question = parsed_sentence[2]

            nouns = self.extract_entities(pos_tagged_tokens)
            frames = self.text_parser.get_frames(sentence_text)
            print((nouns, frames))

            # TODO - Causes error if not checked. Look for alternative way
            if len(frames) == 0:
                return default_fallback

            answer = ' '.join(self.api.query_recursive(nouns, frames))

            if len(answer) == 0:
                return default_fallback
            else:
                return answer
