import socket


class Network:

    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host, self.port = "10.56.216.85", 5555
        self.id = self.connect()

    def connect(self):
        self.client.connect((self.host, self.port))
        return self.client.recv(2048).decode()

    def send(self, data):
        try:
            self.client.send(str.encode(data))
            reply = self.client.recv(2048).decode()
            return reply
        except socket.error as e:
            return str(e)
