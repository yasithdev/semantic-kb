import re
from difflib import SequenceMatcher

from core.parsers import (MessageParser as _MessageParser, TextParser as _TextParser)


def get_reference_url(h_id: int) -> str:
    # Get the first occurring page link when traversing up the headings
    return '/display/%s' % h_id


class MessageEngine:
    MAX_SENT_PER_GRP = 5
    MAX_GRP_PER_ANS = 10
    ACCEPT_RATIO = 0.75
    RE_ALPHANUMERIC = re.compile(r'[^A-Za-z0-9]')
    DEFAULT_FEEDBACK = "Sorry, I don't know the answer for that."

    def __init__(self, api) -> None:
        super().__init__()
        self.msg_parser = _MessageParser()
        self.api = api

    @staticmethod
    def __merge_adjacent_sent_ids(s: set, first: int, last: int) -> next:
        # sort the sentence ids
        s = sorted(s)
        print(s)
        # logic
        for i, e in enumerate(s):
            yield e
            # yield up to MAX_SENT_PER_GRP sentences after current sentence.
            if i + 1 < len(s) and s[i + 1] - e <= MessageEngine.MAX_SENT_PER_GRP:
                yield from range(e + 1, s[i + 1])
            else:
                yield from range(e + 1, min([e + MessageEngine.MAX_SENT_PER_GRP, last + 1]))

    @staticmethod
    def _extract_heading_entities(headings: list) -> next:
        # assign headings as a 2D list of entities extracted from headings
        for _heading in headings:
            # assuming only one sentence
            # parametrized heading, normalized entity dictionary
            _entities = set()
            _frames = set()
            for pos_tags in _TextParser.generate_pos_tag_sets(_heading):
                pos_tags = list(pos_tags)
                for normalized_entities in _TextParser.extract_normalized_entities(pos_tags):
                    _entities = _entities.union([normalized_entities])
            # add entities and content length to heading_entities as LIFO
            _content_length = len(MessageEngine.RE_ALPHANUMERIC.sub('', _heading))
            yield (_heading, _content_length, _entities)

    def __get_heading_score(self, heading_string: str, q_entities: set, q_frames: set) -> float:
        _score = 0
        # get the heading entities and print it
        _heading_entities = self._extract_heading_entities(heading_string.split(' > ')[::-1])
        # calculate entity matching score for entities in each heading
        for h_index, (heading, h_length, h_entities) in enumerate(_heading_entities):
            # match entities of current heading against question entities
            q_entity_hit_ratio = 0
            q_entity_hits = 0
            # logic
            for q_entity in q_entities:
                # becomes true if question entity found within heading entities
                # iterate through heading entities for each question entity
                for h_entity in h_entities:
                    # calculate the match ratio
                    _ratio = SequenceMatcher(a=h_entity, b=q_entity).ratio()
                    # if ratio is greater than the accept ratio, increment q_entity_hits and q_entity_hit_ratio
                    if _ratio >= MessageEngine.ACCEPT_RATIO:
                        q_entity_hit_ratio += _ratio
                        q_entity_hits += 1

            # ratio between [#of q_entities found in current heading] and the [total #of q_entities]
            _hit_ratio = (q_entity_hit_ratio / q_entity_hits) if q_entity_hits > 0 else 0
            # ratio between the [length of all entities combined] and the [length of heading]
            _coherence_factor = sum(len(e) for e in q_entities) / h_length
            # when going to parent headings, dept_weight decreases in square proportion
            _depth_weight = 1 / ((h_index + 1) ** 2)
            # calculate a score for current heading and add to total score
            _weighted_score = _hit_ratio * _coherence_factor * _depth_weight
            # add weighted score to total score
            _score += _weighted_score
        return _score * 100

    def process_and_answer(self, input_q: str) -> next:
        """
    Extract the semantic meaning of a question, and produce a valid list of outputs with a relevance score
        :param input_q: input question
        :return: output answer
        :rtype: next
        """
        # if no results come up, return this

        # generate parse trees from input text
        for pos_tags in _TextParser.generate_pos_tag_sets(input_q):
            # get entities frames, and question score from sentence
            q_entities = _TextParser.extract_normalized_entities(pos_tags)
            q_frames = _TextParser.get_frames(pos_tags)
            # q_score = self.msg_parser.calculate_score(parsed_string)

            # query for matches in database
            sent_id_matches = self.api.query_sentence_ids(q_entities, q_frames)

            # if no matches found, return the default fallback
            if len(sent_id_matches) == 0:
                yield (None, '', 0, MessageEngine.DEFAULT_FEEDBACK)

            else:
                # group sets of sentences under headings, and sort by descending order of heading score
                scored_matches = []
                for h_id, h_string, sentence_ids, first_id, last_id in self.api.group_sentences_by_heading(
                        sent_id_matches):
                    match = (
                        h_id,
                        h_string,
                        self.__get_heading_score(h_string, q_entities, q_frames),
                        self.__merge_adjacent_sent_ids(sentence_ids, first_id, last_id)
                    )
                    scored_matches += [match]
                scored_matches.sort(key=lambda item: item[2], reverse=True)

                # Merge nearby sentences and yield merged_matches
                for (h_id, heading, h_score, s_ids) in scored_matches[:MessageEngine.MAX_GRP_PER_ANS]:
                    answers = [
                        _TextParser.extract_sentence(pos_tags, preserve_entities=True)
                        for index, (sent_id, pos_tags) in enumerate(self.api.get_sentences_by_id(s_ids))
                        if index < MessageEngine.MAX_SENT_PER_GRP
                    ]
                    yield (heading, get_reference_url(h_id), h_score, ' '.join(answers))
