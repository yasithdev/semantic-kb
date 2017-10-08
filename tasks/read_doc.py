import re

from core.api import MongoAPI
from core.parsers import (MarkdownParser, common)


def run(mongo_api: MongoAPI):
    # Load required tools and data
    training_data = mongo_api.get_all_documents(mongo_api.SCRAPED_DOCS)

    for i, data in enumerate(training_data):
        # Iterate through each sentence of the contents and populate KB
        product = re.findall(r'/display/(.+?)(?=/|$)', data['_id'])[0]
        parsed_doc = []
        for heading_list, sentences in MarkdownParser.unmarkdown(data['content'], data['heading'], product):
            flattened_sentences = []
            for sentence in sentences:
                flattened_sentences.extend(common.sent_tokenize(sentence))
            parsed_doc.append((heading_list, flattened_sentences))
        yield parsed_doc
