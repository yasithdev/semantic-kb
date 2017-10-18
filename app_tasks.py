# Insert passed headings and sentences into KB
from datetime import datetime, timedelta

from app import App
from core.engine import doc_engine
from core.parsers import TextParser

SMOOTHING_FACTOR = 0.3


def __process_content(app: App, headings: list, sentences: list):
    def __process_sentences(sents: list, heading_id: int):
        # sentence parsing logic
        for sentence in sents:
            for pos_tags in TextParser.generate_pos_tag_sets(sentence):
                normalized_entities = TextParser.extract_normalized_entities(pos_tags)
                sentence = ' '.join(('%s_%s' % (token, pos) for token, pos in pos_tags))
                # add result to cache
                app.cache += [(sentence, normalized_entities, heading_id)]

    # insert all headings and get the immediate heading id
    heading_id = app.postgres_api.insert_headings(headings)
    # insert the sentences using that heading id
    __process_sentences(sentences, heading_id)
    # persist cache in database
    if len(app.cache) > 0:
        for s, n, h in app.cache:
            app.postgres_api.insert_sentence(s, n, h)
        app.cache.clear()


def __calculate_progress(current: int, total: int, p_timestamp: datetime, p_rate: float):
    # update current variables
    c_timestamp = datetime.now()
    c_timedelta = (c_timestamp - p_timestamp).microseconds / 1000000
    c_rate = SMOOTHING_FACTOR * p_rate + (1 - SMOOTHING_FACTOR) * (1 / c_timedelta)
    percent = round(current * 100 / total, 2)
    est_time = timedelta(c_rate * (total - current)).seconds
    print('\n%d of %d completed' % (current, total))
    # return new rate and timestamp, %completed and est time
    return c_timestamp, c_rate, percent, est_time


# populate the database with sentences and entities
def populate_content(app: App) -> next:
    start_time = datetime.now()
    timestamp = start_time
    rate, i = 0, 0
    app.postgres_api.initialize_db()
    count = app.mongo_api.get_document_count(app.mongo_api.SCRAPED_DOCS)

    for heading_list, flattened_sentences in doc_engine.get_doc_content(app.mongo_api):
        # catch end of document
        if heading_list is None and flattened_sentences is None:
            i += 1
            timestamp, rate, percent, est_time = __calculate_progress(i + 1, count, timestamp, rate)
            app.populate_kb_progress = (percent, est_time)
        # insert content
        else:
            __process_content(app, heading_list, flattened_sentences)
    # Commit changes to KB
    app.postgres_api.conn.commit()
    completion_time = datetime.now()
    app.populate_kb_progress = (100, 0)
    print('Done! (time taken: %s seconds)' % (completion_time - start_time).seconds)


# Generate frames for KB sentences to create semantics
def populate_frames(app: App):
    start_time = datetime.now()
    timestamp = start_time
    rate = 0
    count = app.postgres_api.get_sentence_count()

    for i, (sentence_id, sentence_pos) in enumerate(app.postgres_api.get_all_sentences()):
        sent_frames = TextParser.get_frames(sentence_pos)
        app.postgres_api.insert_frames(sentence_id, sent_frames)
        timestamp, rate, percent, est_time = __calculate_progress(i + 1, count, timestamp, rate)
        app.populate_frames_progress = (percent, est_time)
    # commit changes to KB
    app.postgres_api.conn.commit()
    completion_time = datetime.now()
    app.populate_frames_progress = (100, 0)
    print('Done! (time taken: %s seconds)' % (completion_time - start_time).seconds)
