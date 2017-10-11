import json

from flask import (Flask, request, render_template)

import config
from core.api import accepts_json, PostgresAPI
from core.engine.msg_engine import MessageEngine
from core.parsers import (TextParser, nlp)
from core.services import StanfordServer

API_COMMANDS = [
    {'url': '/', 'request': 'GET', 'function': 'This Page'},
    {'url': '/content', 'request': 'GET', 'function': 'Ask Question'},
    {'url': '/content', 'request': 'POST', 'function': 'Add Content to KB'},
    {'url': '/display', 'request': 'GET', 'function': 'Display KB Content'},
]


class App:
    def __init__(self, debug: bool = False) -> None:
        super().__init__()
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = config.saml['secret_key']
        self.app.config['SAML_PATH'] = config.saml['saml_path']
        self.postgres_api = PostgresAPI(debug)
        self.message_engine = MessageEngine(self.postgres_api)
        self.cache = []

        @self.app.route('/', methods=['GET'])
        def home_page():
            return render_template('home.html', commands=API_COMMANDS)

        @self.app.route('/display/<int:heading_id>', methods=['GET'])
        def view_content(heading_id: int):
            is_json = accepts_json(request)
            try:
                data = self.postgres_api.get_heading_content_by_id(heading_id)
                if len(data.keys()) != 0:
                    data['content'] = '. '.join([
                        nlp.extract_sentence(TextParser.generate_parse_tree(pos_tags), True)
                        for pos_tags in data['content']
                    ])
                if is_json:
                    return json.dumps(data)
                else:
                    return render_template('content.html', data=data)
            except BaseException as ex:
                data = {'error': ex.args}
                if is_json:
                    return json.dumps(data)
                else:
                    return render_template('error.html', data=data)

        @self.app.route('/content', methods=['GET'])
        def answer_question():
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
            except BaseException as ex:
                data = {'error': ex.args}
                if is_json:
                    return json.dumps(data)
                else:
                    return render_template('error.html', data=data)

        @self.app.route('/content', methods=['POST'])
        def add_content_to_kb():
            return ""

    def start(self):
        with StanfordServer():
            self.app.run(host="0.0.0.0")

    def __process_sentences(self, sentences: list, heading_id: int):
        # sentence parsing logic
        for sentence in sentences:
            for pos_tags in TextParser.generate_pos_tag_sets(sentence):
                normalized_entities = TextParser.extract_normalized_entities(pos_tags)
                sentence = ' '.join(('%s_%s' % (token, pos) for token, pos in pos_tags))
                # add result to cache
                self.cache += [(sentence, normalized_entities, heading_id)]

    # Insert passed headings and sentences into KB
    def process_content(self, headings: list, sentences: list):
        # insert all headings and get the immediate heading id
        heading_id = self.postgres_api.insert_headings(headings)
        # insert the sentences using that heading id
        self.__process_sentences(sentences, heading_id)
        # persist cache in database
        if len(self.cache) > 0:
            for s, n, h in self.cache:
                self.postgres_api.insert_sentence(s, n, h)
            self.cache.clear()

    # Generate frames for KB sentences to create semantics
    def generate_frames(self):
        sentence_count = self.postgres_api.get_sentence_count()
        for index, (sentence_id, sentence_pos) in enumerate(self.postgres_api.get_all_sentences()):
            sent_frames = TextParser.get_frames(sentence_pos)
            self.postgres_api.insert_frames(sentence_id, sent_frames)
            print('%d of %d completed' % (index + 1, sentence_count))


if __name__ == "__main__":
    App().start()
