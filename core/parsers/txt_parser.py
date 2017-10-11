import re
from collections import Generator, Iterator
from difflib import SequenceMatcher

from nltk import (RegexpParser, Tree)
from nltk.corpus import (framenet as fn, stopwords)
from nltk.stem import WordNetLemmatizer

from core.parsers import nlp

GRAMMAR = '''           
# Adjectives (Composite)
CA: { <JJR><VB.*>|<RB>?<JJ> }

# Adjectives
AJ: { <CA>(<CC>?<CA>)* }

# Entities
EN: {<AJ>?<NN.*>+}
{<AJ>?<FW>+}
{<AJ|NN><VBG>+<NN.*>?}

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
    def get_frames(pos_tags: Generator) -> set:

        results = set()

        # iterate through each token, and create a dict of token -> words
        search_words = {}
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
            search_word = re.escape(search_word)
            # update search_words dict
            search_words[pos] = search_words.get(pos, []) + [search_word]

        # for each pos tag, query frame-net database and return results
        for pos in dict.keys(search_words):
            words = [x for x in set(search_words[pos])]
            lex_units = fn.lus(r'(?i)(^|\s)%s(\s.+)?\.%s' % ('|'.join(words), pos))
            # If lex units matched, add them to results
            results.update((lexUnit.frame.name for lexUnit in lex_units))

        print('Frames: %d' % len(results))
        return results

    @staticmethod
    def generate_parse_tree(pos_tags: Iterator):
        return PARSER.parse(Tree('S', (Tree(pos, [t]) for t, pos in pos_tags)))

    @staticmethod
    def extract_normalized_entities(pos_tags: Generator) -> set:
        try:
            # extract set of normalized entities and return them
            return nlp.extract_normalized_entities(TextParser.generate_parse_tree(pos_tags))
        except Exception as e:
            input(e.args)
