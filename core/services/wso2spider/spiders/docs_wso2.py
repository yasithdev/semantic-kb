# -*- coding: utf-8 -*-
import re

from scrapy.linkextractors import LinkExtractor
from scrapy.selector import Selector
from scrapy.spiders import Rule, CrawlSpider
from tomd import Tomd

class DocsWso2Spider(CrawlSpider):
    name = 'docs.wso2'
    allowed_domains = ['docs.wso2.com']
    doc_urls = ['AM210', 'ApiCloud', 'EI611', 'EIP', 'IntegrationCloud', 'IS530', 'IdentityCloud', 'DAS310', 'IOTS310',
                'DeviceCloud', 'ESB500']
    start_urls = [str('https://docs.wso2.com/display/' + p) for p in doc_urls]
    # xpath variables
    xpath_title = '//title//text()'
    xpath_h1 = '//h1[contains(@class,"with-breadcrumbs")]//text()'
    xpath_content = '//div[@class="wiki-content"]'
    # generate regex for matching the links that should be proceeded
    re_clean = re.compile(r'><')
    re_tags = re.compile(r'(<(?!\/).+?\/?>)|(<\/[\w\d\s]+?>)')
    re_newline = re.compile(r'(\n\s*){2,}')
    re_space = re.compile(r'(\s){2,}')
    re_allowed = r'.*com\/display\/(%s).*' % '|'.join(doc_urls)
    rules = [Rule(LinkExtractor(allow=[re_allowed]), callback="parse_item", follow=True)]

    @staticmethod
    def parse_item(response):
        selector = response.selector
        # [SCRAPE_RESULT Initialization]
        scrape_result = {
            '_id': str(response.url).split('?', 1)[0],
            'title': Selector.xpath(selector, DocsWso2Spider.xpath_title).extract_first(),
            'heading': ' '.join([x.strip() for x in Selector.xpath(selector, DocsWso2Spider.xpath_h1).extract()]).strip(),
            'content': '',
        }
        important_content = Selector.xpath(selector, DocsWso2Spider.xpath_content).extract_first()
        # process content
        content = DocsWso2Spider.re_clean.sub('>\n<', str(important_content))
        markdown = Tomd(content).markdown
        markdown = DocsWso2Spider.re_tags.sub('\n', markdown)
        markdown = DocsWso2Spider.re_newline.sub('\n', markdown)
        markdown = DocsWso2Spider.re_space.sub(' ', markdown)
        markdown = markdown.strip()
        # assign content to [SCRAPE_RESULT]
        scrape_result['content'] = markdown
        # if scrape_result contains anything, yield it
        if scrape_result['title'] is not None and scrape_result['content'] != '':
            print(scrape_result)
            yield scrape_result
