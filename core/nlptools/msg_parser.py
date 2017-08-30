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
            pos_tagged_tokens = common.pos_tag(sentence)
            pass
            # Check if the tokens in a sentence belong to a question or a statement
            for token in pos_tagged_tokens:
                if token[1][0] == 'W':
                    wh = True
                elif token[1][0] == 'M':
                    md = True
            yield (sentence, pos_tagged_tokens, question or wh or md)
