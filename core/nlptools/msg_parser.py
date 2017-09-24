from core.nlptools import common


class MessageParser:
    @staticmethod
    def sent_tokenize_pos_tag_and_rate_msg(input_text: str, include_entity_names: bool = True) -> next:
        """
    Get an input text, break into sentences, pos-tag the sentence, and calculate a question score indicating how likely
    the sentence is a question
        :param include_entity_names: (optional) default is True. If set to false, entities will be replaced as ENTITY
        :param input_text: input text
        :return: a generator of tuples in the format **(sentence, pos_tagged tokens, question_score)**
        """

        def get_score(wh: bool, md: bool, qmark: bool) -> float:
            return float(wh + md + qmark) / 3

        qmark_tag = False
        wh_tag = False
        md_tag = False

        if '?' in input_text: qmark_tag = True
        input_text = common.sanitize(input_text, preserve_entities=include_entity_names)
        input_sentences = common.sent_tokenize(input_text)

        for sentence in input_sentences:
            pos_tagged_tokens = common.pos_tag(sentence)
            # Check if the tokens in a sentence belong to a question or a statement
            for token in pos_tagged_tokens:
                if token[1][0] == 'W':
                    wh_tag = True
                if token[1][0] == 'M':
                    md_tag = True
            yield (str(sentence), pos_tagged_tokens, get_score(wh_tag, md_tag, qmark_tag))
