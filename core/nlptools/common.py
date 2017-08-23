import re

from nltk.corpus import wordnet
from nltk.util import breadth_first

from core.api import StanfordAPI


def process_sentence(tree):
    entities = []
    sentence = ''
    for x in breadth_first(tree, maxdepth=2):
        try:
            if x.label() == 'S':
                continue
        except AttributeError:
            pass
        else:
            if x.label() == 'ENT':
                entity = " ".join([x[0] for x in x.leaves()])
                sentence = sentence.replace(entity, '[#%s]' % len(entities))
                entities.append(entity)
            elif x.label() in ['VP', 'NP']:
                sentence = ' '.join([sentence] + [' '.join([p[0] for p in x.leaves()])])

    yield sentence.strip().replace(" ' ", ""), entities


def get_wordnet_pos(treebank_tag: str):
    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R'):
        return wordnet.ADV
    else:
        return ''


def pos_tag(sentence: str):
    pos_tagged_string = StanfordAPI().pos_tag(sentence)
    return [tuple(x.split('_')) for x in str(pos_tagged_string, 'ascii').strip().split()]


def sanitize(word: str):
    result = []
    is_last_num_numeric = False
    for c in word:
        if c.isalpha():
            result += [c]
            is_last_num_numeric = False
        elif c.isnumeric() and not is_last_num_numeric:
            is_last_num_numeric = True
            result += 'ENT'
        elif len(result) > 0 and result[-1] != ' ':
            result += [' ']
    return ''.join(result).replace('LRB', '(').replace('RRB', ')')


def sent_tokenize(input: str):
    return re.split(r"[.:?]\s*(?=[A-Z])", input)


def word_tokenize(input: str):
    regex = r'[.:;,?]*\s+|[.:;,?]+\s*(?=$)'
    return list(filter(lambda x: x != '', re.split(regex, input)))
