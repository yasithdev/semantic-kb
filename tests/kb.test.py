# THIS TEST CLEARS THE DATABASE AND POPULATES IT WITH TRAIN DATA
# IF TEST IS TO BE PASSED, THIS SHOULD RUN WITHOUT ENCOUNTERING EXCEPTIONS
from core.api import (ConceptNetAPI, PostgresAPI)
from core.nlptools import (TextParser)

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

# Extract data from phrase and insert into KB
print('INSERTING DATA')
phrase_sets = text_parser.extract_phrase_sets(sample_content)
for phrase_set in phrase_sets:
    triple_set = text_parser.generate_triples(phrase_set)
    db_api.insert_triple_set(triple_set, context)
print('DONE!')

print('CALCULATING FRAMES FOR RELATIONS')
for relation in db_api.get_all_relations():
    frames = text_parser.get_frames(relation[1])
    db_api.add_frames_relation(relation[0], frames)
    # print('.', end=" ")
print('DONE!')
