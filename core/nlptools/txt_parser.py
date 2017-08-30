from nltk import RegexpParser
from nltk.corpus import (framenet as fn, stopwords)
from nltk.stem import WordNetLemmatizer

from core.nlptools import common


class TextParser:
    @staticmethod
    def __get_frames(input_phrase: str, verbose=False):
        sanitized_phrase = common.sanitize(input_phrase)
        pos_tagged_tokens = common.pos_tag(sanitized_phrase, wordnet_pos=True)
        lem = WordNetLemmatizer()

        for token in pos_tagged_tokens:

            # Ignore placeholder token for entities
            if token[0] == 'ENTITY' or len(token[0]) < 2:
                continue

            # Lemmatize token
            if token[1] == '':
                lemma = token[0].lower()
            else:
                lemma = lem.lemmatize(token[0].lower(), token[1])

            # TODO convert adverbs to a root form adjective. Otherwise they are missed
            # TODO maybe this is not necessary. Will check on accuracy and implement if needed

            # If lemma is a stopword, use the original token instead
            if lemma in stopwords.words('english'):
                lemma = token[0].lower()

            # Get LUs matching lemma
            if verbose:
                print('{0!s:-<25}'.format(token))

            lex_units = fn.lus(r'(?i)(\A|(?<=\s))(%s)(\s.*)?\.(%s).*' % (lemma, token[1]))

            # For lemmas that do not return lexical unit matches
            if len(lex_units) == 0:
                if token[1] in ['v', 'a'] and lemma not in ['is', 'are']:
                    yield lemma
                continue

            # Log the results
            if verbose:
                print('{0!s:-<30} |{1}'.format(token, "".join(
                    '{:-<60}|'.format(x) for x in set(('%s-==>-%s' % (lu.name, lu.frame.name) for lu in lex_units)))))

            # Get frame names from matched LUs and add to results
            for lexUnit in lex_units:
                yield lexUnit.frame.name
        print('.', end='', flush=True)

    @staticmethod
    def get_frames(input_phrase: str, verbose=False) -> set:
        return set(TextParser.__get_frames(input_phrase, verbose))

    @staticmethod
    def parametrize_text(input_text: str) -> tuple:
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
                ENT: {<ADJ>*<NN.*>+|<ADJ>*<FW>+|<ADJ|NN><VBG>+<NN.*>?}
                
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
            parse_tree = cp.parse(pos_tagged_tokens)

            # Extract Relevant entities from a parse tree and generate a parametrized sentence
            yield common.process_sentence(parse_tree)
