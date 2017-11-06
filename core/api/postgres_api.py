import pg8000 as psql

ERROR_TOLERANCE = 5
MAX_ENTITY_LENGTH = 50
ROOT_NODE_NAME = 'ROOT'
SPLIT_CHAR = '__'
MIN_RESULT_COUNT = 3


def str_conv(iterable: list, start: str = '{', end: str = '}') -> str:
    result = "%s%s%s" % (start, '' if len(iterable) == 0 else str(iterable)[1:-1], end)
    return result


class PostgresAPI:
    def __init__(self, user="postgres", password="1234", database="semantic_kb", maintenance=False) -> None:
        super().__init__()
        self.maintenance = maintenance
        self.schema_name = "semantic_kb" if not self.maintenance else "maintenance"
        psql.paramstyle = 'qmark'
        self.conn = psql.connect(user=user, password=password, database=database)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''SET SEARCH_PATH TO {0}'''.format(self.schema_name))
        self.autocommit = False
        if self.maintenance:
            self.create_schema()
            self.conn.commit()

    def initialize_db(self):
        self.drop_schema()
        self.create_schema()
        self.conn.commit()

    def create_schema(self) -> None:
        cursor = self.conn.cursor()

        # Create Schema
        cursor.execute('''CREATE SCHEMA IF NOT EXISTS {0}'''.format(self.schema_name))

        # Create Table for Entities
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
              entity_id SERIAL PRIMARY KEY,
              entity TEXT UNIQUE
            )''')

        # Create Table for Headings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS headings (
              heading_id SERIAL PRIMARY KEY,
              heading TEXT,
              parent_id INTEGER REFERENCES headings(heading_id),
              UNIQUE(heading, parent_id)
            )''')

        # Create Table for Sentence Templates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sentences (
              sentence_id SERIAL PRIMARY KEY,
              sentence TEXT,
              dependencies TEXT[],
              heading_id INTEGER REFERENCES headings(heading_id) DEFAULT 1,
              UNIQUE(sentence, heading_id)
            )''')

        # Create Table for Normalizations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS normalizations (
              sentence_id SERIAL,
              entity_id SERIAL
            )''')

        # Create Table for Frames
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS frames (
            frame TEXT PRIMARY KEY,
            sentence_ids INTEGER[] DEFAULT '{}'
            )''')

        # Add Fuzzy String match extensions for schema
        cursor.execute('''CREATE EXTENSION IF NOT EXISTS fuzzystrmatch SCHEMA semantic_kb''')

        # Add ROOT Record for Headings. Every heading maps to this (To avoid foreign key violations)
        cursor.execute('''SELECT EXISTS(SELECT heading_id FROM headings WHERE heading_id = 1)''')
        if not cursor.fetchone()[0]:
            cursor.execute('''
              INSERT INTO headings (heading, parent_id) 
              VALUES (?, NULL) 
              ON CONFLICT (heading_id) DO NOTHING ''', [ROOT_NODE_NAME])

        # Add Function to get heading hierarchy
        cursor.execute('''
            CREATE OR REPLACE FUNCTION get_hierarchy(id INT)
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
                  FROM headings AS H
                  WHERE H.heading_id = id
                  UNION DISTINCT
                  SELECT
                    H.heading_id,
                    H.heading,
                    H.parent_id,
                    HRF.index + 1
                  FROM headings H
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
                  FROM headings H
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
            CREATE OR REPLACE VIEW heading_content AS
              SELECT headings.heading_id, headings.heading, array_agg(sentences.sentence ORDER BY sentence_id ASC) AS content
              FROM (headings JOIN sentences USING (heading_id))
              GROUP BY headings.heading_id
        ''')

        # Commit the DDL
        if self.autocommit:
            self.conn.commit()

    def drop_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute('''DROP SCHEMA IF EXISTS {0} CASCADE'''.format(self.schema_name))
        if self.autocommit:
            self.conn.commit()

    def truncate_tables(self) -> None:
        self.cursor.execute('''
            TRUNCATE 
            normalizations, headings, entities, 
            sentences, frames, 
            RESTART IDENTITY''')
        if self.autocommit:
            self.conn.commit()

    def insert_heading(self, heading: str, parent_id: int = None) -> int:
        # Insert one heading along with its parent_id, and return the new heading_id
        self.cursor.execute('''
            INSERT INTO headings (heading, parent_id) 
            VALUES (?,?) 
            ON CONFLICT(heading, parent_id) DO UPDATE SET parent_id = EXCLUDED.parent_id
            RETURNING heading_id
        ''', [heading, parent_id if parent_id else 1])
        heading_id = self.cursor.fetchone()[0]
        if self.autocommit:
            self.conn.commit()
        return int(heading_id)

    def insert_headings(self, headings: list) -> int:
        current_parent = None
        for heading in headings:
            current_parent = self.insert_heading(heading, current_parent)
        if self.autocommit:
            self.conn.commit()
        return int(current_parent)

    def insert_sentence(self, sentence: str, entities: set, dependencies: set, heading_id: int = None) -> int:
        # Insert parametrized sentence
        self.cursor.execute('''
            INSERT INTO sentences (sentence, dependencies, heading_id) VALUES (?,?,?) 
            ON CONFLICT (sentence, heading_id) DO UPDATE SET sentence = EXCLUDED.sentence 
            RETURNING sentence_id''', [sentence, str_conv(list(dependencies)), heading_id])
        sentence_id = self.cursor.fetchone()[0]

        # Insert normalized entities into database, along with the normalization
        for entity in entities:
            self.cursor.execute('''
                INSERT INTO entities (entity) VALUES (?) 
                ON CONFLICT (entity) DO UPDATE SET entity = EXCLUDED.entity
                RETURNING entity_id
            ''', [entity])
            entity_id = self.cursor.fetchall()[0][0]
            # Insert normalization record to map normalization -> original string
            self.cursor.execute('''
                INSERT INTO normalizations(sentence_id, entity_id) VALUES (?,?)
            ''', [sentence_id, entity_id])
        if self.autocommit:
            self.conn.commit()
        print('.', end='', flush=True)
        return int(sentence_id)

    def insert_frames(self, sentence_id: str, frames: set) -> None:
        for frame in frames:
            self.cursor.execute('''
                INSERT INTO frames (frame, sentence_ids) VALUES (?,?) 
                ON CONFLICT (frame) DO UPDATE SET sentence_ids = frames.sentence_ids || EXCLUDED.sentence_ids
            ''', [frame, str_conv([sentence_id])])
        if self.autocommit:
            self.conn.commit()

    def get_heading_hierarchy(self, heading_id: int) -> list:
        self.cursor.execute('''
            SELECT heading_id, heading, index FROM get_hierarchy(?)
            ''', [heading_id])
        return self.cursor.fetchall()

    def get_sentences_by_id(self, sentence_ids: list) -> next:
        for sentence_id in sentence_ids:
            self.cursor.execute('''
              SELECT sentence_id, sentence FROM sentences 
              WHERE sentence_id = ?
            ''', [sentence_id])
            # get the sentence text and return the output as a list
            row = self.cursor.fetchone()
            if row is not None:
                yield (row[0], (tuple(str.rsplit(tag, SPLIT_CHAR, 1)) for tag in row[1].split()))

    def get_all_sentences(self) -> next:
        self.cursor.execute('SELECT sentence_id, sentence FROM sentences')
        for row in self.cursor.fetchall():
            yield (row[0], (tuple(str.rsplit(tag, SPLIT_CHAR, 1)) for tag in row[1].split()))

    def get_sentence_count(self) -> int:
        self.cursor.execute('SELECT count(sentence_id) FROM sentences')
        return self.cursor.fetchone()[0]

    def get_all_entities(self) -> tuple:
        self.cursor.execute('SELECT entity_id, entity FROM entities ORDER BY entity')
        return self.cursor.fetchall()

    def query_sentence_ids(self, entities: dict, frames: set) -> dict:
        """
        Accepts a set of entities, a set of frames, and a filtering algorithm to generate a set of sentence id groups
        that match all constraints

        :param entities: Dictionary containing the entity as key, and possible ngrams as the value (use them if needed)
        :param frames: Set of question frames
        :return: sets of potential sentence ids that could be the answer
        """
        n = max(len(x.split()) for x in entities)

        # Get the entity ids matching the input entities as a dict of entity --> its direct/fuzzy matches
        def get_matching_entity_ids(input_entities: dict, ngram_level: int) -> dict:
            entity_ids = {}
            q_string = '''
            SELECT 
              entity_id, 
              length(entity) entity_length,
              semantic_kb.levenshtein(entity, '{0}', 2, 1, 2) edit_distance
            FROM 
              entities
            WHERE
              (length(entity) BETWEEN length('{0}') AND {1})
            AND (
              entity LIKE '{0}%%' 
              OR entity LIKE '%%{0}' 
              OR semantic_kb.levenshtein(entity, '{0}', 2, 1, 2) < {2}
            ) 
            ORDER BY entity_length ASC, edit_distance ASC LIMIT 3
            '''
            for entity in input_entities:
                entity_ids[entity] = []
                # execute direct string match
                self.cursor.execute(q_string.format(entity, MAX_ENTITY_LENGTH, ERROR_TOLERANCE))
                # get set of rows and append to matching_entity_ids set
                entity_ids[entity] += [int(row[0]) for row in self.cursor.fetchall()]
                # go through all ngrams until some entity match occurs, then break
                if len(input_entities[entity]) < ngram_level:
                    continue
                for ngrams in input_entities[entity][0: len(input_entities[entity]) - ngram_level + 1]:
                    for ngram in ngrams:
                        self.cursor.execute(q_string.format(ngram, MAX_ENTITY_LENGTH, ERROR_TOLERANCE))
                        entity_ids[entity] += [int(row[0]) for row in self.cursor.fetchall()]
            return entity_ids

        # Get the sentence ids of the sentences containing the passed entity ids
        def get_entity_matching_sent_ids(input_entities: dict) -> dict:
            # If some input entities have no matches in KB, or no entities in input, return empty result
            if input_entities is None or len(input_entities) == 0:
                return {}
            # Only search for non-empty entities
            non_empty_entities = sorted(set(entity for entity in input_entities if len(input_entities[entity]) > 0))
            # If no non-empty entity matches found in database, return empty result
            if len(non_empty_entities) == 0:
                return {}
            # ------------------------------------------
            # --------------
            # PARAMS
            # Column parameter tells which column to return
            column_param = '({0}) AS M'.format(
                ' AND '.join(
                    'bool_or(E{0})'.format(x) for x in range(len(non_empty_entities))
                )
            )
            # Entity parameter returns what elements triggered the sentence
            entity_param = ', '.join(
                '(array_agg(entity_id) && ARRAY[{0}]) AS E{1}'.format(str(input_entities[entity])[1:-1], i)
                for i, entity in enumerate(non_empty_entities)
            )
            # Condition parameter filters results and return only matching results
            condition_param = ' OR '.join(
                'E{0} = TRUE'.format(x) for x in range(len(non_empty_entities))
            )
            # filter to give only relevant results
            filter_param = 'M = TRUE'
            # END OF PARAMS
            # ---------------------
            # ------------------------------------------
            # Execute the query using the params
            self.cursor.execute(
                '''
                SELECT heading_id, sentence_ids FROM (
                    SELECT heading_id, array_agg(sentence_id) sentence_ids, {0} FROM
                    (SELECT DISTINCT sentence_id, {1} FROM normalizations GROUP BY sentence_id) AS TEMP
                    NATURAL JOIN sentences
                    NATURAL JOIN headings
                    WHERE {2}
                    GROUP BY heading_id
                ) AS TBL
                WHERE {3}
                '''.format(column_param, entity_param, condition_param, filter_param)
            )
            # Return the matching sentence_ids grouped under each heading_id
            return {heading: sentence_ids for heading, sentence_ids in self.cursor.fetchall()}

        # Return if any element in sent_ids match any frame in input_frames
        def check_frame_match(sent_ids: set, input_frames: set) -> bool:
            if len(sent_ids) == 0 or len(input_frames) == 0:
                return False
            else:
                frame_param = str(input_frames)[1:-1]
                sent_param = str(sent_ids)[1:-1]
                # self.cursor.execute('''
                #     SELECT count(DISTINCT F.frame) FROM
                #       (SELECT DISTINCT frame, unnest(sentence_ids) AS sentence_id FROM frames) AS F
                #     WHERE
                #       F.frame IN ({0}) AND
                #       F.sentence_id IN ({1})
                # '''.format(frame_param, sent_param))
                self.cursor.execute('''
                    SELECT bool_or(sentence_ids && ARRAY[{0}]) AS has_match FROM frames WHERE frame IN ({1})
                    '''.format(sent_param, frame_param))
                result = self.cursor.fetchone()[0]
                return result

        # Get entity matching sentences, grouped under headings
        entity_ids_dict = {}
        h_grp_match_dict = {}

        # Step down ngram size until at least one heading group returned
        for i in range(n, 0, -1):
            entity_ids_dict = get_matching_entity_ids(entities, i)
            h_grp_match_dict = get_entity_matching_sent_ids(entity_ids_dict)
            if len(h_grp_match_dict) >= MIN_RESULT_COUNT:
                break

        # Print the loaded variables
        print('# Question Entities ----> %s' % len(entity_ids_dict))
        print('# Matched Entities  ----> %s' % sum(len(entity_ids_dict[x]) for x in entity_ids_dict))
        print('# Headings -------------> %s' % len(h_grp_match_dict))
        print('# Sentences ------------> %s' % sum(len(h_grp_match_dict[x]) for x in h_grp_match_dict))

        if len(frames) == 0:
            return h_grp_match_dict
        else:
            # Filter out results that does not contain any input frames.
            # TODO check if best way is to check for existence of ANY frame match, or ALL matches
            fil_h_grp_match_dict = {
                heading: h_grp_match_dict[heading]
                for heading in h_grp_match_dict
                if check_frame_match(set(h_grp_match_dict[heading]), frames)
            }
            print('# Filtered Sentences --------> %s' % sum(len(fil_h_grp_match_dict[x]) for x in fil_h_grp_match_dict))
            return fil_h_grp_match_dict

    def get_heading_info_by_ids(self, heading_ids: list) -> dict:
        if heading_ids is None or len(heading_ids) == 0:
            return {}
        h_id_param = str(sorted(heading_ids))[1:-1]
        self.cursor.execute('''
          SELECT
            H.heading_id,
            H.heading,
            MIN(sentence_id) first_sentence_id,
            MAX(sentence_id) last_sentence_id
          FROM headings as H
          NATURAL JOIN sentences as S
          WHERE heading_id IN ({0})
          GROUP BY heading_id
        '''.format(h_id_param))
        print('Heading info returned...')
        return {heading_id: (heading, min_id, max_id) for heading_id, heading, min_id, max_id in self.cursor.fetchall()}

    def get_heading_content_by_id(self, heading_id: int) -> dict:
        self.cursor.execute('''
          SELECT heading_id, heading, content FROM heading_content
          WHERE heading_id = ?
        ''', [heading_id])
        row = self.cursor.fetchone()
        if row is None:
            return {}
        else:
            return {
                'heading_id': row[0],
                'heading': row[1],
                'content': ((tuple(str.rsplit(tag, SPLIT_CHAR, 1)) for tag in sent.split()) for sent in row[2])
            }

    def commit(self):
        if self.maintenance:
            self.cursor.execute('DROP SCHEMA IF EXISTS semantic_kb CASCADE')
            self.cursor.execute('ALTER SCHEMA maintenance RENAME TO semantic_kb')
            self.cursor.execute('''CREATE EXTENSION IF NOT EXISTS fuzzystrmatch SCHEMA semantic_kb''')
            self.create_schema()
        self.conn.commit()
