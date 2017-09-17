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
        scrape_result = {
            '_id': str(response.url).split('?',1)[0],
            'title': response.css('title::text').extract_first(),
            'content': []
        }
        main_heading = response.css('h1.with-breadcrumbs > a *::text').extract_first()
        scraped_contents = response.css('div.wiki-content h2, div.wiki-content h3, div.wiki-content h4, div.wiki-content h5, div.wiki-content p, div.wiki-content a')
        scraped_contents.extract()

        # initiate result item with the subtitle if its found, or with blank heading
        if main_heading is not None:
            result_item = {'heading': main_heading, 'text': []}
        else:
            result_item = {'heading': '', 'text': []}

        def try_add_result_item():
            if result_item['heading'] != '' or len(result_item['text']) > 0:
                scrape_result['content'] = scrape_result['content'] + [result_item]

        # LOGIC - flatten and assign all result_items into scrape_result content as a list of {heading, text}
        for content in scraped_contents:
            _heading = content.css('h2 *::text, h3 *::text, h4 *::text, h5 *::text').extract_first()
            if _heading is not None:
                # add current result_item to scrape_result content if it has some content
                try_add_result_item()
                # initialize result_item
                result_item = {'heading': _heading, 'text': []}
            else:
                result_item['text'] = result_item['text'] + content.css('p *::text, a *::text').extract()

        # add final result_item to scrape_result content if it has some content
        try_add_result_item()

        # if scrape_result contains anything, yield it
        if scrape_result['title'] is not None and len(scrape_result['content']) > 0:
            yield scrape_result

        # check for potential links to other pages, and follow them
        links = response.css('body a::attr(href)').extract()
        for link in links:
            # Ignore page history and other results
            if str(link).find('pages/') != -1:
                continue
            # Crawl all pages within the product space
            if self.match_regex.search(link) is not None:
                yield response.follow(link, callback=self.parse)
