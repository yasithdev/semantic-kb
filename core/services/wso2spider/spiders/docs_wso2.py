# -*- coding: utf-8 -*-
import re

from bs4 import BeautifulSoup, Tag
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import Selector
from scrapy.spiders import Rule, CrawlSpider
from unicodedata import normalize


class DocsWso2Spider(CrawlSpider):
    name = 'docs.wso2'
    allowed_domains = ['docs.wso2.com']
    doc_urls = ['AM210', 'ApiCloud', 'EI611', 'EIP', 'IntegrationCloud', 'IS530', 'IdentityCloud', 'DAS310', 'IOTS310',
                'DeviceCloud']
    start_urls = [str('https://docs.wso2.com/display/' + p) for p in doc_urls]
    # declare xpath variables
    xpath_title = '//title//text()'
    xpath_h1 = '//h1[contains(@class,"with-breadcrumbs")]//text()'
    xpath_content = '//div[@class="wiki-content"]'
    # generate rules for matching the links that should be proceeded
    re_allowed = r'.*com\/display\/(%s).*' % '|'.join(doc_urls)
    rules = [Rule(LinkExtractor(allow=[re_allowed]), callback="parse_item", follow=True)]

    @staticmethod
    def markdown_format(tag: Tag, content: str):
        # empty content handling
        if content.strip() == '':
            return ''
        ls = ' ' if content[0] == ' ' else ''
        rs = ' ' if content[-1] == ' ' else ''
        # non-empty content handling
        _name = tag.name
        # If child is an <a> tag, append href
        if _name == 'a':
            _href = Tag.get(tag, "href")
            if _href is not None:
                if _href[0] == '/':
                    _href = 'https://docs.wso2.com%s' % _href
                # Only add href if its a doc link, and not a marker
                if not _href[0] == '#':
                    content = '%s[%s](%s)%s' % (ls, content.strip(), _href, rs)
        # If child is a heading tag, append #
        elif _name[0] == 'h':
            x = _name[1]
            if str(x).isdigit():
                x = int(x)
                c = ''
                for i in range(x):
                    c += '#'
                content = '%s%s %s' % (ls, c, content.lstrip())
        # If child is <strong>, emphasize markdown output
        elif _name == 'strong':
            content = '%s**%s**%s' % (ls, content.strip(), rs)
        # If child is an <li> tag, append *
        elif _name == 'li':
            content = '+ %s' % content.lstrip()
        return content

    @staticmethod
    def extract_recursive(tag: Tag, separator_tags: list = list([])) -> str:
        output_string = ''
        for child in tag.childGenerator():
            # ---
            # CONTAINER NODES
            # ---
            if isinstance(child, Tag):
                # ---
                # skip ignored classes
                # ---
                _class = Tag.get(child, "class")
                if _class is not None:
                    _className = ' '.join(_class)
                    if _className.find('code panel') != -1 or _className.find('expand-container') != -1:
                        continue
                # ---
                # DFT into node's children
                # ---
                _name = child.name
                # ---
                # skip pre-formatted elements
                # ---
                if _name == "pre":
                    continue
                # [IMPORTANT] append text to output in the Markdown Syntax
                output_string += DocsWso2Spider.markdown_format(child, DocsWso2Spider.extract_recursive(child, separator_tags))
                # Append newline if current tag in newline_tags list
                if _name in separator_tags:
                    output_string += '\n'
            # ---
            # TERMINAL NODES
            # ---
            else:
                text = str(child)
                if not text.strip().isspace():
                    output_string += text
                    # print(child.strip(), end='')
        return output_string

    @staticmethod
    def parse_item(response):
        # Assign variables
        _separator_tags = ['p', 'td', 'li', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7']
        selector = response.selector
        important_content = Selector.xpath(selector, DocsWso2Spider.xpath_content).extract_first()
        if important_content is None:
            return
        soup = BeautifulSoup(str(important_content).strip(), 'lxml')
        # [SCRAPE_RESULT Initialization]
        scrape_result = {
            '_id': str(response.url).split('?', 1)[0],
            'title': Selector.xpath(selector, DocsWso2Spider.xpath_title).extract_first(),
            'heading': ' '.join(
                [x.strip() for x in Selector.xpath(selector, DocsWso2Spider.xpath_h1).extract()]).strip(),
            'content': normalize('NFKD', DocsWso2Spider.extract_recursive(soup, _separator_tags)).encode('ASCII', 'ignore').decode('ASCII')
        }
        # if scrape_result contains anything, yield it
        if scrape_result['title'] is not None and scrape_result['content'] != '':
            yield scrape_result
