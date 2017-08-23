import pg8000 as psql


class PostgresAPI:
    def __init__(self, debug: bool = False) -> None:
        super().__init__()
        self.conn = psql.connect(user="postgres", password="1234", database="postgres")
        self.cursor = self.conn.cursor()
        # initial configuration
        if debug:
            self.drop_tables()
            self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Create Schema
        cursor.execute('''CREATE SCHEMA IF NOT EXISTS semantic_kb''')
        # Insert Entities
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_kb.entities (
            id SERIAL PRIMARY KEY,
            entity TEXT UNIQUE)''')
        # Insert Relations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_kb.relations (
            id SERIAL PRIMARY KEY,
            relation TEXT UNIQUE)''')
        # Insert Triples
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_kb.triples (
            id SERIAL PRIMARY KEY,
            entity_1 SERIAL REFERENCES semantic_kb.entities,
            relation SERIAL REFERENCES semantic_kb.relations,
            entity_2 SERIAL REFERENCES semantic_kb.entities,
            UNIQUE (entity_1, relation, entity_2))''')
        # Insert Joins
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_kb.joins (
            parent_id SERIAL,
            child_id SERIAL,
            UNIQUE(parent_id, child_id))''')
        # Inserts on
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_kb.frames (
            frame_id VARCHAR(45),
            row_id INTEGER)''')

        cursor.execute('''
            CREATE VIEW semantic_kb.frame_view AS 
            SELECT frame_id, array_agg(row_id) relations FROM semantic_kb.frames GROUP BY frame_id''')
        self.conn.commit()

    def drop_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''DROP SCHEMA IF EXISTS semantic_kb CASCADE''')
        self.conn.commit()

    def truncate_tables(self):
        self.cursor.execute(
            'TRUNCATE semantic_kb.triples, semantic_kb.entities, semantic_kb.relations, semantic_kb.joins, '
            'semantic_kb.frames RESTART IDENTITY')
        self.conn.commit()

    def insert_triple_set(self, triple_set: tuple, context: str):
        previous = None
        for triple in triple_set:
            # sanitize
            triple = [x.strip() for x in triple]
            print('.', end=' ')

            # Insert entity 1
            self.cursor.execute('''
                INSERT INTO semantic_kb.entities (entity) VALUES (%s) ON CONFLICT (entity) DO UPDATE 
                SET entity = EXCLUDED.entity RETURNING id''', [triple[0]])
            entity_1_id = str(list(self.cursor.fetchall())[0][0])

            # Insert entity 2
            self.cursor.execute('''
                INSERT INTO semantic_kb.entities (entity) VALUES (%s) ON CONFLICT (entity) DO UPDATE 
                SET entity = EXCLUDED.entity RETURNING id''', [triple[2]])
            entity_2_id = str(list(self.cursor.fetchall())[0][0])

            # Insert relation
            self.cursor.execute('''
                INSERT INTO semantic_kb.relations (relation) VALUES (%s) ON CONFLICT (relation) DO UPDATE
                SET relation = EXCLUDED.relation RETURNING id''', [triple[1]])
            relation_id = str(list(self.cursor.fetchall())[0][0])

            # Insert triple
            self.cursor.execute('''
                INSERT INTO semantic_kb.triples (entity_1, relation, entity_2) VALUES (%s, %s, %s) 
                ON CONFLICT (entity_1, relation, entity_2) DO UPDATE SET entity_1 = EXCLUDED.entity_1 
                RETURNING id''', [entity_1_id, relation_id, entity_2_id])
            triple_id = self.cursor.fetchall()

            # Insert join if available
            if previous is not None:
                self.cursor.execute('''
                    INSERT INTO semantic_kb.joins (parent_id, child_id) VALUES (%s, %s) ON CONFLICT DO NOTHING''',
                                    [previous, triple_id[0][0]])

            previous = triple_id[0][0]
            self.conn.commit()

    def __query_by_id(self, id: int):
        self.cursor.execute('''
            SELECT e1.entity, r.relation, e2.entity, j.child_id FROM semantic_kb.triples t
            INNER JOIN semantic_kb.entities e1 ON e1.id = t.entity_1
            INNER JOIN semantic_kb.entities e2 ON e2.id = t.entity_2
            INNER JOIN semantic_kb.relations r ON r.id = t.relation
            LEFT JOIN semantic_kb.joins j ON j.parent_id = t.id
            WHERE t.id = %s ORDER BY j.child_id ASC''', [id])
        return self.cursor.fetchall()[0]

    def query_non_recursive(self, nouns: str, frames: list):
        frame_param = str(frames).replace('[', '').replace(']', '')
        self.cursor.execute('''
          SELECT e1.entity, r.relation, e2.entity, jc.child_id, jp.parent_id, t.id FROM semantic_kb.triples t
          INNER JOIN semantic_kb.entities e1 ON e1.id = t.entity_1
          INNER JOIN semantic_kb.entities e2 ON e2.id = t.entity_2
          INNER JOIN semantic_kb.relations r ON r.id = t.relation
          LEFT JOIN semantic_kb.joins jc ON jc.parent_id = t.id
          LEFT JOIN semantic_kb.joins jp ON jp.child_id = t.id
          WHERE (e1.entity  ~~* {0} OR e2.entity ~~* {0}) AND r.id IN (SELECT DISTINCT row_id FROM semantic_kb.frames 
          WHERE frame_id IN ({1})) ORDER BY t.id, jc.child_id ASC'''.format('%s', frame_param),
                            ['%{0}%'.format(nouns), '%{0}%'.format(nouns)])
        results = self.cursor.fetchall()
        processed_set = set()
        for row in results:
            if row[5] not in processed_set:
                yield row
                processed_set.add(row[5])

            # Next and previous triples
            next_triple_id = row[3]
            prev_triple_id = row[4]

            result_triples = []

            while prev_triple_id is not None:
                # Load next triple and add it to processed list
                prev_triple = self.__query_by_id(prev_triple_id)
                # yield current triple if it's id not in processed list, and add it
                if prev_triple_id not in processed_set:
                    prev_triple.append(prev_triple_id)
                    result_triples = [prev_triple] + result_triples
                    processed_set.add(prev_triple_id)
                else:
                    input('lol!')
                # assign new next_triple_id
                prev_triple_id = prev_triple[4]

            while next_triple_id is not None:
                # Load next triple and add it to processed list
                next_triple = self.__query_by_id(next_triple_id)
                # yield current triple if it's id not in processed list, and add it
                if next_triple_id not in processed_set:
                    next_triple.append(next_triple_id)
                    result_triples += [next_triple]
                    processed_set.add(next_triple_id)
                # assign new next_triple_id
                else:
                    input('lol!')
                next_triple_id = next_triple[3]

            for triple in result_triples:
                yield triple

    def query_recursive(self, nouns: str, frames: list):
        frame_param = str(frames).replace('[', '').replace(']', '')
        self.cursor.execute('''
            SELECT t.id, j.child_id FROM semantic_kb.triples t
            INNER JOIN semantic_kb.entities e1 ON e1.id = t.entity_1
            INNER JOIN semantic_kb.entities e2 ON e2.id = t.entity_2
            LEFT JOIN semantic_kb.joins j ON j.parent_id = t.id
            WHERE (e1.entity  ~~* {0} OR e2.entity ~~* {0}) AND t.relation IN (
            SELECT DISTINCT row_id FROM semantic_kb.frames WHERE frame_id IN ({1})
            ) ORDER BY t.id ASC
        '''.format('%s', frame_param),['%{0}%'.format(nouns), '%{0}%'.format(nouns)])
        results = self.cursor.fetchall()

        for row in results:
            id = row[0]
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
            results = self.cursor.fetchall()
            sentence = (' '.join([' '.join(x[1:-2]) for x in results] + [results[-1][-2]]) + '.').replace('# ', '').replace(' #', '').strip()
            yield sentence













    def get_all_relations(self):
        self.cursor.execute('SELECT id, relation FROM semantic_kb.relations')
        return self.cursor.fetchall()

    def add_frames_relation(self, relation: str, frames: list):
        for frame in frames:
            self.cursor.execute('''
                INSERT INTO semantic_kb.frames (frame_id, row_id) VALUES (%s, %s)''', [frame, relation])
        self.conn.commit()
