# THIS TESTS IF THE KB CAN BE PROPERLY QUERIED FOR DIFFERENT TYPES OF QUESTIONS
# GENERIC REQUIREMENT IS FOR NO EXCEPTIONS TO OCCUR AND TO GET RELEVANT ANSWERS
from core.api import PostgresAPI
from core.engine import MessageEngine
from core.services import StanfordServer

# Message engine object
db_api = PostgresAPI()
msgEngine = MessageEngine(db_api)

def run_test():
    while True:
        message = input('Q > ').strip()
        if message == 'exit':
            break
        elif message == '':
            continue
        answer = '. '.join(msgEngine.process_message(message))
        print('A > %s' % answer + '.')

if __name__ == '__main__':
    try:
        # Assume Stanford Server is running, and try test
        run_test()
    except ConnectionRefusedError:
        print('ERROR - Stanford Server has not started')
        # Initialize Stanford Server and try test
        with StanfordServer():
            run_test()

