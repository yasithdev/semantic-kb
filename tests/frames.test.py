from datetime import datetime
from core.services import StanfordServer
from core import ToolSet


# frame extraction from database sentences
def train_semantics(tools: ToolSet):
    for sentence in tools.postgres_api.get_all_sentences():
        sent_frames = set(tools.text_parser.get_frames(sentence[1]))
        tools.postgres_api.insert_frames(sentence[0], sent_frames)


def frame_extraction_test():
    tools = ToolSet()
    # extract frames from sentences and populate the database
    start_time = datetime.now()
    with StanfordServer():
        train_semantics(tools)
    completion_time = datetime.now()
    print('Done! (time taken: %s seconds)' % (completion_time-start_time).seconds)