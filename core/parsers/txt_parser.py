from difflib import SequenceMatcher

from nltk import (RegexpParser)
from nltk.corpus import (framenet as fn, stopwords)
from nltk.stem import WordNetLemmatizer
import re
from core.parsers import common


class TextParser:
    @staticmethod
    def calculate_similarity(a, b) -> float:
        return SequenceMatcher(None, a, b).ratio()

    @staticmethod
    def get_frames(input_phrase: str, verbose=False, search_entities: bool = False) -> set:
        sanitized_phrase = common.sanitize(input_phrase, preserve_entities=search_entities)
        print('# frame query-> %s' % re.escape(sanitized_phrase))
        pos_tagged_tokens = common.pos_tag(sanitized_phrase, wordnet_pos=True, ignored_words=['ENTITY'])
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

            # Log the results
            if verbose:
                print('{0!s:-<30} |{1}'.format(token, "".join(
                    '{:-<60}|'.format(x) for x in set(('%s-==>-%s' % (lu.name, lu.frame.name) for lu in lex_units)))))

            # Get frame names from matched LUs and add to results
            for lexUnit in lex_units:
                n = lexUnit.frame.name
                results[n] = dict(results).get(n, 0) + 1

        result = results.keys()
        print(result, end='\n..........\n')
        return set(result)

    @staticmethod
    def parametrize_text(input_text: str) -> next:
        """
    Break given text into sentences, extract phrases from it, and return a 2D list with lists for each sentence
        :param input_text: text in descriptive format
        :return: list of lists containing phrases for each sentence
        """
        input_sentences = common.sent_tokenize(input_text)
        for sentence in input_sentences:
            input_tokens = common.word_tokenize(sentence)
            pos_tagged_tokens = tuple(common.pos_tag(' '.join(input_tokens)))

            # Extract phrases according to english grammar
            grammar = '''
                # Adjective Chunks
                ADJ: {(<RB>?<JJ><CC>?<RB>?<JJ>?)+}
                
                # Entity Chunks
                ENT: {(<ADJ>*<NN.*|FW>+<IN>)?<ADJ>*<NN.*>+|<ADJ>*<FW>+|<ADJ|NN><VBG>+<NN.*>?}
                
                # Preposition Chunks
                PP:  {(<DT>|<CD>(<CC>?<CD|JJR>)?)<VB.*>?}
                
                # Noun-phrase Chunks
                NP: {<PP>*(<CC>?<ENT>)+}
                
                # Rest should be considered as a Verb-Phrase Chunk
                VP: {<.*>+}
                    }<NP>+{
            '''
            # TODO - Acronyms should be separately tagged with the Entity whenever they are found within brackets

            cp = RegexpParser(grammar)
            try:
                parse_tree = cp.parse(pos_tagged_tokens)
            except Exception:
                print(Exception)
                input(pos_tagged_tokens)

            # Tag the relevant entities from a parse tree and generate a parametrized sentence
            parametrized_sentence = common.generate_parametrized_sent(parse_tree)
            sentence_entities = common.entities_from_parametrized_sent(parametrized_sentence)
            yield parametrized_sentence, {entity: 0 for entity in sentence_entities}
