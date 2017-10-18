import re
from collections import Generator

from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer

from core.api import StanfordAPI

# Constants for reuse
ENTITY_PLACEHOLDER = 'ENTITY'
MIN_ENTITY_LENGTH = 2
MIN_SENT_LENGTH = 4
MAX_LEAF_LENGTH = 25
MAX_ENTITY_LENGTH = 100
ALNUM_THRESHOLD = 0.5
RE_NON_ALNUM_SPACE = re.compile(r'[^A-Za-z0-9\s]')
RE_NON_ALPHA_SPACE = re.compile(r'[^A-Za-z\s]')
RE_SPACES = re.compile(r'\s+')
RE_ACRONYM_PLURAL = re.compile(r'(?<=[A-Z])s$')
RE_RIGHTMOST_WORD = re.compile(r'(?<=\s)(\w+)$')
# HTTP header (pbar.g.,"Authorization: Bearer NtBQkXoKElu0H1a1fQ0DWfo6IX4a,") and it
RE_WORD_TOKENIZE = re.compile(r'[^A-Za-z0-9]*\s+|\s*[^A-Za-z0-9]+|[^A-Za-z0-9]+\s*(?=$)|\s+[^A-Za-z0-9]*(?=$)')
RE_SENT_TOKENIZE = re.compile(r'.+?(?<=[A-Za-z])[!.?;:]\s*(?=[A-Z]|$)|.+?$')
RE_ENTITY = re.compile(r'\[(.+?)\(@E\)\]')
RE_BRACKETS = re.compile(r'\s*-[LR][CSR]B-\s*')
RE_ENTITY_SUB_MULTIPLE = re.compile(r'ENTITY(\s+ENTITY)+')
STANFORD_API = StanfordAPI()


def parametrize_entity(entity: str) -> str:
    return '[%s(@E)]' % entity


def normalize_text(text: str, lemmatize: bool = True, ignore_num: bool = False) -> str:
    """
Normalize the text into **lowercase**, **singular** form
    :param text: input text
    :param lemmatize: default is True. If true, lemmatizes the last word of the text
    :param ignore_num: default is False. If true, ignores numerics completely
    :return: output string
    :rtype: str
    """
    lemmatizer = WordNetLemmatizer()
    # remove plurals from acronyms
    text = RE_ACRONYM_PLURAL.sub('', text)
    # remove all non-alphanumeric/space characters
    text = RE_NON_ALPHA_SPACE.sub(' ', text) if ignore_num else RE_NON_ALNUM_SPACE.sub(' ', text)
    # remove extra spaces, strip, and lowercase
    text = RE_SPACES.sub(' ', text).strip().lower()
    # get rightmost word
    rightmost_word = RE_RIGHTMOST_WORD.findall(text)
    # lemmatize and return entity if no rightmost words found
    if len(rightmost_word) == 0:
        lemma = lemmatizer.lemmatize(text) if lemmatize else text
        return RE_SPACES.sub('', lemma)
    # lemmatize the rightmost word and return new text
    else:
        rightmost_word = rightmost_word[-1]
        lem_word = lemmatizer.lemmatize(rightmost_word) if lemmatize else rightmost_word
        return RE_SPACES.sub('', text.replace(rightmost_word, lem_word))


def concat_valid_leaves(leaf_list: list):
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
