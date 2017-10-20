import json
from threading import Thread

from flask import (Flask, request, render_template, Response, redirect)

import app_tasks
import config
from core.api import accepts_json, PostgresAPI, MongoAPI
from core.engine.msg_engine import MessageEngine
from core.parsers import (TextParser)
from core.services import StanfordServer

API_COMMANDS = [
    {'url': '/', 'request': 'GET', 'function': 'This Page'},
    {'url': '/content', 'request': 'GET', 'function': 'Ask Question'},
    {'url': '/init', 'request': 'GET', 'function': 'Populate KB'},
    {'url': '/display', 'request': 'GET', 'function': 'Display KB Content'},
]


class App(Flask):
    def __init__(self, import_name: str) -> None:
        super().__init__(import_name)
        self.config['SECRET_KEY'] = config.saml['secret_key']
        self.config['SAML_PATH'] = config.saml['saml_path']
        self.mongo_api = MongoAPI()
        self.postgres_api = PostgresAPI(database="semantic_kb")
        self.message_engine = MessageEngine(self.postgres_api)
        self.cache = []
        self.status = 0
        self.populate_content_progress = (100, 0)
        self.populate_frames_progress = (100, 0)

        @self.route('/', methods=['GET'])
        def home_page():
            return render_template('home.html', commands=API_COMMANDS)

        @self.route('/display/<int:heading_id>', methods=['GET'])
        def content_page(heading_id: int):
            is_json = accepts_json(request)
            try:
                data = self.postgres_api.get_heading_content_by_id(heading_id)
                if len(data.keys()) > 0:
                    data['content'] = ' '.join([
                        TextParser.extract_sentence(pos_tags, preserve_entities=True)
                        for pos_tags in data['content']
                    ])
                if is_json:
                    return json.dumps(data)
                else:
                    return render_template('content.html', data=data)
            except Exception as ex:
                data = {'error': ex}
                print(ex)
                if is_json:
                    return json.dumps(data)
                else:
                    return render_template('error.html', data=data)

        @self.route('/content', methods=['GET'])
        def question_answer_page():
            is_json = accepts_json(request)
            try:
                question = request.args.get('question')
                answers = [
                    {'heading': heading, 'url': url, 'score': round(score, 2), 'answer': answer}
                    for heading, url, score, answer in self.message_engine.process_and_answer(question)
                ] if question is not None else []

                # output the answers
                if is_json:
                    return json.dumps({
                        'question': question,
                        'answers': answers
                    })
                else:
                    return render_template('answers.html', question=question, answers=answers)
            except Exception as ex:
                data = {'error': ex}
                print(ex)
                if is_json:
                    return json.dumps(data)
                else:
                    return render_template('error.html', data=data)

        @self.route('/progress_kb')
        def progress_kb():
            def get_log():
                p = self.populate_content_progress
                yield 'data: {"percent": "%s", "remaining" : "%s"}\n\n' % p

            return Response(get_log(), mimetype="text/event-stream")

        @self.route('/progress_frames')
        def progress_frames():
            def get_log():
                p = self.populate_frames_progress
                yield 'data: {"percent": "%s", "remaining" : "%s"}\n\n' % p

            return Response(get_log(), mimetype="text/event-stream")

        @self.route('/init', methods=['GET'])
        def init():
            if self.status != 1:
                self.status = 1

                # method to run a complete init
                def full_init():
                    self.populate_content_progress = (0, 0)
                    self.populate_frames_progress = (0, 0)
                    app_tasks.populate_content(self)
                    app_tasks.populate_frames(self)
                    self.populate_content_progress = (100, 0)
                    self.populate_frames_progress = (100, 0)
                    self.status = 0

                Thread(target=full_init).start()
            return redirect('/progress')

        @self.route('/progress', methods=['GET'])
        def progress():
            return render_template('progress.html')

    def start(self):
        with StanfordServer():
            self.run(host="0.0.0.0")


if __name__ == "__main__":
    App(__name__).start()
