# THIS TEST CLEARS THE DATABASE AND POPULATES IT WITH TRAIN DATA
# IF TEST IS TO BE PASSED, THIS SHOULD RUN WITHOUT ENCOUNTERING EXCEPTIONS
from core.api import (ConceptNetAPI, PostgresAPI, MongoAPI)
from core.nlptools import (TextParser)
from core.services import StanfordServer

all_entities = set()
all_frames = set()

# API objects
commonsense_api = ConceptNetAPI()
mongo_api = MongoAPI()
postgres_api = PostgresAPI(debug=True)
# Parser object(s)
text_parser = TextParser()
# Truncate all tables
postgres_api.truncate_tables()
import re


# data insertion and semantic processing methods
def populate_kb(content: str):
    global all_entities, all_frames
    for parametrized_sentence in text_parser.parametrize_text(content):
        sentence = str(parametrized_sentence[0])
        entity_dict = dict(parametrized_sentence[1])
        postgres_api.insert_sentence(sentence, entity_dict)
        for entity in entity_dict.keys():
            all_entities.add(entity)


def train_semantics():
    for sentence in postgres_api.get_all_sentences():
        sent_frames = set(text_parser.get_frames(sentence[1]))
        postgres_api.insert_frames(sentence[0], sent_frames)
        for frame in sent_frames:
            all_frames.add(frame)


# Load training data
training_data = mongo_api.get_all_documents()
data_count = mongo_api.get_document_count()

# Phase 1 - Extract data from phrase and insert into KB (fast)
print('Phase 1 of 2 - Populating KB')
# Initialize Stanford Server
with StanfordServer():
    i = 0
    for data in training_data:
        print('Training Page: %s' % data['_id'], end='', flush=True)
        for contents in data['content']:
            content = str(contents['text']).strip()
            if content == '':
                continue
            sub_contents = [x.strip() for x in re.split(r'(\s\|)|(!\s)', content) if x.strip() != '']
            for sc in sub_contents:
                populate_kb(sc)
        i += 1
        print('\n%d of %d completed' % (i, data_count))
print('Phase 1 Completed...')

# Phase 2 - Train for Semantic Searching
print('Phase 2 of 2 - Training Semantics')
# Initialize Stanford Server
with StanfordServer():
    train_semantics()
print('Phase 2 Completed...')

# Print training statistics after completion
print('Training Completed ------')
print('--- Entities\t- %d' % len(tuple(all_entities)))
print('--- Frames\t- %d' % len(tuple(all_frames)))