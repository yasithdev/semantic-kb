import re


class MarkdownParser:
    @staticmethod
    def unmarkdown(input_text: list, main_heading: str) -> next:
        """
    convert markdown to headings and text
        :param input_text:
        :param main_heading:
        :return:
        """
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
        heading_list = [main_heading]
        content = []

        for line in input_text:
            # if line is heading, update heading_list appropriately
            h = re_h.findall(line)
            if len(h) > 0:
                if len(content) > 0:
                    yield heading_list, content
                    content = []
                h = h.pop()
                l, t = (len(h[0]), h[1])
                # truncate heading_list if current heading level is lower
                if len(heading_list) >= l:
                    heading_list = heading_list[:l - 1]
                heading_list.append(un_md(t))
            # if not, parse markdown text as plain text and return with heading hierarchy
            else:
                content.append(un_md(line))
        # yield final content if any exists
        if len(content) > 0:
            yield heading_list, content
