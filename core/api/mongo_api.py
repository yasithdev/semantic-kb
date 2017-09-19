from pymongo import MongoClient


class MongoAPI:
    _collection_name = 'scraped_docs'
    _mongo_uri = 'localhost'
    _mongo_db = 'kb'

    def __init__(self, mongo_uri: str = _mongo_uri, mongo_db: str = _mongo_db) -> None:
        super().__init__()
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def get_all_documents(self, collection_name: str = _collection_name) -> next:
        return self.db[collection_name].find()

    def get_document_count(self, collection_name: str = _collection_name) -> int:
        return self.db[collection_name].count()
