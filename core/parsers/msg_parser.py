from nltk import Tree, breadth_first


class MessageParser:
    @staticmethod
    def calculate_score(parsed_string: str) -> next:
        """
    Get an input text, break into sentences, pos-tag the sentence, and calculate a question score indicating how likely
    the sentence is a question
        :param parsed_string: input text
        :return: a float value between 0 an 1
        """

        def get_score(wh: bool, md: bool, qmark: bool) -> float:
            return float(wh + md + qmark) / 3

        qmark_tag = False
        wh_tag = False
        md_tag = False
        score = 0

        if '?' in parsed_string: qmark_tag = True

        tree = Tree.fromstring(parsed_string)
        i = 0
        for node in breadth_first(tree):
            if isinstance(node, Tree):
                i += 1
                # Check if the tokens in a sentence belong to a question or a statement
                t = node.label()
                if t[0] == 'W':
                    wh_tag = True
                if t[0] == 'M':
                    md_tag = True
                score += get_score(wh_tag, md_tag, qmark_tag)
            else:
                break
        return (score / i) if i > 0 else 0
