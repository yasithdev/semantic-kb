import re
from difflib import SequenceMatcher

from core.parsers import (MessageParser as _MessageParser, TextParser as _TextParser, nlp)


def get_reference_url(h_id: int) -> str:
    # Get the first occurring page link when traversing up the headings
    return '/display/%s' % h_id


class MessageEngine:
    MAX_SENT_PER_GRP = 5
    MAX_GRP_PER_ANS = 100
    ACCEPT_RATIO = 0.75
    RE_ALPHANUMERIC = re.compile(r'[^A-Za-z0-9]')
    DEFAULT_FEEDBACK = "Sorry, I don't know the answer for that."

    def __init__(self, api, frame_dict) -> None:
        super().__init__()
        self.msg_parser = _MessageParser()
        self.frame_dict = frame_dict
        self.api = api

    @staticmethod
    def __merge_adjacent_sent_ids(s: set, first: int, last: int) -> next:
        # sort the sentence ids
        s = sorted(s)
        # logic
        for i, e in enumerate(s):
            # If starting sentence is close to first sentence, yield the first sentences too
            if i == 0 and MessageEngine.MAX_SENT_PER_GRP > (e - first) > 0:
                yield from range(first, e)
            yield e
            # yield up to MAX_SENT_PER_GRP sentences after current sentence.
            if i + 1 < len(s) and s[i + 1] - e <= MessageEngine.MAX_SENT_PER_GRP:
                yield from range(e + 1, s[i + 1])
            else:
                yield from range(e + 1, min([e + MessageEngine.MAX_SENT_PER_GRP, last + 1]))

    @staticmethod
    def __extract_heading_data(headings: list, frame_dict: dict) -> next:
        # assign headings as a 2D list of entities extracted from headings
        for _heading in headings:
            # assuming only one sentence
            # parametrized heading, normalized entity dictionary
            _entities = set([])
            _frames = set([])
            for pos_tags in _TextParser.generate_pos_tag_sets(_heading):
                pos_tags = list(pos_tags)
                _entities.update(_TextParser.extract_entities(pos_tags))
                _frames.update(_TextParser.get_frames(pos_tags, frame_dict))
            # add entities and content length to heading_entities as LIFO
            _content_length = len(MessageEngine.RE_ALPHANUMERIC.sub('', _heading))
            yield (_heading, _content_length, _entities, _frames)

    @staticmethod
    def __get_heading_score(heading_string: str, q_entities: set, q_frames: set, frame_dict: dict) -> float:
        _score = 0
        # edge cases
        if len(q_entities) == 0:
            return _score
        # get the heading entities and verbs and print it
        _heading_data = MessageEngine.__extract_heading_data(heading_string.split(' > ')[::-1], frame_dict)
        # calculate entity matching score for entities in each heading
        for h_index, (heading, h_length, h_entities, h_frames) in enumerate(_heading_data):
            # edge cases
            if len(h_entities) == 0:
                continue
            # match entities and frames of current heading against question entities and frames
            q_frame_hits = len(q_frames.intersection(h_frames))
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
            _entity_hit_ratio = (q_entity_hit_ratio / q_entity_hits) if q_entity_hits > 0 else 0
            # ratio between [#of common frame count] and [#of question frames]
            _frame_hit_ratio = (q_frame_hits / len(q_frames)) if len(q_frames) > 0 else 0
            # raw match score for entities using SequenceMatcher
            _coherence = sum(SequenceMatcher(a=heading_string, b=e).ratio() for e in h_entities)
            # when going to parent headings, dept_weight decreases in square proportion
            _depth_weight = 1 / ((h_index + 1) ** 2)
            # calculate a score for current heading and add to total score
            _weighted_score = _entity_hit_ratio * (1 + _frame_hit_ratio) * _coherence * _depth_weight
            # add weighted score to total score
            _score += _weighted_score
        return _score * 100

    @staticmethod
    def __expand_entities(src_entities: set) -> dict:
        return {x: list(nlp.get_ngrams(x)) for x in src_entities}

    def process_and_answer(self, input_q: str) -> next:
        """
    Extract the semantic meaning of a question, and produce a valid list of outputs with a relevance score
        :param input_q: input question
        :return: output answer
        :rtype: next
        """
        # if no results come up, return this

        # generate parse trees from input text
        for pos_tags in _TextParser.generate_pos_tag_sets(input_q.strip('?.,:\n')):
            print(pos_tags)
            # get entities frames, and question score from sentence
            q_entities = _TextParser.extract_entities(pos_tags)
            q_frames = _TextParser.get_frames(pos_tags, self.frame_dict)
            q_entities_enhanced = MessageEngine.__expand_entities(q_entities)
            # q_score = self.msg_parser.calculate_score(parsed_string)

            # query for matches in database
            print(q_entities_enhanced)
            grouped_sent_id_matches = self.api.query_sentence_ids(q_entities_enhanced, q_frames)

            # if no matches found, return the default fallback
            if len(grouped_sent_id_matches) == 0:
                yield (None, '', 0, MessageEngine.DEFAULT_FEEDBACK)

            else:
                # group sets of sentences under headings, and sort by descending order of heading score
                scored_matches = []
                print('Rating Answers...')
                heading_info = self.api.get_heading_info_by_ids(grouped_sent_id_matches.keys())
                for h_id in grouped_sent_id_matches:
                    sent_ids = grouped_sent_id_matches[h_id]
                    h_string, min_id, max_id = heading_info[h_id]
                    match = [
                        h_id,
                        h_string,
                        self.__get_heading_score(h_string, q_entities, q_frames, self.frame_dict),
                        self.__merge_adjacent_sent_ids(sent_ids, min_id, max_id)
                    ]
                    scored_matches += [match]
                print('Rating Completed!')
                scored_matches.sort(key=lambda item: item[2], reverse=True)
                # Merge nearby sentences and yield merged_matches
                for (h_id, heading, h_score, s_ids) in scored_matches[:MessageEngine.MAX_GRP_PER_ANS]:
                    answers = [
                        _TextParser.extract_sentence(pos_tags, preserve_entities=True)
                        for index, (sent_id, pos_tags) in enumerate(self.api.get_sentences_by_id(s_ids))
                        if index < MessageEngine.MAX_SENT_PER_GRP
                    ]
                    yield (heading, get_reference_url(h_id), h_score, ' '.join(answers))
