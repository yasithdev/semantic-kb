import re

from core.api import MongoAPI
from core.parsers import (MarkdownParser, nlp)

RE_PRODUCT = re.compile(r'/display/(.+?)(?=/|$)')


def run(mongo_api: MongoAPI):
    # Load required tools and data
    training_data = mongo_api.get_all_documents(mongo_api.SCRAPED_DOCS)

    for i, data in enumerate(training_data):
        # Iterate through each sentence of the contents and populate KB
        product = RE_PRODUCT.search(data['_id']).group(1)
        for heading_list, sentences in MarkdownParser.unmarkdown(data['content'], data['heading'], product):
            yield (heading_list, [sent for sents in sentences for sent in nlp.sent_tokenize(sents)])
        yield (None, None)
