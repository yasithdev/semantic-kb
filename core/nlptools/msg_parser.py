from nltk.tag import pos_tag

from core.nlptools import common


class MessageParser:

    @staticmethod
    def parse(input_text: str):
        question = False
        wh = False
        md = False
        if '?' in input_text: question = True
        input_text = common.sanitize(input_text)
        input_sentences = common.sent_tokenize(input_text)
        for sentence in input_sentences:
            input_tokens = common.word_tokenize(sentence)
            pos_tagged_tokens = pos_tag(input_tokens)
            # Check if the tokens in a sentence belong to a question or a statement
            for token in pos_tagged_tokens:
                if token[1][0] == 'W':
                    wh = True
                elif token[1][0] == 'M':
                    md = True
            yield (sentence, pos_tagged_tokens, question or wh or md)
