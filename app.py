from flask import (Flask, request, render_template)

import config
from core.api import accepts_json, PostgresAPI
from core.parsers import TextParser
from core.services import StanfordServer


class App:
    def __init__(self, debug: bool = False) -> None:
        super().__init__()
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = config.saml['secret_key']
        self.app.config['SAML_PATH'] = config.saml['saml_path']
        self.postgres_api = PostgresAPI(debug)

        @self.app.route('/')
        def home():
            return render_template('home.html', commands=[
                {'url': '/content', 'request': 'GET', 'function': 'View KB content'},
                {'url': '/learn', 'request': 'POST', 'function': 'Add Knowledge to KB'},
                {'url': '/query', 'request': 'POST', 'function': 'Query from KB'}
            ])

        @self.app.route('/content', methods=['GET'])
        def content():
            is_json = accepts_json(request)
            intent_id = request.args.get('id')
            scope = request.args.get('scope')
            return str([is_json, intent_id, scope])

        @self.app.route('/learn', methods=['POST'])
        def learn():
            return ""

        @self.app.route('/query', methods=['POST'])
        def query():
            is_json = accepts_json(request)
            intent_args = request.args.json()
            return str([is_json, intent_args])

    def start(self):
        with StanfordServer():
            self.app.run()

    # Insert passed headings and sentences into KB
    def populate_kb(self, headings: list, sections: list):
        # insert all headings and get the immediate heading id
        heading_id = self.postgres_api.insert_headings(headings)
        # insert the sentences using that heading id
        for text in sections:
            for parsed_string in TextParser.get_parsed_strings(text):
                normalized_entities = TextParser.extract_normalized_entities(parsed_string)
                self.postgres_api.insert_sentence(parsed_string, normalized_entities, heading_id)

    # Generate frames for KB sentences to create semantics
    def generate_frames(self):
        sentence_count = self.postgres_api.get_sentence_count()
        for index, (sentence_id, sentence) in enumerate(self.postgres_api.get_all_sentences()):
            sent_frames = TextParser.get_frames(sentence)
            self.postgres_api.insert_frames(sentence_id, sent_frames)
            print('%d of %d completed' % (index + 1, sentence_count))


if __name__ == "__main__":
    App().start()
