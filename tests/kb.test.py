# THIS TEST CLEARS THE DATABASE AND POPULATES IT WITH TRAIN DATA
# IF TEST IS TO BE PASSED, THIS SHOULD RUN WITHOUT ENCOUNTERING EXCEPTIONS
from core.api import (ConceptNetAPI, PostgresAPI)
from core.nlptools import (TextParser)
from core.services import StanfordServer

# Declare variables
# Read sample content from file
with open('static/train_data', 'r') as train_data:
    sample_content = train_data.read()
context = ''

# API objects
commonsense_api = ConceptNetAPI()
db_api = PostgresAPI(debug=True)

# Parser object(s)
text_parser = TextParser()

# Truncate all tables
db_api.truncate_tables()

with StanfordServer():
    # Extract data from phrase and insert into KB
    print('INSERTING DATA')
    all_entities = set()
    for parametrized_sentence in text_parser.parametrize_text(sample_content):
        db_api.insert_sentence(parametrized_sentence)
        for entity in parametrized_sentence[1]:
            all_entities.add(entity)
    print('DONE! Total Entities - %d' % len(list(all_entities)))

    print('CALCULATING FRAMES FOR RELATIONS')
    all_frames = set()
    for sentence in db_api.get_all_sentences():
        sent_frames = text_parser.get_frames(sentence[1])
        db_api.insert_frames(sentence[0], sent_frames)
        for frame in sent_frames:
            all_frames.add(frame)
    print('DONE! Total Frames - %d' % len(list(all_frames)))
