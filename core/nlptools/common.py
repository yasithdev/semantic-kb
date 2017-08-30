import re

from nltk.corpus import wordnet
from nltk.util import breadth_first

from core.api import StanfordAPI

stanfordAPI = StanfordAPI()


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

    return sentence.strip().replace(" ' ", ""), entities


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


def pos_tag(sentence: str, wordnet_pos = False):
    for token in stanfordAPI.pos_tag(sentence):
        if wordnet_pos:
            yield (token[0], get_wordnet_pos(token[1]))
        else:
            yield tuple(token)


def sanitize(sentence: str):
    # remove entity tags
    entity_sanitized_sent =  re.sub(r'\[\@\d+?\]', 'ENTITY', sentence)
    # remove bracket tags and return
    return re.sub(r'-[LR][CSR]B-', '', entity_sanitized_sent)


def sent_tokenize(input: str):
    return re.split(r"[.:?]\s*(?=[A-Z])", input)


def word_tokenize(input: str):
    regex = r'[.:;,?]*\s+|[.:;,?]+\s*(?=$)'
    for x in re.split(regex, input):
        if x != '':
            yield x
