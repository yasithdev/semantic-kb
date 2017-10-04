import re

from nltk import Tree
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from nltk.util import breadth_first

from core.api import StanfordAPI

MAX_LEAF_LENGTH = 25
MAX_ENTITY_LENGTH = 100
RE_NON_ALNUM_SPACE = re.compile(r'[^A-Za-z0-9\s]')
RE_SPACES = re.compile(r'\s+')
RE_ACRONYM_PLURAL = re.compile(r'(?<=[A-Z])s$')
RE_RIGHTMOST_WORD = re.compile(r'(?<=\s)(\w+)$')

def parametrize_entity(entity: str) -> str:
    return '[%s(@E)]' % entity


def normalize_entity(entity: str) -> str:
    """
Normalize the entity into **lowercase**, **singular** form
    :param entity: input entity
    :return: output string
    :rtype: str
    """
    lemmatizer = WordNetLemmatizer()
    # remove plurals from acronyms
    entity = RE_ACRONYM_PLURAL.sub('', entity)
    # remove all non-alphanumeric/space characters
    entity = RE_NON_ALNUM_SPACE.sub(' ', entity)
    # remove extra spaces, strip, and lowercase
    entity = RE_SPACES.sub(' ', entity).strip().lower()
    # get rightmost word
    rightmost_word = RE_RIGHTMOST_WORD.findall(entity)
    # lemmatize and return entity if no rightmost words found
    if len(rightmost_word) == 0:
        return RE_SPACES.sub('', lemmatizer.lemmatize(entity))
    # lemmatize the rightmost word and return new entity
    else:
        rightmost_word = rightmost_word[-1]
        lem_word = lemmatizer.lemmatize(rightmost_word)
        return RE_SPACES.sub('', entity.replace(rightmost_word, lem_word))


def parametrize_and_normalize_tree(tree: Tree, max_leaf_length: int = MAX_LEAF_LENGTH, max_entity_length: int = MAX_ENTITY_LENGTH) -> tuple:
    """
Accepts a **NLTK tree**, and convert into a parametrized sentence with entities wrapped in the form
[**original_phrase**(@E)]. Return the parametrized sentence, and the entity normalization
of the entities in a dict
    :param max_entity_length:
    :param max_leaf_length:
    :param tree: NLTK Tree
    :return: tuple in the format (*parametrized_sentence*, *entity_normalization*)
    :rtype: tuple
    """
    parametrized_sentence = ''
    entity_normalization = {}
    for node in breadth_first(tree, maxdepth=1):
        try:
            if node.label() == 'S':
                continue
        except AttributeError:
            pass
        else:
            # If noun phrase or verb phrase found
            # NOTE: this node is traversed BEFORE traversing to ENT node, which is a leaf node if a VP or NP
            # i.e. the ENT nodes are traversed after traversing all VPs and NPs
            if node.label() in ['VP', 'NP']:
                phrase = ' '.join([l[0] for l in node.leaves()])
                for leaf in breadth_first(node, maxdepth=1):
                    if not isinstance(leaf, Tree):
                        continue
                    # If an entity is found
                    if leaf.label() == 'EN':
                        # Generate entity from tree leaves
                        entity_leaves = [l[0] for l in leaf.leaves()]

                        def split_long_entities(leaf_list, ml):
                            si = 0
                            for i, l in enumerate(leaf_list):
                                if len(l) > ml and si < i:
                                    yield leaf_list[si:i]
                                    si = i+1
                            if si < len(leaf_list):
                                yield leaf_list[si:]

                        split_entities = list(split_long_entities(entity_leaves, max_leaf_length))
                        for entity in [' '.join(x) for x in split_entities]:
                            # validation constraints
                            if max_entity_length >= len(entity) > 1 and float(len(entity) - len(re.findall(r'[^A-Za-z0-9\s]', entity)))/len(entity) > 0.5:
                                # Replace the original entity(ies) with entity wrapper
                                phrase = phrase.replace(entity, parametrize_entity(entity))
                                entity_normalization[normalize_entity(entity)] = entity
                parametrized_sentence = ' '.join([parametrized_sentence, phrase]).replace(" 's", "'s")
    return parametrized_sentence, entity_normalization


