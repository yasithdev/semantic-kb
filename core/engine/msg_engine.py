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

    @staticmethod
    def __merge_nearby_sentence_ids(sent_ids: set) -> next:
        # sort the matching ids
        sent_ids = list(sent_ids)
        sent_ids.sort()
        # define a threshold
        __threshold__ = 3
        # logic
        if len(sent_ids) > 1:
            for i in range(len(sent_ids)):
                yield sent_ids[i]
                if i+1 < len(sent_ids):
                    if sent_ids[i+1] - sent_ids[i] < __threshold__:
                        for x in range(sent_ids[i] + 1, sent_ids[i+1]):
                            yield x
        elif len(sent_ids) == 1:
            for x in range(sent_ids[0], sent_ids[0] + __threshold__):
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
            parametrized_sentence, entity_dict = list(self.txt_parser.parametrize_sentence(sentence))[0]
            frames = self.txt_parser.get_frames(parametrized_sentence)
            # query matching sentences from database
            entities = set(entity_dict.keys())
            matching_sentence_ids = self.api.query_sentence_ids(entities, frames)
            sentence_ids = list(self.__merge_nearby_sentence_ids(matching_sentence_ids))
            answers_with_params = self.api.get_sentences_by_id(sentence_ids)
            # check whether any answers returned
            any_answers = False
            for answer_with_param in answers_with_params:
                if not any_answers:
                    any_answers = True
                yield common.sanitize(answer_with_param, preserve_entities=True)
            # if no answers returned at this point, return the default feedback
            if not any_answers:
                yield default_fallback
