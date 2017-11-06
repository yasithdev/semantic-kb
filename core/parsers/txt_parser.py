import re
from collections import Iterable
from difflib import SequenceMatcher

from nltk import (RegexpParser, Tree, breadth_first)
from nltk.corpus import (framenet as fn, stopwords)
from nltk.stem import WordNetLemmatizer

from core.parsers import nlp

GRAMMAR = '''           
# Adjectives (Composite)
CA: { <JJR><VB.*>|<RB>?<JJ> }

# Adjectives
AJ: { <CA>(<CC>?<CA>)* }

# Entities
EN: {<AJ>?<NN.*|FW>+}

# Noun-phrases
NP: {<DT>?<CC>?(<CC><CD>)*<EN>(<CC>?<EN>)*}

# Rest should be considered as a Verb-Phrase Chunk
VP: {<.*>+}
}<NP>+{
'''
PARSER = RegexpParser(GRAMMAR)
LEMMATIZER = WordNetLemmatizer()
STOPWORDS = stopwords.words('english')


class TextParser:
    @staticmethod
    def calculate_similarity(a, b) -> float:
        return SequenceMatcher(None, a, b).ratio()

    @staticmethod
    def generate_pos_tag_sets(input_string: str) -> next:
        """
    Break given string into sentences, and return their pos-tagged lists.\n
    **REQUIRES AN ACTIVE POS TAGGER TO BE RUNNING!!**
        :param input_string: input string. may contain one or more sentences
        """
        return (list(nlp.pos_tag(sentence)) for sentence in nlp.sent_tokenize(input_string))

    @staticmethod
    def get_frames(pos_tags: Iterable, frame_cache: dict, verbose: bool = False) -> set:
        results = set()

        # iterate through each token, and create a dict of token -> words
        for token, pos in pos_tags:

            search_word = token.lower()

            # Ignore single-letter words and stopwords
            if pos[0] == ['N'] or len(search_word) < 2 or search_word in STOPWORDS:
                continue

            # Get wordnet-pos. Ignore words with no wordnet pos tag
            pos = nlp.get_wordnet_pos(pos)
            if pos == '':
                # add search_word to results set if eligible
                normalized_token = nlp.normalize_text(search_word, lemmatize=False, ignore_num=True)
                if len(normalized_token) > 1:
                    results.add(normalized_token)
                continue

            # If lemma is not a stop-word, use that instead of lowercase token
            lemma = LEMMATIZER.lemmatize(search_word, pos)
            if lemma not in STOPWORDS:
                search_word = lemma

            # Get lexical units matching the search word and pos
            search_word = nlp.normalize_text(search_word, lemmatize=False, ignore_num=True).replace('.', '')

            # Load frames for missing tokens from FrameNet if it does not exist in cache
            key = '%s__%s' % (search_word, pos)
            if key not in frame_cache:
                frame_cache[key] = sorted(
                    set(lu.frame.name for lu in fn.lus(r'(?i)(^|\s)(%s)(\s.+)?\.%s' % (search_word, pos))))

            # add the frames from current key to the results set
            results.update(frame_cache[key])
        if verbose:
            print('Frames: %d' % len(results))
        else:
            print('.', end='', flush=True)
        return results

    @staticmethod
    def generate_parse_tree(pos_tags: list):
        return PARSER.parse(Tree('S', (Tree(pos, [t]) for t, pos in pos_tags)))

    @staticmethod
    def extract_entities(pos_tags: list) -> set:
        """
    Accepts a **POS Tags list**, extract the entities, and return them in normalized form
    of the entities in a dict
        :param pos_tags: list of pos tags
        :return: set of normalized entities for the tree, and set of important dependencies
        :rtype: Set
        """
        normalized_entities = set()
        for node in breadth_first(TextParser.generate_parse_tree(pos_tags), maxdepth=1):
            # If noun phrase or verb phrase found
            # NOTE: this node is traversed BEFORE traversing to ENT node, which is a leaf node if a VP or NP
            # i.e. the ENT nodes are traversed after traversing all VPs and NPs
            if node.label() in ['VP', 'NP']:
                # traverse each entity and parametrize the phrase
                for leaf in breadth_first(node, maxdepth=1):
                    # continue if leaf is not an entity leaf
                    if not isinstance(leaf, Tree):
                        continue
                    elif leaf.label() == 'EN':
                        # Generate entity from tree leaves, and add to normalized_entities
                        for entity in nlp.yield_valid_entities(leaf.leaves()):
                            entity = nlp.normalize_text(entity)
                            if entity != '':
                                normalized_entities.add(entity)
        return normalized_entities

    @staticmethod
    def extract_sentence(pos_tags: list, preserve_entities=False) -> str:
        """
    Recreate and return original sentence from parse_tree. If preserve_entities set to False (default), entities
    are replaced by a placeholder to simplify sentence
        :param pos_tags: List/Generator of POS Tags
        :param preserve_entities: whether to preserve entities, or replace them with a placeholder
        :return: sentence
        """
        # concatenate all leaves and create a sentence if entities are preserved
        if preserve_entities:
            entity_sanitized_sent = ' '.join(token for token, pos in pos_tags)

        # if not, replace each entity with a placeholder and create a sentence
        else:
            entity_sanitized_sent = ''
            parse_tree = PARSER.parse(TextParser.generate_parse_tree(pos_tags))
            # declare temporary variable
            for node in breadth_first(parse_tree, maxdepth=1):
                # If noun phrase or verb phrase found
                # NOTE: this node is traversed BEFORE traversing to ENT node, which is a leaf node if a VP or NP
                # i.e. the ENT nodes are traversed after traversing all VPs and NPs
                if node.label() in ['VP', 'NP']:
                    phrase = ' '.join(node.leaves())
                    # traverse each entity and parametrize the phrase
                    for leaf in breadth_first(node, maxdepth=1):
                        # continue if leaf is not an entity leaf
                        if not isinstance(leaf, Tree) or leaf.label() != 'EN':
                            continue
                        else:
                            entity = ' '.join(leaf.leaves())
                            phrase = phrase.replace(entity, nlp.ENTITY_PLACEHOLDER)
                    entity_sanitized_sent += ' ' + phrase

        entity_sanitized_sent = entity_sanitized_sent.strip()

        # sanitize bracket tags
        if preserve_entities:
            if len(nlp.RE_BRACKETS.findall(entity_sanitized_sent)) > 0:
                # replace bracket tags with correct brackets
                entity_sanitized_sent = re.sub(r'\s*-LCB-\s*', ' {', entity_sanitized_sent).strip()
                entity_sanitized_sent = re.sub(r'\s*-RCB-\s*', '} ', entity_sanitized_sent).strip()
                entity_sanitized_sent = re.sub(r'\s*-LSB-\s*', ' [', entity_sanitized_sent).strip()
                entity_sanitized_sent = re.sub(r'\s*-RSB-\s*', '] ', entity_sanitized_sent).strip()
                entity_sanitized_sent = re.sub(r'\s*-LRB-\s*', ' (', entity_sanitized_sent).strip()
                entity_sanitized_sent = re.sub(r'\s*-RRB-\s*', ') ', entity_sanitized_sent).strip()
        else:
            # remove any bracket tags
            entity_sanitized_sent = nlp.RE_BRACKETS.sub(' ', entity_sanitized_sent).strip()

        # if ENTITY placeholders are used, merge neighbouring placeholders
        if not preserve_entities:
            entity_sanitized_sent = nlp.RE_ENTITY_SUB_MULTIPLE.sub(nlp.ENTITY_PLACEHOLDER,
                                                                   entity_sanitized_sent).strip()

        # add a period if sentence does not end with a punctuation
        if entity_sanitized_sent[-1] not in '!;:.':
            entity_sanitized_sent += '.'

        # return sanitized sentence
        return entity_sanitized_sent