def get_wordnet_pos(treebank_tag: str) -> str:
    """
Transform **Penn-Treebank** POS tags to **Wordnet** POS Tags
    :param treebank_tag: penn-treebank pos-tag
    :return: wordnet pos-tag
    """
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


def pos_tag(sentence: str, wordnet_pos=False, ignored_words: list = list()) -> next:
    """
POS-tag a sentence using Stanford pos-tagger, ignore any words mentioned in ignored_words,
and return a list of pos_tagged tokens
    :param sentence: the sentence to pos-tag
    :param wordnet_pos: If true, return pos-tags in wordnet-format. Default is false (returns stanford pos-tag format)
    :param ignored_words: Any specific words to explicitly ignore when pos-tagging
    :rtype: Generator
    """
    stanford_api = StanfordAPI()
    pos_tagged_sentence = stanford_api.pos_tag(sentence)
    # yield triples depending on which pos-tag syntax is requested
    for token in pos_tagged_sentence:
        # do not yield words in ignored_words list
        if token[0] in ignored_words:
            continue
        # wordnet pos-tags
        if wordnet_pos:
            yield (token[0], get_wordnet_pos(token[1]))
        # penn-treebank pos-tags (default)
        else:
            yield tuple(token)


def sanitize(parametrized_sentence: str, preserve_entities=False) -> str:
    """
Convert a sentence obtained from Semantic KB it into Frame-Extractable format.
Named Entity tags are replace with the keyword ENTITY (if preserve_entities = False)
    :param parametrized_sentence: parametrized_sentence from Semantic KB
    :param preserve_entities: whether to preserve entities, or replace them with ENTITY
    :return: sanitized string
    """
    # declare temporary variable
    entity_sanitized_sent = parametrized_sentence

    # sanitize entity wrappers
    if preserve_entities:
        # substitute entity names to entity wrapper
        entity_sanitized_sent = re.sub(r'\[(.+?)\(@E\)\]', r'\1', entity_sanitized_sent).strip()
    else:
        # substitute the placeholder ENTITY to entity wrapper
        entity_sanitized_sent = re.sub(r'\[(.+?)\(@E\)\]', 'ENTITY', entity_sanitized_sent).strip()

    # sanitize bracket tags
    if preserve_entities:
        # replace bracket tags with correct brackets
        entity_sanitized_sent = re.sub(r'\s*-LCB-\s*', ' {', entity_sanitized_sent).strip()
        entity_sanitized_sent = re.sub(r'\s*-RCB-\s*', '} ', entity_sanitized_sent).strip()
        entity_sanitized_sent = re.sub(r'\s*-LSB-\s*', ' [', entity_sanitized_sent).strip()
        entity_sanitized_sent = re.sub(r'\s*-RSB-\s*', '] ', entity_sanitized_sent).strip()
        entity_sanitized_sent = re.sub(r'\s*-LRB-\s*', ' (', entity_sanitized_sent).strip()
        entity_sanitized_sent = re.sub(r'\s*-RRB-\s*', ') ', entity_sanitized_sent).strip()
    else:
        # remove any bracket tags
        entity_sanitized_sent = re.sub(r'\s*-[LR][CSR]B-\s*', ' ', entity_sanitized_sent).strip()

    # if ENTITY placeholders are used, merge neighbouring placeholders
    if not preserve_entities:
        entity_sanitized_sent = re.sub(r'ENTITY(\s+ENTITY)+', 'ENTITY', entity_sanitized_sent).strip()

    # return sanitized sentence
    return entity_sanitized_sent


def sent_tokenize(input_string: str) -> list:
    """
Accepts a string containing *multiple* sentences, and return a list of sentences.
    :param input_string: string containing multiple sentences
    :return: list of sentences
    :rtype: list
    """
    output = [x.strip() for x in re.split(r"(?<=[a-zA-Z])([!.?;:]\s*)(?=[A-Z])", input_string)
            if x.strip() != '' and not len(x.strip()) < 2]
    return output


def word_tokenize(input: str) -> list:
    """
Accepts a string containing a *single* sentence, and return a generator for the tokens
    :param input: sentence string
    :return: list of tokens
    :rtype: list
    """
    regex = r'[.:;,?]*\s+|[.:;,?]+\s*(?=$)'
    for x in re.split(regex, input):
        if x != '':
            yield x
