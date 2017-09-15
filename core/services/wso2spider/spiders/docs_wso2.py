# -*- coding: utf-8 -*-
import re

import scrapy


class DocsWso2Spider(scrapy.Spider):
    name = 'docs.wso2'
    allowed_domains = ['docs.wso2.com']
    # All WSO2 Documentation URLs (Without PaaS)
    doc_urls = ['AM210', 'ApiCloud', 'EI611', 'EIP', 'IntegrationCloud', 'IS530', 'IdentityCloud', 'DAS310', 'IOTS310',
                'DeviceCloud', 'ESB500']
    start_urls = [str('https://docs.wso2.com/display/' + p) for p in doc_urls]
    # generate regex for matching the links that should be proceeded
    match_regex = re.compile(r'display\/(%s)' % '|'.join(doc_urls))

    def parse(self, response):
        result = {
            'title': response.css('title::text').extract_first(),
            'content': response.css('div.wiki-content p::text, div.wiki-content a::text').extract()
        }
        # yield the result if content is found
        if result['title'] is not None and len(result['content']) > 0:
            yield result
        # check for potential links to other pages, and follow them
        links = response.css('body a::attr(href)').extract()
        for link in links:
            # Ignore page history and other results
            if str(link).find('pages/') != -1:
                continue
            # Crawl all pages within the product space
            if self.match_regex.search(link) is not None:
                yield response.follow(link, callback=self.parse)
