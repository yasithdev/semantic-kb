from datetime import datetime
from core.services import StanfordServer
from core import ToolSet
from core import common


# data insertion as sentences and entities
def populate_kb(heading: str, sentences: list, tools: ToolSet):
    for sentence in sentences:
        for parametrized_sentence in tools.text_parser.parametrize_text(sentence):
            sentence = str(parametrized_sentence[0])
            entity_dict = dict(parametrized_sentence[1])
            tools.postgres_api.insert_sentence(sentence, entity_dict)


def sentence_and_entity_extraction_test():
    # Load required tools and data
    tools = ToolSet()
    training_data = tools.mongo_api.get_all_documents()
    data_count = tools.mongo_api.get_document_count()
    start_time = datetime.now()
    # populate the database with sentences and entities
    with StanfordServer():
        for i, data in enumerate(training_data):
            # Iterate through each sentence of the contents and populate KB
            print('URL: %s' % data['_id'], end='', flush=True)
            for contents in data['content']:
                for heading, content in (str(contents['heading']).strip(), str(contents['text']).strip()):
                    if content == '' and heading == '':
                        continue
                    elif content != '':
                        populate_kb(heading, common.sent_tokenize(content), tools)
            print('\n%d of %d completed' % (i + 1, data_count))
    completion_time = datetime.now()
    print('Done! (time taken: %s seconds)' % (completion_time-start_time).seconds)
