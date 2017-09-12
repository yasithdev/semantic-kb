from core.nlptools import common


class MessageParser:
    @staticmethod
    def calculate_q_score(input_text: str) -> list:
        """
    Get an input text, break into sentences, pos-tag the sentence, and calculate a question score indicating how likely
    the sentence is a question
        :param input_text: input text
        :return: a generator of tuples in the format **(sentence, pos_tagged tokens, question_score)**
        """
        def get_score(wh: bool, md: bool, qmark: bool):
            return 1
        qmark = False
        wh_tag = False
        md = False
        if '?' in input_text: qmark = True
        input_text = common.sanitize(input_text)
        input_sentences = common.sent_tokenize(input_text)
        for sentence in input_sentences:
            pos_tagged_tokens = common.pos_tag(sentence)
            pass
            # Check if the tokens in a sentence belong to a question or a statement
            for token in pos_tagged_tokens:
                if token[1][0] == 'W':
                    wh_tag = True
            yield (sentence, pos_tagged_tokens, qmark or wh_tag or md)
