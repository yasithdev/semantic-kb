from socket import (socket, gethostname)


class StanfordAPI:
    def __init__(self, port: int = 5000, buffer: int = 4096) -> None:
        super().__init__()
        self.host = gethostname()
        self.port = port
        self.buffer = buffer

    def pos_tag(self, message: str):
        with socket() as s:
            s.connect((self.host, self.port))
            s.send(message.strip().encode('ascii') + b'\n')
            data = s.recv(self.buffer)
        return [tuple(x.rsplit('_', 1)) for x in str(data, 'ascii').strip().split()]
