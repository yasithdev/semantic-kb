import re
from difflib import SequenceMatcher

from nltk import (RegexpParser, Tree)
from nltk.corpus import (framenet as fn, stopwords)
from nltk.stem import WordNetLemmatizer

from core.parsers import common

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


class TextParser:
    @staticmethod
    def calculate_similarity(a, b) -> float:
        return SequenceMatcher(None, a, b).ratio()

    @staticmethod
    def get_frames(parsed_string: str, verbose=False, search_entities: bool = False) -> set:
        sentence = common.extract_sentence(parsed_string, preserve_entities=search_entities)
        print('# frame query-> %s' % re.escape(sentence))
        pos_tagged_tokens = common.pos_tag(sentence, wordnet_pos=True, ignored_words=['ENTITY'])
        lem = WordNetLemmatizer()
        results = {}
        for token in pos_tagged_tokens:
            # Lemmatize token
            if token[1] == '':
                lemma = token[0].lower()
            else:
                lemma = lem.lemmatize(token[0].lower(), token[1])

            # If lemma is a stop-word, use the original token instead
            if lemma in stopwords.words('english'):
                lemma = token[0].lower()
            # If the token is also a stop-word, ignore it
            if lemma in stopwords.words('english'):
                print('IGNORED -> %s' % lemma)
                continue

            # If lemma is a small string, do not check for it since it may be a punctuation mark, etc
            if len(lemma) < 2:
                continue

            # Get LUs matching lemma
            if verbose:
                print('{0!s:-<25}'.format(token))

            lex_units = fn.lus(r'(?i)(\A|(?<=\s))(%s)(\s.*)?\.(%s).*' % (re.escape(lemma), token[1]))

            # For lemmas that do not return lexical unit matches
            if len(lex_units) == 0:
                if token[1] in ['v', 'a'] and lemma not in ['is', 'are']:
                    results[lemma] = dict(results).get(lemma, 0) + 1
                continue

            # Get frame names from matched LUs and add to results
            for lexUnit in lex_units:
                n = lexUnit.frame.name
                results[n] = dict(results).get(n, 0) + 1

        result = results.keys()
        print(result, end='\n..........\n')
        return set(result)

    @staticmethod
    def get_parsed_strings(input_string: str) -> next:
        """
    Break given string into sentences, and return its pos-tagged strings
        :rtype: Generator
        """
        input_sentences = common.sent_tokenize(input_string)
        for sentence in input_sentences:
            pos_tags = [Tree(p, list([t])) for t,p in common.pos_tag(common.generate_pos_taggable_string(sentence))]
            pos_tagged_string = str(Tree('S', pos_tags))
            try:
                tree = Tree.fromstring(pos_tagged_string)
                tree = PARSER.parse(tree)
                yield str(tree)
            except ValueError as e:
                print(e)
                print(sentence)
                input(pos_tags)

    @staticmethod
    def extract_normalized_entities(parsed_string: str) -> set:
        try:
            # extract set of normalized entities and return them
            tree = Tree.fromstring(parsed_string)
            return common.extract_normalized_entities(tree)
        except Exception as e:
            input(e.args)
