from datetime import datetime

from app import App
from core.services import StanfordServer


def run():
    # Populate KB with Frames
    App().generate_frames()


if __name__ == '__main__':
    start_time = datetime.now()
    try:
        run()
    except ConnectionError:
        with StanfordServer():
            run()
    completion_time = datetime.now()
    print('Done! (time taken: %s seconds)' % (completion_time - start_time).seconds)
