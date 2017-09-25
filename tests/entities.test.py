from datetime import datetime

from core.api import (MongoAPI, PostgresAPI)
from core.parsers import (TextParser, MarkdownParser, common)
from core.services import StanfordServer


# data insertion as sentences and entities
def populate_kb(heading: list, sentences: list, postgres_api: PostgresAPI, mongo_api: MongoAPI):
    for sentence in sentences:
        for parametrized_sentence in TextParser.parametrize_text(sentence):
            sentence = str(parametrized_sentence[0])
            entity_dict = dict(parametrized_sentence[1])
            postgres_api.insert_sentence(sentence, entity_dict)


def run_test(postgres_api: PostgresAPI, mongo_api: MongoAPI):
    # Load required tools and data
    training_data = mongo_api.get_all_documents(MongoAPI.SCRAPED_DOCS)
    training_data_count = mongo_api.get_document_count(MongoAPI.SCRAPED_DOCS)
    start_time = datetime.now()
    # populate the database with sentences and entities
    with StanfordServer():
        for i, data in enumerate(training_data):
            # Iterate through each sentence of the contents and populate KB
            print('URL: %s' % data['_id'], flush=True)
            for heading, sentences in MarkdownParser.unmarkdown(data['content'], data['heading']):
                # sentence tokenize and flatten the sentences
                flattened_sentences = []
                for sentence in sentences:
                    flattened_sentences.extend(common.sent_tokenize(sentence))
                populate_kb(heading, flattened_sentences, postgres_api, mongo_api)
            print('\n%d of %d completed' % (i + 1, training_data_count))
    completion_time = datetime.now()
    print('Done! (time taken: %s seconds)' % (completion_time - start_time).seconds)


if __name__ == '__main__':
    _postgres_api = PostgresAPI(debug=True)
    _mongo_api = MongoAPI()
    run_test(_postgres_api, _mongo_api)
