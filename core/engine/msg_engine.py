import math
import re
from difflib import SequenceMatcher

from core.parsers import (MessageParser as _MessageParser, TextParser as _TextParser, common)

SENT_GROUP_THRESHOLD = 3
ACCEPTANCE_RATIO = 0.5
SENTENCE_THRESHOLD = 7


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


    def _extract_heading_entities(self, headings: list) -> list:
        # assign headings as a 2D list of entities extracted from headings
        _h_ent = []
        re_alnum = re.compile(r'[^A-Za-z0-9]')
        for _heading in headings:
            _entities = []
            # parametrized heading, normalized entity dictionary
            for ph, e_dict in self.txt_parser.parametrize_text(_heading):
                _entities.extend(dict.values(e_dict))
            # add entities and content length to heading_entities as LIFO
            _content_length = len(re_alnum.sub('', _heading))
            _h_ent = [(_entities, _content_length)] + _h_ent
        return _h_ent


    def _calculate_score(self, heading_string: str, q_entities: set) -> float:
        _score = float(0)
        # get the heading entities and print it
        _heading_entities = self._extract_heading_entities(heading_string.split(' > '))
        # calculate entity matching score for entities in each heading
        for h_index, (h_entities, h_length) in enumerate(_heading_entities):
            # match entities of current heading against question entities
            q_entity_hits = int(0)
            # score for the current heading
            _h_score = float(0)
            for q_entity in q_entities:
                _q_e_found = False
                for h_entity in h_entities:
                    # calculate the match ratio
                    _ratio = SequenceMatcher(a=h_entity, b=q_entity).ratio()
                    if _ratio >= ACCEPTANCE_RATIO:
                        # if ratio is close to 1, consider it as a positive match, and count it for score
                        _h_score += _ratio
                        _q_e_found = True
                # if entity was found in headings, mark that as a hit
                if _q_e_found:
                    q_entity_hits += 1

            # ratio between [#of q_entities found in current heading] and the [total #of q_entities]
            _hit_ratio = float(q_entity_hits) / len(q_entities)
            # when going to parent headings, dept_weight decreases in square proportion
            _depth_weight = float(1) / (h_index + 1)
            # ratio between the [length of all entities combined] and the [length of heading]
            _coherence_factor = float(sum(len(q_e) for q_e in q_entities)) / h_length
            # calculate a score for current heading and add to total score
            _weighted_score = _h_score * _hit_ratio * _depth_weight * _coherence_factor

            # add weighted score to total score
            _score += _weighted_score
        return _score


    def process_and_answer(self, input_q: str) -> list:
        """
    Extract the semantic meaning of a question, and produce a valid list of outputs with a relevance score
        :param input_q: input question
        :return: output answer
        :rtype: str
        """
        # if no results come up, return this
        default_fallback_heading = "Answer Not Found"
        default_fallback = 'Sorry, I do not know the answer for that'

        # get a list of tuples in the form (sentence, tokens, score) for the input message content
        for q_sentence, tokens, q_score in self.msg_parser.sent_tokenize_pos_tag_and_calculate_score(input_q):

            # get the parametrized sentences, dictionary of entities, and its frames
            for parametrized_q_sentence, q_entity_dict in self.txt_parser.parametrize_text(q_sentence):

                # get entities and frames from sentence
                q_entities = set(dict.values(q_entity_dict))
                q_frames = self.txt_parser.get_frames(parametrized_q_sentence)

                # query matching sentences from database
                sent_id_matches = self.api.query_sentence_ids(q_entities, q_frames)

                # group sets of sentences under headings, and sort by descending order of heading score
                scored_matches = sorted([
                    (x[0],self._calculate_score(x[0], q_entities), x[1])
                    for x in self.api.group_sentences_by_heading(sent_id_matches)
                ], key= lambda item: item[1], reverse=True)

                # Condition 1 - No matches returned. Return default fallback
                if len(scored_matches) == 0:
                    return [(default_fallback_heading, default_fallback)]

                # Condition 2 - Getting most prominent matches, and getting merge nearby sentences as well
                # Limit the number of sentences in the answer to SENTENCE_THRESHOLD
                prominent_matches = scored_matches[:5] if len(scored_matches) >= 5 else scored_matches

                # Merge nearby sentences and create a merged_matches list from records in prominent_matches
                merged_matches = []
                for index, record in enumerate(prominent_matches):
                    heading, h_score, s_ids = record
                    s_ids = list(self.__merge_nearby_sentence_ids(s_ids))
                    merged_matches += [(heading, s_ids)]

                # Return answers grouped under each heading. Also print them for debugging purposes
                output = []
                for heading, sentence_ids in merged_matches:
                    sentences = [
                        common.sanitize(sentence, preserve_entities=True)
                        for sent_id, sentence in self.api.get_sentences_by_id(sentence_ids)
                    ]
                    output += [(heading, str('. '.join(sentences) + '.'))]
                return output
