from nltk import RegexpParser
from nltk.corpus import (framenet as fn, stopwords)
from nltk.stem import WordNetLemmatizer
from nltk.tag import pos_tag
from nltk.util import breadth_first

from core.nlptools import common


class TextParser:
    @staticmethod
    def get_frames(input_phrase: str):
        sanitized_phrase = common.sanitize(input_phrase).lower()
        pos_tagged_tokens = pos_tag(common.word_tokenize('X %s Y' % sanitized_phrase))
        lem = WordNetLemmatizer()
        results = set()
        for token in pos_tagged_tokens[1:-1]:

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
            # lex_units = fn.lus(r'(?i)(\A|(?<=\s))(%s)[sd(es)]?(\s.*)?\.(%s)' % (lemma, pos))
            lex_units = fn.lus(r'(?i)(\A|(?<=\s))(%s)(\s.*)?\.(%s)' % (lemma, pos))
            if len(lex_units) == 0:
                results = results.union([lemma])
                continue

            # Log the results
            print('{0!s:-<30} |{1}'.format(token, "".join('{:-<60}|'.format(x) for x in set(['%s-==>-%s' % (lu.name,lu.frame.name) for lu in lex_units]))))

            # Get frame names from matched LUs and add to results
            frames = set([lexUnit.frame.name for lexUnit in lex_units])
            results = results.union(frames)
        return list(results)

    @staticmethod
    def extract_phrase_sets(input_text: str) -> list:
        """
    Break given text into sentences, extract phrases from it, and return a 2D list with lists for each sentence
        :param input_text: text in descriptive format
        :return: list of lists containing phrases for each sentence
        """
        input_sentences = common.sent_tokenize(input_text)
        for sentence in input_sentences:
            input_tokens = common.word_tokenize(sentence)
            pos_tagged_tokens = pos_tag(input_tokens)

            # Extract phrases according to english grammar
            grammar = '''
                #Modifier
                    MOD:{<JJ.*|RB.*|CD|POS|PRP.*|PDT>+<CC>*<JJ.*|RB.*|CD|POS|PRP.*|PDT>*}
                #NOUN PHRASE
                    NP: {<MOD|DT>*<NN.*>+<MOD|DT|NN.*>*}
                    
                #Wh-Clause
                    WH: {<IN|PDT>*<W.*>+}
                #Preposition
                    CP:{<IN|CC|TO|EX|PRP.*|DT|MD>+}
                #VERB PHRASE
                    VP: {(<MOD>|<CP|R.*>)*<CP|V.*|WH>+(<MOD>|<CP|V.*|R.*>)*|<CP>+}
            '''

            cp = RegexpParser(grammar)
            parse_tree = cp.parse(pos_tagged_tokens)
            # parse_tree.draw()
            extracted_phrases = []

            # Extract Relevant phrases from tree
            for tree in list(breadth_first(parse_tree, maxdepth=1))[1:]:
                extracted_phrases += common.flatten_tree(tree, ['NP', 'VP'])

            # Add the phrase list as a sub-list into parsed_content
            yield extracted_phrases

    @staticmethod
    def generate_triples(phrase_set, context: str = '#'):
        init_phrase = ""
        verb_phrase = ""
        term_phrase = ""

        def get_triple():
            triple = (init_phrase.strip(), verb_phrase.strip(), term_phrase.strip())
            return triple

        def is_complete():
            return init_phrase != '' and verb_phrase != '' and term_phrase != ''

        is_init = True

        for i in range(len(phrase_set)):
            # Case of getting a verb phrase
            if phrase_set[i][1] == 'VP':
                is_init = False
                if init_phrase == "":
                    init_phrase = context
                if verb_phrase == "":
                    verb_phrase = phrase_set[i][0]
                else:
                    verb_phrase += ' %s' % phrase_set[i][0]
            # Case of getting a noun phrase
            elif phrase_set[i][1] == 'NP':
                if init_phrase == "":
                    is_init = True
                    init_phrase = phrase_set[i][0]
                # case when previous phrase is also a noun phrase
                elif i > 0 and phrase_set[i - 1][1] == 'NP' and is_init:
                    init_phrase += ' %s' % phrase_set[i][0]
                # case when verb_phrase exists and term_phrase is empty
                elif term_phrase == "":
                    is_init = False
                    term_phrase = phrase_set[i][0]
                # for all other cases append to term_phrase
                elif not is_init:
                    term_phrase += ' %s' % phrase_set[i][0]
            else:
                if is_init:
                    init_phrase += ' %s' % phrase_set[i][0]
                else:
                    term_phrase += ' %s' % phrase_set[i][0]

            is_end = i + 1 >= len(phrase_set)

            # if triple is complete and end reached or next token is a noun phrase
            if (is_end or phrase_set[i + 1][1] == "VP") and is_complete():
                yield get_triple()

            if i + 1 >= len(phrase_set) and not is_complete():
                if term_phrase == '':
                    term_phrase = context
                if not is_complete():
                    # phrases were not broken down correctly
                    print(init_phrase, '|', verb_phrase, '|', term_phrase)
                else:
                    yield get_triple()

            if not is_end and phrase_set[i + 1][1] == "VP" and is_complete():
                init_phrase = term_phrase
                verb_phrase = ""
                term_phrase = ""
