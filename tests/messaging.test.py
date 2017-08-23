# THIS TESTS IF THE KB CAN BE PROPERLY QUERIED FOR DIFFERENT TYPES OF QUESTIONS
# GENERIC REQUIREMENT IS FOR NO EXCEPTIONS TO OCCUR AND TO GET RELEVANT ANSWERS
from core.api import PostgresAPI
from core.engine import MessageEngine

# Message engine object
db_api = PostgresAPI()
msgEngine = MessageEngine(db_api)

# Process and reply to messages
print('\nQ&A')
while True:
    message = input('Q > ').strip()
    if message == 'exit':
        break
    elif message == '':
        continue
    print('A > %s' % msgEngine.process(message))
