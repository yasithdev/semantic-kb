from core.parsers import (MessageParser as _MessageParser, TextParser as _TextParser, common)

SENT_GROUP_THRESHOLD = 3

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

    @staticmethod
    def __merge_nearby_sentence_ids(s: set) -> next:
        # sort the matching ids
        s = sorted(s)
        # logic
        if len(s) > 1:
            for i, e in enumerate(s):
                yield e
                if i + 1 < len(s) and s[i + 1] - e < SENT_GROUP_THRESHOLD:
                    for x in range(s[i] + 1, s[i + 1]):
                        yield x
        elif len(s) == 1:
            e = s[0]
            for x in range(e, e + SENT_GROUP_THRESHOLD):
                yield x

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
            for parametrized_sentence, entity_normalization in self.txt_parser.parametrize_text(sentence):
                normalized_entities = dict.values(entity_normalization)
                frames = self.txt_parser.get_frames(parametrized_sentence)
                # query matching sentences from database
                matching_sentence_ids = self.api.query_sentence_ids(normalized_entities, frames)
                sentence_ids = list(self.__merge_nearby_sentence_ids(matching_sentence_ids))
                input('# Sentences: %d' % len(sentence_ids))
                answers_with_params = self.api.get_sentences_by_id(sentence_ids)
                # check whether any answers returned
                any_answers = False
                for answer_with_param, heading_hierarchy in answers_with_params:
                    input(heading_hierarchy)
                    if not any_answers:
                        any_answers = True
                    yield common.sanitize(answer_with_param, preserve_entities=True)
                # if no answers returned at this point, return the default feedback
                if not any_answers:
                    yield default_fallback
