from flask import (Flask, request, render_template)

import config
from core.api import accepts_json


class App:
    def __init__(self) -> None:
        super().__init__()
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = config.saml['secret_key']
        self.app.config['SAML_PATH'] = config.saml['saml_path']

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
        self.app.run()


if __name__ == "__main__":
    App().start()
