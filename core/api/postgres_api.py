import pg8000 as psql


class PostgresAPI:
    def __init__(self, debug: bool = False) -> None:
        super().__init__()
        self.conn = psql.connect(user="postgres", password="1234", database="postgres")
        self.cursor = self.conn.cursor()
        # initial configuration
        if debug:
            self.drop_schema()
            self.create_schema()

    def create_schema(self):
        cursor = self.conn.cursor()
        # Create Schema
        cursor.execute('''CREATE SCHEMA IF NOT EXISTS semantic_kb''')
        # Create Table for Entities
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_kb.entities (
            id SERIAL PRIMARY KEY,
            entity TEXT UNIQUE)''')
        # Create Table for Sentence Templates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_kb.sentences (
            id SERIAL PRIMARY KEY,
            sentence TEXT UNIQUE)''')
        # Create Table for Frames
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_kb.frames (
            sentence_id INTEGER REFERENCES semantic_kb.sentences(id),
            frame TEXT,
            UNIQUE(sentence_id, frame))''')
        # Create View for observing frames and sentences mapping to them
        cursor.execute('''
            CREATE VIEW semantic_kb.frame_view AS 
            SELECT frame, array_agg(sentence_id) sentence_ids FROM semantic_kb.frames GROUP BY frame ORDER BY frame ASC''')
        self.conn.commit()

    def drop_schema(self):
        cursor = self.conn.cursor()
        cursor.execute('''DROP SCHEMA IF EXISTS semantic_kb CASCADE''')
        self.conn.commit()

    def truncate_tables(self):
        self.cursor.execute('''
            TRUNCATE semantic_kb.entities, semantic_kb.sentences, semantic_kb.frames RESTART IDENTITY''')
        self.conn.commit()

    def insert_sentence(self, parametrized_sentence: tuple):
        sentence = parametrized_sentence[0]
        for i in range(len(parametrized_sentence[1])):
            entity = parametrized_sentence[1][i]
            # Insert each entity
            self.cursor.execute('''
                INSERT INTO semantic_kb.entities (entity) VALUES (%s) 
                ON CONFLICT (entity) DO UPDATE SET entity = EXCLUDED.entity
                RETURNING id''', [entity])
            # Update sentence with referential parameters to entity_id
            entity_id = self.cursor.fetchall()[0][0]
            sentence = sentence.replace('[#%d]' % i, '[@%d]' % entity_id)

        # Insert templated sentence
        self.cursor.execute('''
            INSERT INTO semantic_kb.sentences (sentence) VALUES (%s) ON CONFLICT (sentence) DO UPDATE 
            SET sentence = EXCLUDED.sentence RETURNING id''', [sentence])
        # Return (sentence_id, sentence) Tuple
        sentence_id = self.cursor.fetchall()[0][0]
        self.conn.commit()
        print('.')
        return sentence_id, sentence

    def insert_frames(self, sentence_id: str, frames: list):
        for frame in frames:
            self.cursor.execute('''
                INSERT INTO semantic_kb.frames (sentence_id, frame) VALUES (%s, %s)''', [sentence_id, frame])
        self.conn.commit()

    def query_sentences(self, entities: list, frames: list):
        frame_param = str(frames).replace('[', '').replace(']', '')
        self.cursor.execute('''
            SELECT DISTINCT sentence_id from semantic_kb.frames WHERE frame IN ({0}) 
            ORDER BY sentence_id ASC'''.format(frame_param))
        sentence_ids = self.cursor.fetchall()

        # TODO - Fix Method so that sentences having correct entities are returned in ascending order of sentence_id
        return ''

        for sentence_id in sentence_ids:
            self.cursor.execute('''
                WITH RECURSIVE
                tree_up(parent, child, depth) AS (
                  SELECT j.parent_id, j.child_id, -1 from semantic_kb.joins j WHERE j.child_id = {0}
                  UNION
                  SELECT j.parent_id, j.child_id, depth - 1 FROM tree_up tu 
                  INNER JOIN semantic_kb.joins j on j.child_id = parent
                ),
                tree_down(parent, child, depth) AS (
                  SELECT j.parent_id, j.child_id, 1 from semantic_kb.joins j WHERE j.parent_id = {0}
                  UNION
                  SELECT j.parent_id, j.child_id, depth + 1 FROM tree_down td 
                  INNER JOIN semantic_kb.joins j on j.parent_id = child
                )
                SELECT DISTINCT ids.id, e1.entity, r.relation, e2.entity, ids.depth FROM (
                SELECT parent AS id, depth FROM tree_up UNION VALUES({0}, 0) UNION SELECT child AS id, depth FROM tree_down) AS ids
                INNER JOIN semantic_kb.triples t ON ids.id = t.id
                INNER JOIN semantic_kb.entities e1 ON e1.id = t.entity_1
                INNER JOIN semantic_kb.entities e2 ON e2.id = t.entity_2
                INNER JOIN semantic_kb.relations r ON r.id = t.relation
                ORDER BY ids.depth ASC
            '''.format(id)
                                )
            sentence_ids = self.cursor.fetchall()
            sentence = (' '.join([' '.join(x[1:-2]) for x in sentence_ids] + [sentence_ids[-1][-2]]) + '.').replace(
                '# ', '').replace(' #', '').strip()
            yield sentence

    def get_all_sentences(self):
        self.cursor.execute('SELECT id, sentence FROM semantic_kb.sentences')
        return self.cursor.fetchall()
