from datetime import datetime

from app import App
from core.api import MongoAPI
from core.services import StanfordServer
from tasks import read_doc


def run():
    mongo_api = MongoAPI()
    doc_count = mongo_api.get_document_count(mongo_api.SCRAPED_DOCS)
    app = App(debug=True)

    # populate the database with sentences and entities
    with StanfordServer():
        for i, content in enumerate(read_doc.run(mongo_api)):
            for heading_list, flattened_sentences in content:
                app.populate_kb(heading_list, flattened_sentences)
            print('\n%d of %d completed' % (i + 1, doc_count))


if __name__ == '__main__':
    start_time = datetime.now()
    run()
    completion_time = datetime.now()
    print('Done! (time taken: %s seconds)' % (completion_time - start_time).seconds)
