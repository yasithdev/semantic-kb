from nltk import RegexpParser
from nltk.corpus import (framenet as fn, stopwords)
from nltk.stem import WordNetLemmatizer

from core.nlptools import common


class TextParser:
    @staticmethod
    def get_frames(input_phrase: str, verbose=False):

        sanitized_phrase = common.sanitize(input_phrase)
        pos_tagged_tokens = common.pos_tag(sanitized_phrase)
        # print(pos_tagged_tokens)
        lem = WordNetLemmatizer()
        results = set()
        for token in pos_tagged_tokens:

            # Ignore placeholder token for entities
            if token[0] == 'ENT' or len(token[0]) < 2:
                continue

            # Get Wordnet POS tag
            pos = common.get_wordnet_pos(token[1])
            if pos == '':
                continue

            # Lemmatize token
            lemma = lem.lemmatize(token[0], pos)
            # TODO convert adverbs to a root form adjective. Otherwise they are missed
            # if pos == wordnet.ADV:
            #     if str(lemma).endswith('ly'):
            #         lemma = lemma[:-2]
            #         if lemma[-1] == 'i':
            #             lemma = lemma[:-1] + 'y'
            #         pos = wordnet.ADJ
            #         input(lemma)
            if lemma in stopwords.words('english'):
                lemma = token[0]

            # Get LUs matching lemma
            if verbose:
                print('{0!s:-<25}'.format(token))
            lex_units = fn.lus(r'(?i)(\A|(?<=\s))(%s)(\s.*)?\.(%s)' % (lemma, pos))
            if len(lex_units) == 0:
                results = results.union([lemma])
                continue

            # Log the results
            if verbose:
                print('{0!s:-<30} |{1}'.format(token, "".join(
                    '{:-<60}|'.format(x) for x in set(['%s-==>-%s' % (lu.name, lu.frame.name) for lu in lex_units]))))

            # Get frame names from matched LUs and add to results
            frames = set([lexUnit.frame.name for lexUnit in lex_units])
            results = results.union(frames)

        if not verbose:
            print('.')
        return list(results)

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
            pos_tagged_tokens = common.pos_tag(' '.join(input_tokens))

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
            yield next(common.process_sentence(parse_tree))
