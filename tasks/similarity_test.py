from core.api import PostgresAPI
from core.parsers import TextParser

entities = PostgresAPI().get_all_entities()
textParser = TextParser()

def run_test():
    for i in range(len(entities)):
        for j in range(i + 1, len(entities)):
            similarity = textParser.calculate_similarity(entities[i][1], entities[j][1])
            if similarity > 0.925:
                print('%s\t%s\t->%f' % (entities[i][1], entities[j][1], similarity))

if __name__ == '__main__':
    run_test()