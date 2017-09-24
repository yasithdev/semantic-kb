from core.api import (ConceptNetAPI, PostgresAPI, MongoAPI)
from core.nlptools import (TextParser)

class ToolSet:
    def __init__(self) -> None:
        super().__init__()
        self.conceptnet_api = ConceptNetAPI()
        self.mongo_api = MongoAPI()
        self.postgres_api = PostgresAPI(debug=True)
        self.text_parser = TextParser()