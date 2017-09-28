from pymongo import MongoClient


class MongoAPI:
    # Constants
    SCRAPED_DOCS = 'scraped_docs'
    ENTITIES = 'entities'
    FRAMES = 'frames'
    KNOWLEDGE_BASE = 'knowledge_base'

    _mongo_uri = 'localhost'
    _mongo_db = 'kb'

    def __init__(self, mongo_uri: str = _mongo_uri, mongo_db: str = _mongo_db) -> None:
        super().__init__()
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def get_all_documents(self, collection_name: str) -> next:
        return self.db[collection_name].find()

    def get_document_count(self, collection_name: str) -> int:
        return self.db[collection_name].count()

    def insert_document(self, collection_name: str, document: dict):
        self.db[collection_name].insert_one(document)
