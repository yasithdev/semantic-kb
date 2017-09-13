from core.nlptools import (MessageParser as _MessageParser, TextParser as _TextParser, common)


class MessageEngine:
    def __init__(self, api) -> None:
        super().__init__()
        self.msg_parser = _MessageParser()
        self.txt_parser = _TextParser()
        self.api = api

    @staticmethod
    def extract_entities(pos_tagged_tokens: list, n_tuple: tuple = ('N', 'P')) -> str:
        n = ['']
        n.extend([x[0] for x in pos_tagged_tokens if str(x[1]).startswith(n_tuple)])
        return " ".join(n).strip()

    def process_message(self, input_msg: str) -> next:
        """
    Extract the semantic meaning of a question, and produce a valid list of outputs with a relevance score
        :param input_msg: input question
        :return: output answer
        :rtype: str
        """
        # create structure to return the default feedback if no results come up
        default_fallback = 'Sorry. I do not know the answer for that'

        # get a list of tuples in the form (sentence, tokens, score) for the input message content
        for sentence, tokens, score in self.msg_parser.sent_tokenize_pos_tag_and_rate_msg(input_msg):
            # get the parametrized sentences, dictionary of entities, and its frames
            parametrized_sentence, entity_dict = list(self.txt_parser.parametrize_sentence(sentence))[0]
            frames = self.txt_parser.get_frames(parametrized_sentence)
            # query matching sentences from database
            entities = set(entity_dict.keys())
            answers_with_params = self.api.query_sentences(entities, frames)
            # check whether any answers returned
            if len(answers_with_params) > 0:
                for answer in answers_with_params:
                    yield common.sanitize(answer, preserve_entities=True)
            # if no answers returned at this point, return the default feedback
            else:
                yield default_fallback
