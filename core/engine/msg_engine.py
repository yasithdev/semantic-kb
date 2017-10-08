import re
from difflib import SequenceMatcher

from core.parsers import (MessageParser as _MessageParser, TextParser as _TextParser, common)


class MessageEngine:
    MAX_SENT_PER_GRP = 3
    MAX_GRP_PER_ANS = 5
    ACCEPT_RATIO = 0.75
    RE_ALPHANUMERIC = re.compile(r'[^A-Za-z0-9]')

    def __init__(self, api) -> None:
        super().__init__()
        self.msg_parser = _MessageParser()
        self.txt_parser = _TextParser()
        self.api = api

    @staticmethod
    def __merge_adjacent_sent_ids(s: set) -> next:
        # sort the matching ids
        s = sorted(s)
        # logic
        l = len(s)
        if l > 1:
            for i, e in enumerate(s):
                if i + 1 < l and s[i + 1] - e <= MessageEngine.MAX_SENT_PER_GRP:
                    yield from range(s[i], s[i + 1])
        elif l == 1:
            yield from range(s[0], s[0] + MessageEngine.MAX_SENT_PER_GRP)

    def __extract_heading_entities(self, headings: list) -> next:
        # assign headings as a 2D list of entities extracted from headings
        for _heading in headings:
            # assuming only one sentence
            # parametrized heading, normalized entity dictionary
            _entities = set()
            for parsed_string in self.txt_parser.get_parsed_strings(_heading):
                for normalized_entities in self.txt_parser.extract_normalized_entities(parsed_string):
                    _entities = _entities.union([normalized_entities])
            # add entities and content length to heading_entities as LIFO
            _content_length = len(MessageEngine.RE_ALPHANUMERIC.sub('', _heading))
            yield (_heading, _content_length, _entities)

    def __get_heading_score(self, heading_string: str, q_entities: set) -> float:
        _score = float(0)
        # get the heading entities and print it
        _heading_entities = self.__extract_heading_entities(heading_string.split(' > ')[::-1])
        # calculate entity matching score for entities in each heading
        for h_index, (heading, h_length, h_entities) in enumerate(_heading_entities):
            # match entities of current heading against question entities
            q_entity_hits = int(0)
            # score for the current heading
            _h_score = float(0)
            # logic
            for q_entity in q_entities:
                # becomes true if question entity found within heading entities
                _q_e_found = False
                # iterate through heading entities for each question entity
                for h_entity in h_entities:
                    # calculate the match ratio
                    _ratio = SequenceMatcher(a=h_entity, b=q_entity).ratio()
                    # increment heading score by the match ratio
                    _h_score += _ratio
                    # if ratio is greater than the accept ratio, increment the hits by 1
                    if _ratio >= MessageEngine.ACCEPT_RATIO:
                        if not _q_e_found:
                            # increment entity hit counter
                            q_entity_hits += 1
                            _q_e_found = True

            # ratio between [#of q_entities found in current heading] and the [total #of q_entities]
            _hit_ratio = float(q_entity_hits) / len(q_entities)
            # when going to parent headings, dept_weight decreases in square proportion
            _depth_weight = float(1) / (h_index + 1)
            # ratio between the [length of all entities combined] and the [length of heading]
            _coherence_factor = float(sum(len(e) for e in q_entities)) / h_length
            # calculate a score for current heading and add to total score
            _weighted_score = _h_score * _hit_ratio * _depth_weight * _coherence_factor
            # add weighted score to total score
            _score += _weighted_score
        return _score

    def process_and_answer(self, input_q: str) -> next:
        """
    Extract the semantic meaning of a question, and produce a valid list of outputs with a relevance score
        :param input_q: input question
        :return: output answer
        :rtype: str
        """
        # if no results come up, return this
        default_fallback = 'Sorry, I do not know the answer for that.'

        # generate parse strings from input text
        for parsed_string in self.txt_parser.get_parsed_strings(input_q):

            # get entities frames, and question score from sentence
            q_entities = self.txt_parser.extract_normalized_entities(parsed_string)
            q_frames = self.txt_parser.get_frames(parsed_string, search_entities=True)
            q_score = self.msg_parser.calculate_score(parsed_string)

            # query for matches in database
            sent_id_matches = self.api.query_sentence_ids(q_entities, q_frames)

            # if no matches found, return the default fallback
            if len(sent_id_matches) == 0:
                yield (None, 0, default_fallback)

            else:
                # group sets of sentences under headings, and sort by descending order of heading score
                scored_matches = []
                for heading_string, sentence_ids in self.api.group_sentences_by_heading(sent_id_matches):
                    match = (
                        heading_string,
                        self.__get_heading_score(heading_string, q_entities),
                        self.__merge_adjacent_sent_ids(sentence_ids)
                    )
                    scored_matches += [match]
                scored_matches.sort(key=lambda item: item[1], reverse=True)

                # Merge nearby sentences and yield merged_matches
                for (heading, h_score, s_ids) in scored_matches[:MessageEngine.MAX_GRP_PER_ANS]:
                    answers = [
                        common.extract_sentence(sentence, preserve_entities=True)
                        for sent_id, sentence in self.api.get_sentences_by_id(s_ids)
                    ]
                    yield (heading, h_score, str('. '.join(answers) + '.'))
