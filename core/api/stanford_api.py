import socket


class StanfordAPI:
    def __init__(self, host: str = socket.gethostname(), port: int = 5000, buffer: int = 4096) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.buffer = buffer

    def pos_tag(self, message: str):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP) as s:
            s.connect((self.host, self.port))
            s.send(message.strip().encode('ascii') + b'\n')
            data = s.recv(self.buffer)
        return data
