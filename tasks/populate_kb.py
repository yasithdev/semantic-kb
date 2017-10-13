from datetime import datetime

from app import App
from core.api import MongoAPI
from core.engine import doc_engine
from core.services import StanfordServer


def run():
    mongo_api = MongoAPI()
    doc_count = mongo_api.get_document_count(mongo_api.SCRAPED_DOCS)
    app = App(debug=True)

    # populate the database with sentences and entities
    with StanfordServer():
        i = 0
        for heading_list, flattened_sentences in doc_engine.get_doc_content(mongo_api):
            # catch end of document
            if heading_list is None and flattened_sentences is None:
                i += 1
                print('\n%d of %d completed' % (i, doc_count))
            # insert content
            else:
                app.process_content(heading_list, flattened_sentences)
        # Commit changes to KB
        app.postgres_api.conn.commit()


def populate_kb():
    start_time = datetime.now()
    run()
    completion_time = datetime.now()
    print('Done! (time taken: %s seconds)' % (completion_time - start_time).seconds)


if __name__ == '__main__':
    populate_kb()
