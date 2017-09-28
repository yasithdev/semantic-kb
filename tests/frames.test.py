from datetime import datetime
from core.services import StanfordServer
from core.parsers import TextParser
from core.api import PostgresAPI


# frame extraction from database sentences
def train_semantics(postgres_api: PostgresAPI):
    sentence_count = postgres_api.get_sentence_count()
    for index, sentence in enumerate(postgres_api.get_all_sentences()):
        sent_frames = set(TextParser.get_frames(sentence[1]))
        postgres_api.insert_frames(sentence[0], sent_frames)
        print('%d of %d completed' % (index+1, sentence_count))


def run_test():
    postgres_api = PostgresAPI()
    # extract frames from sentences and populate the database
    start_time = datetime.now()
    with StanfordServer():
        train_semantics(postgres_api)
    completion_time = datetime.now()
    print('Done! (time taken: %s seconds)' % (completion_time-start_time).seconds)

if __name__ == '__main__':
    run_test()