import re

from nltk import Tree
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from nltk.util import breadth_first

from core.api import StanfordAPI


def normalize_entity(entity: str) -> str:
    lemmatizer = WordNetLemmatizer()
    regex = re.compile(r'[\s\-\:\\\/](?=\w+$)')
    split_chars = regex.findall(entity)
    if len(split_chars) > 0:
        # Case where a split exists
        split_char = split_chars[0]
        split_entity = regex.split(entity)
        lem_word = split_entity[1]
        if split_entity[1].lower() == 'apps'.lower():
            pass
        if not lem_word.isupper():
            lem_word = lemmatizer.lemmatize(lem_word.lower())
        iterable = [split_entity[0], split_char, lem_word]
        lemmatized_entity = "".join(iterable)
    else:
        # Case when entity is one-word
        lemmatized_entity = lemmatizer.lemmatize(entity)
    return lemmatized_entity


def process_sentence(tree):
    normalized_entities = []
    sentence = ''
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
                    if leaf.label() == 'ENT':
                        # Generate entity from tree leaves
                        entity = ' '.join([l[0] for l in leaf.leaves()])
                        # Generate normalized form of the entity
                        normalized_entity = normalize_entity(entity)
                        # print('%s -> %s' % (entity, normalized_entity))

                        # Check if normalized_entity already in list, and assign index if exists
                        if normalized_entity in normalized_entities:
                            index = normalized_entities.index(normalized_entity)
                        else:
                            # insert normalized_entity in normalized_entities and set the index
                            index = len(normalized_entities)
                            normalized_entities.append(normalized_entity)
                        # Replace the original entity with the tagged form of entity
                        phrase = phrase.replace(entity, '[%s(E:%s|@:%d)]' % (entity, normalized_entity, index))
                sentence = ' '.join([sentence, phrase])

    result = sentence.replace(" 's", "'s"), normalized_entities
    return result


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


def pos_tag(sentence: str, wordnet_pos=False):
    # get pos-tagged output from stanford API
    stanford_api = StanfordAPI()
    pos_tagged_sentence = stanford_api.pos_tag(sentence)
    # yield triples depending on which pos-tag syntax is requested
    for token in pos_tagged_sentence:
        # wordnet pos-tags
        if wordnet_pos:
            yield (token[0], get_wordnet_pos(token[1]))
        # penn-treebank pos-tags (default)
        else:
            yield tuple(token)


def sanitize(sentence: str, preserve_entities = False) -> str:
    """
Convert a sentence obtained from Semantic KB it into Frame-Extractable format.
Named Entity tags are replace with the keyword ENTITY (if preserve_entities = False)
    :param sentence: sentence from Semantic KB
    :param preserve_entities: whether to preserve entities, or replace them with ENTITY
    :return: sanitized string
    """
    # declare temporary variable
    entity_sanitized_sent = sentence

    # sanitize entity wrappers
    if preserve_entities:
        entity_matches = re.findall(r'\[.+?\(E:.+?\|@:\d+?\)\]', sentence)
        # remove entity wrappers and replace with entity
        for match in entity_matches:
            sub = re.findall(r'(?<=\[).+?(?=\(E:.+?\|@:\d+?\)\])', match)[0]
            entity_sanitized_sent = entity_sanitized_sent.replace(match, sub, 1)
    else:
        # replace entity wrappers with keyword ENTITY
        entity_sanitized_sent = re.sub(r'\[.+?\(E:.+?\|@:\d+?\)\]', 'ENTITY', sentence).strip()

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


def sent_tokenize(input: str):
    return re.split(r"[.:?]\s*(?=[A-Z])", input)


def word_tokenize(input: str):
    regex = r'[.:;,?]*\s+|[.:;,?]+\s*(?=$)'
    for x in re.split(regex, input):
        if x != '':
            yield x
