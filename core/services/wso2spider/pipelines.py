# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import logging
import re

import pymongo
from scrapy import Spider
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
    # constants
    regex = re.compile(r'\s+(?=[.,:)\]!\'\";])|(?<=[(\[\"\'\\\/])\s+')

    def process_item(self, item, spider):
        # clean unwanted spaces and incompatible characters from given text
        def sanitize(text: str) -> str:
            content = re.sub(r'\s{2,}', ' ', self.regex.sub('', text)).strip()
            if content == '':
                return content
            elif content[0] == '<' and content[-1] == '>':
                return '`%s`' % content
            else:
                return content

        # updated variables for title and content
        filtered_title = sanitize(item['title'])
        filtered_heading = sanitize(item['heading'])
        filtered_content = [sanitize(line) for line in str(item['content']).splitlines() if sanitize(line) != '']

        # return only if item is validated as a doc content
        if (len(filtered_title) > 0 or len(filtered_heading) > 0) and len(filtered_content) > 0:
            return {
                '_id': item['_id'],
                'title': filtered_title,
                'heading': filtered_heading,
                'content': filtered_content
            }
        else:
            raise DropItem("Missing title and heading or content")


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
        Spider.log(spider, 'inserted %s' % item['_id'], logging.DEBUG)
        return item
