from socket import (socket, gethostname)


class StanfordAPI:
    def __init__(self, port: int = 5000, buffer: int = 4096) -> None:
        super().__init__()
        self.host = gethostname()
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
            yield tuple(x.rsplit('_', 1))
