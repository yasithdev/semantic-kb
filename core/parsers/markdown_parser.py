import re


class MarkdownParser:
    # regex to pick up headings
    re_h = re.compile(r'(#+)\s(.*)')
    re_a = re.compile(r'\[(.+?)\]\([h/#].+?\)')
    re_md = re.compile(r'\*{2,}|\+\s|`<|`>')
    re_s = re.compile(r'\s{2,}')

    @staticmethod
    def __strip_markdown_tags(markdown: str) -> str:
        """
    strip off markdown tags [and (temporarily) generate spaces]
        :param markdown: input text with markdown tags
        :return:
        """
        # keep only text from hyperlinks
        temp = MarkdownParser.re_a.sub(r'\1', markdown)
        # remove bracketed content
        temp = MarkdownParser.re_md.sub(' ', temp)
        # return with whitespaces sanitized
        return MarkdownParser.re_s.sub(' ', temp).strip()

    @staticmethod
    def unmarkdown(input_text: list, page_headings: list, product: str) -> next:
        """
    Converts markdown to headings and text. No nesting
        :param product: Name of the WSO2 Product to which the content belongs to
        :param input_text:
        :param page_headings:
        :return:
        """
        headings = {0: product, 1: page_headings[-1], 2: None, 3: None, 4:None, 5:None, 6:None, 7:None}
        hl = 1
        content = []

        def generate_heading_list() -> list:
            return [headings[0]] + page_headings[:-1] + [headings[x] for x in range(1,8) if headings[x] is not None]

        for line in input_text:
            # if line is heading, update heading_list appropriately
            h = MarkdownParser.re_h.findall(line)
            # check if headings found
            if len(h) > 0:
                # yield current content and headings if exists
                if len(content) > 0:
                    yield generate_heading_list(), content
                    content = []
                # get first result from h
                h = h.pop()
                l, t = (len(h[0]), h[1])
                # truncate heading_list if current heading level is lower
                if hl >= l:
                    # clear heading details below current level
                    for x in range(l+1, hl+1):
                        headings[x] = None
                    # update current heading level
                    hl = l
                # update current heading
                headings[l] = MarkdownParser.__strip_markdown_tags(t)
            # if not, parse markdown text as plain text and return with heading hierarchy
            else:
                content.append(MarkdownParser.__strip_markdown_tags(line))
        # yield final content if any exists
        if len(content) > 0:
            yield generate_heading_list(), content

    @staticmethod
    def unmarkdown_nested(text: list, heading: str, current_level: int):
        """
    Converts markdown to a dictionary with nested headings and text
        :param current_level:
        :param text:
        :param heading:
        """
        content = []

        for i, line in enumerate(text):
            # if line is heading, update heading_list appropriately
            h = MarkdownParser.re_h.findall(line)
            h = h.pop()
            if len(h) > 0:
                l, t = (len(h[0]), h[1])

                if l > current_level:
                    MarkdownParser.unmarkdown_nested(text[i+1:], t, l)
                else:
                    return heading, content

                if len(content) > 0:
                    yield heading_list, content
                    content = []
                # truncate heading_list if current heading level is lower
                if len(heading_list) >= l:
                    heading_list = heading_list[:l - 1]
                heading_list.append(MarkdownParser.__strip_markdown_tags(t))
            # if not, parse markdown text as plain text and return with heading hierarchy
            else:
                content.append(MarkdownParser.__strip_markdown_tags(line))
        # yield final content if any exists
        if len(content) > 0:
            yield heading_list, content


