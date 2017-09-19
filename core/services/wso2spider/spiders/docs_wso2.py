# -*- coding: utf-8 -*-
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import Rule, CrawlSpider


class DocsWso2Spider(CrawlSpider):
    name = 'docs.wso2'
    allowed_domains = ['docs.wso2.com']
    # All WSO2 Documentation URLs (Without PaaS)
    doc_urls = ['AM210', 'ApiCloud', 'EI611', 'EIP', 'IntegrationCloud', 'IS530', 'IdentityCloud', 'DAS310', 'IOTS310',
                'DeviceCloud', 'ESB500']
    start_urls = [str('https://docs.wso2.com/display/' + p) for p in doc_urls]
    # generate regex for matching the links that should be proceeded
    allow_regex = r'.*com\/display\/(%s).*' % '|'.join(doc_urls)
    rules = [Rule(LinkExtractor(allow=[allow_regex]), callback="parse_item", follow=True)]

    @staticmethod
    def parse_item(response):
        scrape_result = {
            '_id': str(response.url).split('?', 1)[0],
            'title': response.css('title::text').extract_first(),
            'content': []
        }
        main_heading = response.css('h1.with-breadcrumbs > a *::text').extract_first()
        # scrape all possible content which can have text
        scraped_contents = response.css(
            '.wiki-content h2, .wiki-content h3, .wiki-content h4, .wiki-content h5, .wiki-content li, .wiki-content td, .wiki-content p, .wiki-content a')
        scraped_contents.extract()

        # initiate result item with the subtitle if its found, or with blank heading
        if main_heading is not None:
            result_item = {'heading': main_heading, 'text': []}
        else:
            result_item = {'heading': '', 'text': []}

        def try_add_result_item():
            if result_item['heading'] != '' or len(result_item['text']) > 0:
                scrape_result['content'] += [result_item]

        # LOGIC - flatten and assign all result_items into scrape_result content as a list of {heading, text}
        ignore_set = set([])
        for content in scraped_contents:
            _heading = content.css('h2 *::text, h3 *::text, h4 *::text, h5 *::text').extract_first()
            if _heading is not None:
                # add current result_item to scrape_result content if it has some content
                try_add_result_item()
                # initialize result_item
                result_item = {'heading': _heading, 'text': []}
            else:
                # get list of non-blank text matches
                c = [x.strip() for x in content.css('*::text').extract() if x.strip() != '']
                if content.css('td, li').extract_first() is not None:
                    if len(c) > 0:
                        result_item['text'] += ['|'] + c
                    ignore_set = ignore_set.union(set(content.css('a::text, p::text').extract()))
                else:
                    temp_set = set(content.css('a::text, p::text').extract())
                    if len(temp_set.intersection(ignore_set)) > 0:
                        ignore_set = ignore_set.difference(temp_set)
                        continue
                    result_item['text'] += c

        # add final result_item to scrape_result content if it has some content
        try_add_result_item()

        # if scrape_result contains anything, yield it
        if scrape_result['title'] is not None and len(scrape_result['content']) > 0:
            yield scrape_result
