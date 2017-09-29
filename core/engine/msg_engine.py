import math
from collections import Iterable
from difflib import SequenceMatcher

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

        def calculate_heading_score(heading_string: str, q_entities: Iterable) -> float:
            # TODO Use Dulanjana's evaluation algorithm to evaluate this
            headings = []
            # assign headings as a 2D list of entities extracted from headings
            for h in heading_string.split(' > '):
                h_ent = []
                for p_h, e in self.txt_parser.parametrize_text(h):
                    h_ent.extend(dict.values(e))
                headings += [h_ent]
            # reverse the heading items to iterate bottom-to-ROOT
            headings.reverse()
            # calculate entity matching score for heading
            sc = 0
            for i, h in enumerate(headings):
                t = 0
                for e in h:
                    for x in q_entities:
                        t += SequenceMatcher(a=e, b=x).ratio() / math.pow(i + 1, 2)
                t /= len(h)
                sc += t
            return sc

        # get a list of tuples in the form (sentence, tokens, score) for the input message content
        for sentence, tokens, score in self.msg_parser.sent_tokenize_pos_tag_and_rate_msg(input_msg):
            # get the parametrized sentences, dictionary of entities, and its frames
            for parametrized_sentence, entity_normalization in self.txt_parser.parametrize_text(sentence):
                normalized_entities = dict.values(entity_normalization)
                frames = self.txt_parser.get_frames(parametrized_sentence)
                # query matching sentences from database
                matching_sentence_ids = self.api.query_sentence_ids(normalized_entities, frames)
                grouped_sentence_ids = self.api.group_sentences_by_heading(matching_sentence_ids)



                for heading, sentence_ids in grouped_sentence_ids:
                    heading_score = calculate_heading_score(heading, normalized_entities)
                    if heading_score < 0.8:
                        continue
                    print('\033[1m' + heading + '\033[0m' + '\n' + str(sentence_ids))
                    print('Score: %f [%s]\n' % (heading_score, 'ACCEPTED' if heading_score > 0.8 else 'REJECTED'))

                sentence_ids = list(self.__merge_nearby_sentence_ids(matching_sentence_ids))
                input('# Sentences: %d' % len(sentence_ids))
                answers_with_params = self.api.get_sentences_by_id(sentence_ids)
                # check whether any answers returned
                any_answers = False
                for sentence_id, answer_with_param, heading_hierarchy in answers_with_params:
                    print('\033[1m' + heading_hierarchy + '\033[0m')
                    print(str((sentence_id, answer_with_param)) + '\n')
                    if not any_answers:
                        any_answers = True
                    yield common.sanitize(answer_with_param, preserve_entities=True)
                # if no answers returned at this point, return the default feedback
                if not any_answers:
                    yield default_fallback
