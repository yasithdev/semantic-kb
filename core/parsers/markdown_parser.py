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
    def unmarkdown(input_text: list, main_heading: str) -> next:
        """
    Converts markdown to headings and text. No nesting
        :param input_text:
        :param main_heading:
        :return:
        """
        heading_list = [main_heading]
        content = []

        for line in input_text:
            # if line is heading, update heading_list appropriately
            h = MarkdownParser.re_h.findall(line)
            if len(h) > 0:
                if len(content) > 0:
                    yield heading_list, content
                    content = []
                h = h.pop()
                l, t = (len(h[0]), h[1])
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


