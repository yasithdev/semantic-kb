import re

from nltk.corpus import wordnet


def flatten_tree(tree_node, accepted_labels):
    phrase = ""
    try:
        tree_node.label()
    except AttributeError:
        pass
    else:
        if tree_node.label() in accepted_labels:
            phrase = " ".join([x[0] for x in tree_node.leaves()])
        if phrase != "" and len(phrase) > 1:
            yield (phrase.strip().replace(" ' ", ""), tree_node.label())


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


def sanitize(word: str):
    result = []
    for c in word:
        if c.isalpha():
            result += [c]
        elif len(result) > 0 and result[-1] != '':
            result += [' ']
    return ''.join(result)


def sent_tokenize(input: str):
    return re.split(r"[.:?]\s*(?=[A-Z])", input)


def word_tokenize(input: str):
    regex = r'[.:;,?]*\s+|[.:;,?]+\s*(?=$)'
    return list(filter(lambda x: x != '', re.split(regex, input)))
