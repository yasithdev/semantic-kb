import re
from collections import Generator

from nltk import Tree
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from nltk.util import breadth_first

from core.api import StanfordAPI

# Constants for reuse
ENTITY_PLACEHOLDER = 'ENTITY'
MIN_ENTITY_LENGTH = 2
MIN_SENT_LENGTH = 4
MAX_LEAF_LENGTH = 25
MAX_ENTITY_LENGTH = 100
ALNUM_THRESHOLD = 0.5
RE_NON_ALNUM_SPACE = re.compile(r'[^A-Za-z0-9\s]')
RE_SPACES = re.compile(r'\s+')
RE_ACRONYM_PLURAL = re.compile(r'(?<=[A-Z])s$')
RE_RIGHTMOST_WORD = re.compile(r'(?<=\s)(\w+)$')
# HTTP header (e.g.,"Authorization: Bearer NtBQkXoKElu0H1a1fQ0DWfo6IX4a,") and it
RE_WORD_TOKENIZE = re.compile(r'[^A-Za-z0-9]*\s+|\s*[^A-Za-z0-9]+|[^A-Za-z0-9]+\s*(?=$)|\s+[^A-Za-z0-9]*(?=$)')
RE_SENT_TOKENIZE = re.compile(r'.+?(?<=[A-Za-z])[!.?;:]\s*(?=[A-Z]|$)|.+?$')
RE_ENTITY = re.compile(r'\[(.+?)\(@E\)\]')
RE_BRACKETS = re.compile(r'\s*-[LR][CSR]B-\s*')
RE_ENTITY_SUB_MULTIPLE = re.compile(r'ENTITY(\s+ENTITY)+')
STANFORD_API = StanfordAPI()


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


def __concat_valid_leaves(leaf_list: list):

    def validate_and_yield_entity(leaves: list) -> next:
        entity = ' '.join(leaves)
        total_len = len(entity)
        if MAX_ENTITY_LENGTH >= total_len >= MIN_ENTITY_LENGTH:
            junk_len = len(RE_NON_ALNUM_SPACE.findall(entity))
            ratio = 1 - junk_len / total_len
            if ratio >= ALNUM_THRESHOLD:
                yield entity

    # when long leaf found, join all leaves up to it and return as one entity
    si = 0
    for i, l in enumerate(leaf_list):
        if len(l) > MAX_LEAF_LENGTH and si < i:
            yield from validate_and_yield_entity(leaf_list[si:i])
            si = i + 1
    # yield final entity if possible
    if si < len(leaf_list):
        yield from validate_and_yield_entity(leaf_list[si:])


def extract_normalized_entities(parse_tree: Tree) -> set:
    """
Accepts a **NLTK tree**, extract the entities, and return them in normalized form
of the entities in a dict
    :param parse_tree: NLTK Tree
    :return: set of normalized entities for the tree
    :rtype: Set
    """
    normalized_entities = set()
    for node in breadth_first(parse_tree, maxdepth=1):
        # If noun phrase or verb phrase found
        # NOTE: this node is traversed BEFORE traversing to ENT node, which is a leaf node if a VP or NP
        # i.e. the ENT nodes are traversed after traversing all VPs and NPs
        if node.label() in ['VP', 'NP']:
            # traverse each entity and parametrize the phrase
            for leaf in breadth_first(node, maxdepth=1):
                # continue if leaf is not an entity leaf
                if not isinstance(leaf, Tree) or leaf.label() != 'EN':
                    continue
                else:
                    # Generate entity from tree leaves, and add to normalized_entities
                    for entity in __concat_valid_leaves(leaf.leaves()):
                        normalized_entities.add(normalize_entity(entity))
    return normalized_entities


def get_wordnet_pos(treebank_tag: str) -> str:
    """
Transform **Penn-Treebank** POS tags to **Wordnet** POS Tags
    :param treebank_tag: penn-treebank pos-tag
    :return: wordnet pos-tag
    """
    c = treebank_tag[0]
    if c == 'J':
        return wordnet.ADJ
    elif c == 'V':
        return wordnet.VERB
    elif c == 'N':
        return wordnet.NOUN
    elif c == 'R':
        return wordnet.ADV
    else:
        return ''


