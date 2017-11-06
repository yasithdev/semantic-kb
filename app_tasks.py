# Insert passed headings and sentences into KB
from datetime import datetime

from app import App
from core.api import PostgresAPI
from core.engine import doc_engine
from core.parsers import TextParser

SMOOTHING_FACTOR = 0.05
SPLIT_CHAR = '__'
POSTGRES_API = PostgresAPI(maintenance=True)


def __process_content(app: App, headings: list, sentences: list):
    def __process_sentences(sents: list, h_id: int):
        # sentence parsing logic
        for sentence in sents:
            for pos_tags in TextParser.generate_pos_tag_sets(sentence):
                entities, dependencies = TextParser.extract_entities_and_dependencies(pos_tags)
                sentence = ' '.join(('%s%s%s' % (token, SPLIT_CHAR, pos) for token, pos in pos_tags))
                # add result to cache
                app.cache += [(sentence, entities, dependencies, h_id)]

    # insert all headings and get the immediate heading id
    heading_id = POSTGRES_API.insert_headings(headings)
    # insert the sentences using that heading id
    __process_sentences(sentences, heading_id)
    # persist cache in database
    if len(app.cache) > 0:
        for s, n, d, h in app.cache:
            POSTGRES_API.insert_sentence(s, n, d, h)
        app.cache.clear()


def __calculate_progress(current: int, total: int, start_time: datetime, p_timestamp: datetime):
    print('\n%d of %d completed' % (current, total))
    # timestamp and percent
    c_timestamp = datetime.now()
    c_percent = round(current * 100 / total, 2)
    # calculate time deltas
    p_timedelta = (p_timestamp - start_time).total_seconds()
    c_timedelta = (c_timestamp - start_time).total_seconds()
    # calculate rates
    p_rate = 0 if current == 1 else ((current - 1) / p_timedelta)
    c_rate = current / c_timedelta
    c_rate = SMOOTHING_FACTOR * p_rate + (1 - SMOOTHING_FACTOR) * c_rate
    # calculate estimated time remaining
    est_time = int((total - current) / c_rate)
    # return new rate and timestamp, %completed and est time
    return c_timestamp, c_percent, est_time


# populate the database with sentences and entities
def populate_content(app: App) -> next:
    start_time = datetime.now()
    timestamp = start_time
    i = 0
    POSTGRES_API.initialize_db()
    count = app.mongo_api.get_document_count(app.mongo_api.SCRAPED_DOCS)

    for heading_list, flattened_sentences in doc_engine.get_doc_content(app.mongo_api):
        # catch end of document
        if heading_list is None and flattened_sentences is None:
            timestamp, percent, est_time = __calculate_progress(i + 1, count, start_time, timestamp)
            app.populate_content_progress = (percent, est_time)
            i += 1
        # insert content
        else:
            __process_content(app, heading_list, flattened_sentences)
    # Commit changes to KB
    POSTGRES_API.conn.commit()
    completion_time = datetime.now()
    app.populate_content_progress = (100, 0)
    print('Done! (time taken: %s seconds)' % (completion_time - start_time).seconds)


# Generate frames for KB sentences to create semantics
def populate_frames(app: App):
    start_time = datetime.now()
    timestamp = start_time
    count = POSTGRES_API.get_sentence_count()
    app.frame_dict = app.mongo_api.load_frame_cache(app.mongo_api.FRAMES)
    for i, (sentence_id, sentence_pos) in enumerate(POSTGRES_API.get_all_sentences()):
        sent_frames = TextParser.get_frames(sentence_pos, app.frame_dict)
        POSTGRES_API.insert_frames(sentence_id, sent_frames)
        timestamp, percent, est_time = __calculate_progress(i + 1, count, start_time, timestamp)
        app.populate_frames_progress = (percent, est_time)
    # commit changes to KB
    POSTGRES_API.conn.commit()
    app.mongo_api.persist_frame_cache(app.mongo_api.FRAMES, app.frame_dict)
    completion_time = datetime.now()
    app.populate_frames_progress = (100, 0)
    print('Done! (time taken: %s seconds)' % (completion_time - start_time).seconds)


# If in maintenance mode, commit the changes to production database
def finalize():
    POSTGRES_API.commit()
