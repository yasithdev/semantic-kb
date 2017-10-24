from socket import socket


class StanfordAPI:
    SPLIT_CHAR = '__'

    def __init__(self, port: int = 6000, buffer: int = 4096) -> None:
        super().__init__()
        self.host = '127.0.0.1'
        self.port = port
        self.buffer = buffer

    def pos_tag(self, message: str) -> next:
        with socket() as s:
            s.connect((self.host, self.port))
            s.send(message.strip().encode('ascii', 'ignore') + b'\r' + b'\n')
            result = b''
            while True:
                data = s.recv(self.buffer)
                if data == b'':
                    break
                else:
                    result += data
        for x in str(result, 'ascii', 'ignore').strip().split():
            yield tuple(x.rsplit(self.SPLIT_CHAR, 1))