def pos_tag(sentence: str, wordnet_pos=False) -> next:
    """
POS-tag a sentence using Stanford pos-tagger, and return a list of pos_tagged tokens
    :param sentence: the sentence to pos-tag
    :param wordnet_pos: If true, return pos-tags in wordnet-format. Default is false (returns stanford pos-tag format)
    """
    # yield triples depending on which pos-tag syntax is requested
    for token, pos in STANFORD_API.pos_tag(sentence):
        # yield wordnet pos-tag or penn-treebank pos tags depending on choice
        yield [token, get_wordnet_pos(pos) if wordnet_pos else pos]


def extract_sentence(parse_tree: Tree, preserve_entities=False) -> str:
    """
Recreate and return original sentence from parse_tree. If preserve_entities set to False (default), entities
are replaced by a placeholder to simplify sentence
    :param parse_tree: nltk Tree
    :param preserve_entities: whether to preserve entities, or replace them with a placeholder
    :return: sentence
    """
    # concatenate all leaves and create a sentence if entities are preserved
    if preserve_entities:
        entity_sanitized_sent = ' '.join(parse_tree.leaves())

    # if not, replace each entity with a placeholder and create a sentence
    else:
        entity_sanitized_sent = ''
        # declare temporary variable
        for node in breadth_first(parse_tree, maxdepth=1):
            # If noun phrase or verb phrase found
            # NOTE: this node is traversed BEFORE traversing to ENT node, which is a leaf node if a VP or NP
            # i.e. the ENT nodes are traversed after traversing all VPs and NPs
            if node.label() in ['VP', 'NP']:
                phrase = ' '.join(node.leaves())
                # traverse each entity and parametrize the phrase
                for leaf in breadth_first(node, maxdepth=1):
                    # continue if leaf is not an entity leaf
                    if not isinstance(leaf, Tree) or leaf.label() != 'EN':
                        continue
                    else:
                        entity = ' '.join(leaf.leaves())
                        phrase = phrase.replace(entity, ENTITY_PLACEHOLDER)
                entity_sanitized_sent += ' ' + phrase

    entity_sanitized_sent = entity_sanitized_sent.strip()

    # sanitize bracket tags
    if preserve_entities:
        if len(RE_BRACKETS.findall(entity_sanitized_sent)) > 0:
            # replace bracket tags with correct brackets
            entity_sanitized_sent = re.sub(r'\s*-LCB-\s*', ' {', entity_sanitized_sent).strip()
            entity_sanitized_sent = re.sub(r'\s*-RCB-\s*', '} ', entity_sanitized_sent).strip()
            entity_sanitized_sent = re.sub(r'\s*-LSB-\s*', ' [', entity_sanitized_sent).strip()
            entity_sanitized_sent = re.sub(r'\s*-RSB-\s*', '] ', entity_sanitized_sent).strip()
            entity_sanitized_sent = re.sub(r'\s*-LRB-\s*', ' (', entity_sanitized_sent).strip()
            entity_sanitized_sent = re.sub(r'\s*-RRB-\s*', ') ', entity_sanitized_sent).strip()
    else:
        # remove any bracket tags
        entity_sanitized_sent = RE_BRACKETS.sub(' ', entity_sanitized_sent).strip()

    # if ENTITY placeholders are used, merge neighbouring placeholders
    if not preserve_entities:
        entity_sanitized_sent = RE_ENTITY_SUB_MULTIPLE.sub(ENTITY_PLACEHOLDER, entity_sanitized_sent).strip()

    # return sanitized sentence
    return entity_sanitized_sent


def sent_tokenize(in_str: str) -> Generator:
    """
Accepts a string containing *multiple* sentences, and return a list of sentences.
    :param in_str: string containing multiple sentences
    :return: list of sentences
    :rtype: list
    """
    return (
        x.strip() for x in RE_SENT_TOKENIZE.findall(in_str)
        if x.strip() != '' and not len(x.strip()) < MIN_SENT_LENGTH
    )
