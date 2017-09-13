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

    def create_schema(self) -> None:
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

    def drop_schema(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute('''DROP SCHEMA IF EXISTS semantic_kb CASCADE''')
        self.conn.commit()

    def truncate_tables(self) -> None:
        self.cursor.execute('''
            TRUNCATE semantic_kb.entities, semantic_kb.sentences, semantic_kb.frames RESTART IDENTITY''')
        self.conn.commit()

    def insert_sentence(self, sentence: str, entity_dict: dict) -> int:
        # assign variables to sentence, entity_dict, and entities
        entities = entity_dict.keys()

        # insert each entity and update entity_dict with correct entity ids
        for entity in entities:
            # Insert entity
            self.cursor.execute('''
                INSERT INTO semantic_kb.entities (entity) VALUES (%S) 
                ON CONFLICT (entity) DO UPDATE SET entity = EXCLUDED.entity
                RETURNING id''', [entity])
            # Update entity_dict with correct entity id
            entity_dict[entity] = self.cursor.fetchall()[0][0]
            # Update sentence with the new entity id
            sentence = sentence.replace('(E:%s|@:0)' % entity, '(E:%s|@:%d)' % (entity, entity_dict[entity]))

        # Insert parametrized sentence
        self.cursor.execute('''
            INSERT INTO semantic_kb.sentences (sentence) VALUES (%S) ON CONFLICT (sentence) DO UPDATE 
            SET sentence = EXCLUDED.sentence RETURNING id''', [sentence])

        # return the sentence_id
        sentence_id = self.cursor.fetchall()[0][0]
        self.conn.commit()
        print('.', end='', flush=True)
        return int(sentence_id)

    def insert_frames(self, sentence_id: str, frames: set) -> None:
        for frame in frames:
            self.cursor.execute('''
                INSERT INTO semantic_kb.frames (sentence_id, frame) VALUES (%S, %S)''', [sentence_id, frame])
        self.conn.commit()

    def query_sentences(self, entities: set, frames: set) -> list:
        # Get the entity ids of the entities matching the input entities
        def get_matching_entity_ids(input_entities: set) -> set:
            for entity in input_entities:
                self.cursor.execute('''
                            SELECT DISTINCT id from semantic_kb.entities WHERE entity LIKE '%%{0}%%'
                            OR semantic_kb.levenshtein(entity, '{0}') <= 2'''.format(entity))
                return set([int(result[0]) for result in self.cursor.fetchall()])

        # Get the sentence ids of the sentences containing the passed entity ids
        def get_entity_matching_sent_ids(input_entity_ids: set) -> next:
            for id in input_entity_ids:
                self.cursor.execute('''SELECT DISTINCT id, sentence from semantic_kb.sentences 
                                    WHERE sentence LIKE '%%@:{0})%%';'''.format(id))
                results = self.cursor.fetchall()
                if results is None:
                    return set()
                for result in results:
                    yield int(result[0])

        # Get the sentence ids of the sentences matching the input frames
        def get_frame_matching_sent_ids(input_frames: set) -> set:
            if len(input_frames) == 0:
                return set([])
            else:
                frame_param = str(input_frames).replace('{', '').replace('}', '')
                input(frame_param)
                self.cursor.execute('''
                    SELECT DISTINCT sentence_id from semantic_kb.frames WHERE frame IN ({0})'''.format(frame_param))
                return set([int(result[0]) for result in self.cursor.fetchall()])

        # Actual query computation logic starts here
        entity_ids = get_matching_entity_ids(entities)
        entity_matching_sent_ids = set(get_entity_matching_sent_ids(entity_ids))
        frame_matching_sent_ids = get_frame_matching_sent_ids(frames)

        # Print the loaded variables
        print('Entity Ids: %s' % entity_ids)
        print('Entity-Matching sentence Ids: %s' % entity_matching_sent_ids)
        print('Frame-Matching sentence Ids: %s' % frame_matching_sent_ids)

        # TODO Check if the logic can be made better
        sent_ids_intersection = entity_matching_sent_ids.intersection(frame_matching_sent_ids)
        sent_ids_union = entity_matching_sent_ids.union(frame_matching_sent_ids)

        # Using the matching sentence ids, return the sentences in order of their Ids
        if len(sent_ids_intersection) != 0:
            matched_sent_ids = sent_ids_intersection
        else:
            matched_sent_ids = sent_ids_union

        if len(matched_sent_ids) == 0:
            # if no results found, return empty list
            return []
        else:
            sent_id_param = str(matched_sent_ids).replace('{', '').replace('}', '')
            self.cursor.execute('''
                        SELECT DISTINCT id, sentence from semantic_kb.sentences WHERE id IN ({0}) 
                        ORDER BY id ASC'''.format(sent_id_param))
            # get the sentence text and return the output as a list
            return [result[1] for result in self.cursor.fetchall()]

    def get_all_sentences(self) -> tuple:
        self.cursor.execute('SELECT id, sentence FROM semantic_kb.sentences')
        return self.cursor.fetchall()

    def get_all_entities(self) -> tuple:
        self.cursor.execute('SELECT id, entity FROM semantic_kb.entities ORDER BY entity')
        return self.cursor.fetchall()

    def get_all_frames(self) -> tuple:
        self.cursor.execute('SELECT frame, sentence_ids FROM semantic_kb.frame_view')
        return self.cursor.fetchall()
