import pg8000 as psql

ERROR_TOLERANCE = 3


class PostgresAPI:
    def __init__(self, debug: bool = False) -> None:
        super().__init__()
        self.conn = psql.connect(user="postgres", password="1234", database="postgres")
        self.cursor = self.conn.cursor()
        # initial configuration
        if debug:
            self.drop_schema()
            self.create_schema()

    def create_schema(self) -> None:
        cursor = self.conn.cursor()

        # Create Schema
        cursor.execute('''CREATE SCHEMA IF NOT EXISTS semantic_kb''')

        # Create Table for Entities
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_kb.entities (
              entity_id SERIAL PRIMARY KEY,
              entity TEXT UNIQUE
            )''')

        # Create Table for Headings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_kb.headings (
              heading_id SERIAL PRIMARY KEY,
              heading TEXT,
              parent_id INTEGER REFERENCES semantic_kb.headings(heading_id),
              UNIQUE(heading, parent_id)
            )''')

        # Create Table for Sentence Templates
        # TODO Maintain UNIQUE for sentence and heading_id. Cannot do it atm since headings are not set
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_kb.sentences (
              sentence_id SERIAL PRIMARY KEY,
              sentence TEXT,
              heading_id INTEGER REFERENCES semantic_kb.headings(heading_id) DEFAULT 1
            )''')

        # Create Table for Normalizations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_kb.normalizations (
              sentence_id SERIAL,
              entity_id SERIAL,
              raw_entity TEXT NOT NULL
              )''')

        # Create Table for Frames
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS semantic_kb.frames (
            sentence_id INTEGER REFERENCES semantic_kb.sentences(sentence_id),
            frame TEXT,
            UNIQUE(sentence_id, frame))''')

        # Add Fuzzy String match extensions for semantic_kb
        cursor.execute('''CREATE EXTENSION fuzzystrmatch WITH SCHEMA semantic_kb''')

        # Add ROOT Record for Headings. Every heading maps to this (To avoid foreign key violations)
        # TODO try a better approach
        cursor.execute('''INSERT INTO semantic_kb.headings (heading, parent_id) VALUES ('ROOT', NULL)''')

        # Add Function to get heading hierarchy
        cursor.execute('''
            CREATE OR REPLACE FUNCTION semantic_kb.get_hierarchy(id INT)
              RETURNS TABLE(
                heading_id INTEGER,
                heading    TEXT,
                index      INTEGER
              ) AS
            $$ BEGIN
              RETURN QUERY
              WITH RECURSIVE
                  traverse_down(heading_id, heading, parent_id, index) AS (
                  SELECT
                    H.heading_id,
                    H.heading,
                    H.parent_id,
                    0
                  FROM semantic_kb.headings AS H
                  WHERE H.heading_id = id
                  UNION DISTINCT
                  SELECT
                    H.heading_id,
                    H.heading,
                    H.parent_id,
                    HRF.index + 1
                  FROM semantic_kb.headings H
                    JOIN traverse_down HRF ON H.parent_id = HRF.heading_id
                ),
                  traverse_both(heading_id, heading, parent_id, index) AS (
                  SELECT
                    H.heading_id,
                    H.heading,
                    H.parent_id,
                    H.index
                  FROM traverse_down H
                  UNION DISTINCT
                  SELECT
                    H.heading_id,
                    H.heading,
                    H.parent_id,
                    HRF.index - 1
                  FROM semantic_kb.headings H
                    JOIN traverse_both HRF ON H.heading_id = HRF.parent_id
                )
              SELECT
                TB.heading_id,
                TB.heading,
                TB.index
              FROM traverse_both TB
              ORDER BY index ASC, heading_id ASC;
            END; $$
            LANGUAGE plpgsql
        ''')

        # Create View for observing content under each heading
        self.cursor.execute('''
            CREATE OR REPLACE VIEW semantic_kb.heading_content AS 
            SELECT heading, string_agg(sentence, '. ') AS content FROM semantic_kb.sentences 
            JOIN semantic_kb.headings USING(heading_id)
            GROUP BY heading_id, heading
        ''')

        # Commit the DDL
        self.conn.commit()

    def drop_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute('''DROP SCHEMA IF EXISTS semantic_kb CASCADE''')
        self.conn.commit()

    def truncate_tables(self) -> None:
        self.cursor.execute('''
            TRUNCATE semantic_kb.normalizations, semantic_kb.headings, semantic_kb.entities, semantic_kb.sentences, semantic_kb.frames, RESTART IDENTITY''')
        self.conn.commit()

    def insert_heading(self, heading: str, parent_id: int = None) -> int:
        # Insert one heading along with its parent_id, and return the new heading_id
        self.cursor.execute('''
            INSERT INTO semantic_kb.headings (heading, parent_id) VALUES (%s, COALESCE(%s,1))
            ON CONFLICT(heading, parent_id) 
            DO UPDATE SET heading = EXCLUDED.heading, parent_id = EXCLUDED.parent_id
            RETURNING heading_id''',
                            [heading, parent_id])
        heading_id = self.cursor.fetchone()[0]
        self.conn.commit()
        return int(heading_id)

    def insert_headings(self, headings: list) -> int:
        current_parent = None
        for heading in headings:
            current_parent = self.insert_heading(heading, current_parent)
        return int(current_parent)

    def insert_sentence(self, sentence: str, entity_normalization: dict, heading_id: int = None) -> int:
        # Insert parametrized sentence
        self.cursor.execute('''
            INSERT INTO semantic_kb.sentences (sentence, heading_id) VALUES (%s, %s) RETURNING sentence_id''',
                            [sentence, heading_id]
                            )
        sentence_id = self.cursor.fetchone()[0]

        # Insert normalized entities into database, along with the normalization
        for entity in entity_normalization.keys():
            # ignore long entities (probably codes)
            if len(entity) >= 100:
                continue
            self.cursor.execute('''
                INSERT INTO semantic_kb.entities (entity) VALUES (%s) 
                ON CONFLICT (entity) DO UPDATE SET entity = EXCLUDED.entity
                RETURNING entity_id''', [entity_normalization[entity]])
            entity_id = self.cursor.fetchall()[0][0]
            # Insert normalization record to map normalization -> original string
            self.cursor.execute('''
                INSERT INTO semantic_kb.normalizations(sentence_id, entity_id, raw_entity) VALUES 
                (%s, %s, %s)''', [sentence_id, entity_id, entity])
        self.conn.commit()
        print('.', end='', flush=True)
        return int(sentence_id)

    def insert_frames(self, sentence_id: str, frames: set) -> None:
        for frame in frames:
            self.cursor.execute('''
                INSERT INTO semantic_kb.frames (sentence_id, frame) VALUES (%s, %s)''', [sentence_id, frame])
        self.conn.commit()

    def get_heading_hierarchy(self, heading_id: int) -> list:
        self.cursor.execute('''SELECT heading_id, heading, index from semantic_kb.get_hierarchy(%s)'''
        , [heading_id])
        return self.cursor.fetchall()

    def get_sentences_by_id(self, sentence_ids: list) -> next:
        for id in sentence_ids:
            self.cursor.execute('''
              SELECT DISTINCT S.sentence_id, S.sentence,
              (SELECT string_agg(GH.heading, ' > ') FROM semantic_kb.get_hierarchy(heading_id) GH
              WHERE GH.index <= 0) heading_hierarchy
              FROM semantic_kb.sentences S WHERE S.sentence_id=%s''', [id])
            # get the sentence text and return the output as a list
            result = self.cursor.fetchone()
            if result is not None:
                yield result

    def get_all_sentences(self) -> tuple:
        self.cursor.execute('SELECT sentence_id, sentence FROM semantic_kb.sentences')
        return self.cursor.fetchall()

    def get_sentence_count(self) -> int:
        self.cursor.execute('SELECT count(sentence_id) FROM semantic_kb.sentences')
        return self.cursor.fetchone()[0]

    def get_all_entities(self) -> tuple:
        self.cursor.execute('SELECT entity_id, entity FROM semantic_kb.entities ORDER BY entity')
        return self.cursor.fetchall()

    def query_sentence_ids(self, entities: set, frames: set) -> set:
        # Get the entity ids of the entities matching the input entities
        def get_matching_entity_ids(input_entities: set) -> set:
            matches = []
            for entity in input_entities:
                self.cursor.execute('''
                    SELECT DISTINCT entity_id, length(entity) from semantic_kb.entities WHERE length(entity) < 50
                    AND length(entity) >= length('{0}')
                    AND (
                      entity LIKE '{0}%%' 
                      OR entity LIKE '%%{0}' 
                      OR semantic_kb.levenshtein(entity, '{0}', 2, 1, 2) <= {1}
                    ) 
                    ORDER BY length(entity) LIMIT 15
                    '''.format(entity, ERROR_TOLERANCE))
                matches += [set([int(result[0]) for result in self.cursor.fetchall()])]
            # sort matches in ascending order of match lengths, and get the intersection
            matches = sorted(matches, key=len, reverse=True)
            r = set()
            critical_matches = []
            # linearly enumerate and generate minimum result set
            for x, e in enumerate(matches):
                if x == 0:
                    r = e
                    continue
                # try to assign intersection. if failed, add the results as critical matches
                isc = r.intersection(e)
                if len(isc) == 0:
                    critical_matches += e
                else:
                    r = isc

            # TODO In critical matches, get the most occurring matches and union them with r and return
            isc = r.intersection(critical_matches)
            return isc if len(isc) != 0 else r.union(critical_matches)

        # Get the sentence ids of the sentences containing the passed entity ids
        def get_entity_matching_sent_ids(input_entity_ids: set) -> set:
            if input_entity_ids is None or len(input_entity_ids) == 0:
                return set([])
            entity_param = str(input_entity_ids).replace('{', '').replace('}', '')
            self.cursor.execute('''SELECT DISTINCT sentence_id from semantic_kb.normalizations 
                                WHERE entity_id IN ({0})'''.format(entity_param))
            return set([int(result[0]) for result in self.cursor.fetchall()])

        # Get the sentence ids of the sentences matching the input frames
        def get_frame_matching_sent_ids(input_frames: set) -> set:
            if len(input_frames) == 0:
                return set([])
            else:
                frame_param = str(input_frames).replace('{', '').replace('}', '')
                self.cursor.execute('''
                    SELECT DISTINCT sentence_id from semantic_kb.frames WHERE frame IN ({0})'''.format(frame_param))
                return set([int(result[0]) for result in self.cursor.fetchall()])

        # Actual query computation logic starts here
        entity_ids = get_matching_entity_ids(entities)
        entity_matching_sent_ids = get_entity_matching_sent_ids(entity_ids)
        frame_matching_sent_ids = get_frame_matching_sent_ids(frames)

        # Print the loaded variables
        print('# Entity Ids: %s' % len(entity_ids))
        print('# Entity-Matching sentence Ids: %s' % len(entity_matching_sent_ids))
        print('# Frame-Matching sentence Ids: %s' % len(frame_matching_sent_ids))

        # TODO Check if the logic can be made better
        sent_ids_intersection = entity_matching_sent_ids.intersection(frame_matching_sent_ids)

        # Using the matching sentence ids, return the sentences in order of their Ids
        if len(sent_ids_intersection) > 0:
            # Option 1 - Intersection Exists. Gives most relevant results
            return sent_ids_intersection
        elif len(entity_matching_sent_ids) > 0:
            # Option 2 - No intersection. Gives results relevant to entity
            return entity_matching_sent_ids
        else:
            # Option 3 - No entity matching sentences. Return no results
            return set([])

    def group_sentences_by_heading(self, sentence_ids: set) -> list:
        if sentence_ids is None or len(sentence_ids) == 0:
            return []
        sentence_id_param = str(sentence_ids).replace('{', '').replace('}', '')
        self.cursor.execute('''
          SELECT 
            (SELECT string_agg(GH.heading, ' > ') FROM semantic_kb.get_hierarchy(heading_id) GH 
            WHERE GH.index <= 0) heading, 
            array_agg(sentence_id ORDER BY sentence_id ASC) FROM semantic_kb.sentences WHERE sentence_id IN (%s)
          GROUP BY heading_id
        ''' % sentence_id_param)
        return self.cursor.fetchall()
