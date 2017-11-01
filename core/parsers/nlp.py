import re
from collections import Generator

from nltk import ngrams
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer

from core.api import StanfordAPI

# Constants for reuse
ALNUM_THRESHOLD = 0.5
ENTITY_PLACEHOLDER = 'ENTITY'
LIST_JUNK = (r'[ie](\s|\.)+[eg](\s|\.|$)+', r'etc(\s|\.|$)+')
MAX_ENTITY_LENGTH = 100
MIN_ENTITY_LENGTH = 2
MAX_LEAF_LENGTH = 25
MIN_LEAF_LENGTH = 2
MIN_SENT_LENGTH = 4
RE_PLURAL_DROP = re.compile(r'(?<=[A-Ze])(s)$')
RE_PLURAL_Y = re.compile(r'(?<=[A-Za-z])(ies)$')
RE_BRACKETS = re.compile(r'\s*-[LR][CSR]B-\s*')
RE_ENTITY = re.compile(r'\[(.+?)\(@E\)\]')
RE_ENTITY_SUB_MULTIPLE = re.compile(r'ENTITY(\s+ENTITY)+')
RE_JUNK = re.compile(r'|'.join(r'(%s)' % x for x in LIST_JUNK))
RE_NON_ALNUM_SPACE = re.compile(r'[^A-Za-z0-9.\s]')
RE_NON_ALPHA_SPACE = re.compile(r'[^A-Za-z.\s]')
RE_PUNCT = re.compile(r'(\s+[.,()!?\\:]\s*)|(\s*[.,()!?\\:](\s+|(\s*$)))')
RE_LINKS = re.compile(r'(http(s)?://)|(<.+?>/)|(:\d{2,})|(^[<{])')
RE_RIGHTMOST_WORD = re.compile(r'(?<=\s)(\w+)$')
RE_SENT_TOKENIZE = re.compile(r'.+?(?<=[A-Za-z])[!.?;:]\s*(?=[A-Z]|$)|.+?$')
RE_SPACES = re.compile(r'\s+')
RE_WORD_TOKENIZE = re.compile(r'[^A-Za-z0-9]*\s+|\s*[^A-Za-z0-9]+|[^A-Za-z0-9]+\s*(?=$)|\s+[^A-Za-z0-9]*(?=$)')
STANFORD_API = StanfordAPI()


def normalize_text(text: str, lemmatize: bool = True, ignore_num: bool = False) -> str:
    """
Normalize the text into **lowercase**, **singular** form
    :param text: input text
    :param lemmatize: default is True. If true, lemmatizes the last word of the text
    :param ignore_num: default is False. If true, ignores numerals completely
    :return: output string
    :rtype: str
    """
    lemmatizer = WordNetLemmatizer()
    # remove plurals from entities
    text = RE_PLURAL_DROP.sub('', text)
    text = RE_PLURAL_Y.sub('y', text)
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
        text = text[::-1].replace(rightmost_word[::-1], lem_word[::-1], 1)[::-1]
        text = RE_SPACES.sub(' ', text.replace(rightmost_word, lem_word))
        return text


def yield_valid_entities(leaf_list: list):
    # run pos tagger again and only extract most relevant part
    # Step 1 - Drop Links and Short/Long Leaves
    leaf_list = [
        y for y in (RE_JUNK.sub('', x).strip() for x in leaf_list if not RE_LINKS.search(x))
        if MAX_LEAF_LENGTH >= len(y) >= MIN_LEAF_LENGTH
    ]
    # Step 3 - Split by punctuations, and ignore too long or too entities
    entity_list = [
        x.strip('. ') for x in (y.strip() for y in RE_PUNCT.split(' '.join(leaf_list)) if y is not None) if
        x != ''
        and MAX_ENTITY_LENGTH >= len(x) >= MIN_ENTITY_LENGTH
        and len(RE_NON_ALPHA_SPACE.findall(x)) / len(x) < ALNUM_THRESHOLD
    ]
    yield from entity_list


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


def get_ngrams(phrase: str, min_n: int = 1):
    tokens = phrase.split()
    if len(tokens) > min_n:
        for i in range(len(tokens) - 1, min_n - 1, -1):
            yield [' '.join(grams) for grams in ngrams(tokens, i)]
