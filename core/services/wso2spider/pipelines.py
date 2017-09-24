# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import re

import pymongo
from scrapy.exceptions import DropItem


class DuplicatesPipeline(object):
    def __init__(self):
        self.ids_seen = set()

    def process_item(self, item, spider):
        if item['_id'] in self.ids_seen:
            raise DropItem("Duplicate item found")
        else:
            self.ids_seen.add(item['_id'])
            return item


class Wso2SpiderPipeline(object):
    def process_item(self, item, spider):
        # clean unwanted spaces and incompatible characters from given text
        regex = re.compile(r'[\x80-\xff]|\s+(?=[.,:)\]!\'\";])|(?<=[(\[\"\'])\s+')

        def sanitize(text: str) -> str:
            return re.sub(r'\s{2,}', ' ', regex.sub('', text)).strip()

        # previous id, title and content
        id = item['_id']
        title = item['title']
        content = item['content']
        urls = [{'name': key, 'url': item['urls'][key]} for key in dict.keys(item['urls'])]

        # updated variables for title and content
        filtered_title = sanitize(title)
        filtered_content = []

        for item in content:
            filtered_item = {
                'heading': sanitize(item['heading']),
                'text': sanitize('\n'.join(item['text']))
            }
            # only add filtered_item to filtered_content if any content is there
            if len(filtered_item['heading']) > 0 or len(filtered_item['text']) > 0:
                filtered_content += [filtered_item]

        # return only if item is validated as a doc content
        if len(filtered_title) > 0 and len(filtered_content) > 0:
            return {
                '_id': id,
                'title': filtered_title,
                'content': filtered_content
            }
        else:
            raise DropItem("Missing title or content")


class MongoPipeline(object):
    collection_name = 'scraped_docs'

    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        self.db[self.collection_name].insert_one(dict(item))
        return item
