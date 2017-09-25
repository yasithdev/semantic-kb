from datetime import datetime
from core.services import StanfordServer
from core import ToolSet
from core import common
import re

# data insertion as sentences and entities
def populate_kb(headings: list, sentences: list, tools: ToolSet):
    for sentence in sentences:
        print('%s : %s' % (' > '.join(headings), sentence))
        for parametrized_sentence in tools.text_parser.parametrize_text(sentence):
            sentence = str(parametrized_sentence[0])
            entity_dict = dict(parametrized_sentence[1])
            tools.postgres_api.insert_sentence(sentence, entity_dict)


def sentence_and_entity_extraction_test():
    # Load required tools and data
    tools = ToolSet()
    training_data = tools.mongo_api.get_all_documents()
    data_count = tools.mongo_api.get_document_count()
    start_time = datetime.now()

    # convert markdown to headings and text
    def unmarkdown(input_text: list, page_heading: str) -> next:
        # regex to pick up headings
        re_h = re.compile(r'(#+)\s(.*)')
        re_a = re.compile(r'\[(.+?)\]\([h/#].+?\)')
        re_md = re.compile(r'\*{2,}|\+\s|`<|`>')
        re_s = re.compile(r'\s{2,}')

        # method to strip off markdown tags [and (temporarily) generate spaces]
        def un_md(md: str) -> str:
            # keep only text from hyperlinks
            temp = re_a.sub(r'\1', md)
            # remove bracketed content
            temp = re_md.sub(' ', temp)
            # return with whitespaces sanitized
            return re_s.sub(' ', temp).strip()

        # parse down markdown into heading hierarchy and text
        heading_list = [page_heading]
        for line in input_text:
            # if line is heading, update heading_list appropriately
            h = re_h.findall(line)
            if len(h) > 0:
                h = h.pop()
                l, t = (len(h[0]), h[1])
                # truncate heading_list if current heading level is lower
                if len(heading_list) >= l:
                    heading_list = heading_list[:l-1]
                heading_list.append(un_md(t))
            # if not, parse markdown text as plain text and return with heading hierarchy
            else:
                yield heading_list, un_md(line)

    # populate the database with sentences and entities
    with StanfordServer():
        for i, data in enumerate(training_data):
            # Iterate through each sentence of the contents and populate KB
            print('URL: %s' % data['_id'], flush=True)
            for heading, text in unmarkdown(data['content'], data['heading']):
                populate_kb(heading, common.sent_tokenize(text), tools)
            print('\n%d of %d completed' % (i + 1, data_count))
    completion_time = datetime.now()
    print('Done! (time taken: %s seconds)' % (completion_time-start_time).seconds)

if __name__ == '__main__':
    sentence_and_entity_extraction_test()
