import threading
import socket
import requests
import time

from datetime import datetime
from scripts.game import on_client_connected, on_client_disconnected
from scripts.socket.client import ClientDisconnectException, MAX_CLIENT_COUNT

FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!leave"


class SocketServer:
	def __init__(self, ip, port):
		# Get the IP address of RadminVPN.
		self.ip = ip
		self.port = int(port)  # Internal port.

		self.clients = []
		self.nicknames = []
		self.running = True


	def shutdown(self):
		print(f"[SHUTTING DOWN]: Server is about to shut down, disconnect all clients.")
		# Close all connection to clients.
		for client in self.clients:
			client.send(DISCONNECT_MESSAGE.encode(FORMAT))
			client.close()

		self.running = False
		self.clients.clear()
		self.nicknames.clear()


	def client_count(self):
		return len(self.clients)


	def get_nickname_at(self, index):
		return self.nicknames[index]


	def get_public_ip(self):
		try:
			response = requests.get("https://httpbin.org/ip")
			if response.status_code == 200:
				response_json = response.json()
				return response_json["origin"]
			else:
				print(f"Failed to retrieve IP - Status Code: {response.status_code}")
		except Exception as e:
			print(f"An Error occurs: {e}")


	def broadcast(self, message):
		for client in self.clients:
			client.send(message.encode(FORMAT))


	# A method to handle each client, on each separated thread.
	def handle_client(self, client, address):
		while self.running:
			try:
				message = client.recv(1024).decode(FORMAT)
				if message.split(": ", 1)[1] == DISCONNECT_MESSAGE:
					raise ClientDisconnectException("Client disconnected.")
				else:
					self.broadcast(message)
			except Exception:
				index = self.clients.index(client)
				client.send(DISCONNECT_MESSAGE.encode(FORMAT))
				self.clients.remove(client)
				client.close()
				
				nickname = self.nicknames[index]
				print(f"[LEAVING]: {address} a.k.a \"{nickname}\" has left the chat.")
				self.broadcast(f"[LEAVING]: {nickname} has left the chat.")
				self.nicknames.remove(nickname)
				break


	def start_server(self):
		print("[GREETING]: Welcome to Socket with Python, stranger.")
		# print(f"[PUBLIC IP]: {self.get_public_ip()}")
		print("[STARTING]: Server is starting...")

		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
			server.bind((self.ip, self.port))
			print(f"[LISTENING]: Server is listening for connections on {self.ip} - port: {self.port}")
			server.listen()

			self.running = True
			while self.running:
				client, address = server.accept()
				now = datetime.now()

				if len(self.clients) < MAX_CLIENT_COUNT:
					print(f"[NEW CONNECTION INBOUND - {now: %B %d, %Y - %H:%M:%S}]: {address} connected.")

					# Send a keyword that asks the client to enter their nickname.
					client.send("NICKNAME".encode(FORMAT))
					nickname = client.recv(1024).decode(FORMAT)
					self.nicknames.append(nickname)
					self.clients.append(client)

					print(f"[JOINING]: {address} joined the chat as {nickname}.")
					self.broadcast(f"[JOINING]: {nickname} joined the chat!")
					client.send((f"[CONNECTED]: Welcome to the Chat Room, {nickname}!\n" +
								"[RECEIVING INPUT]: Now, you can enter messages and send them to other people.").encode(FORMAT))

					threading.Thread(target=self.handle_client, args=(client, address)).start()
				else:
					client.send(("[JOIN FAILED]: Connected successfully but the maximum number of clients has been reached. " +
								"Hence CAN NOT join the game.").encode(FORMAT))
					time.sleep(1)
					client.send(DISCONNECT_MESSAGE.encode(FORMAT))
					client.close()


class GameServer(SocketServer):
	def __init__(self, ip, port):
		super().__init__(ip, port)
		self.clients = {}


	def shutdown(self):
		print(f"[SHUTTING DOWN]: Server is about to shut down, disconnect all clients.")
		# Close all connection to clients.
		for client_id in self.clients:
			self.clients[client_id].send(DISCONNECT_MESSAGE.encode(FORMAT))
			self.clients[client_id].close()
			on_client_disconnected(list(self.clients.keys()).index(client_id))

		self.running = False
		self.clients.clear()
		self.nicknames.clear()


	def broadcast(self, sender_id, message):
		# Broadcast the message to all connected clients, except the sender.
		for client_id in self.clients:
			if client_id != sender_id:
				self.clients[client_id].send(message.encode(FORMAT))


	def handle_client(self, client, address):
		client_index = list(self.clients.values()).index(client)
		client_id = list(self.clients.keys())[client_index]
		while self.running:
			try:
				message = client.recv(1024).decode(FORMAT)
				if message == DISCONNECT_MESSAGE:
					raise ClientDisconnectException("Client disconnected.")
				else:
					self.broadcast(client_id, message)
			except Exception:
				#client.send(DISCONNECT_MESSAGE.encode(FORMAT))
				self.clients.pop(client_id)
				client.close()
				
				nickname = self.nicknames[client_index]
				print(f"[LEAVING]: {address} a.k.a \"{nickname}\" has left the game.")
				self.nicknames.remove(nickname)
				
				on_client_disconnected(client_index)
				self.broadcast(client_id, f"PLAYER LEFT:{client_index}")
				break


	def start_server(self):
		print("[GREETING]: Welcome to Socket with Python, stranger.")
		# print(f"[PUBLIC IP]: {self.get_public_ip()}")
		print("[STARTING]: Server is starting...")

		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
			server.bind((self.ip, self.port))
			print(f"[LISTENING]: Server is listening for connections on {self.ip} - port: {self.port}")
			server.listen()

			self.running = True
			while self.running:
				client, address = server.accept()
				now = datetime.now()

				if len(self.clients) < MAX_CLIENT_COUNT:
					print(f"[NEW CONNECTION INBOUND - {now: %B %d, %Y - %H:%M:%S}]: {address} connected.")

					# Send a keyword that asks the client to send their nickname and id.
					client.send("NICKNAME".encode(FORMAT))
					nickname = client.recv(1024).decode(FORMAT)
					client.send("CLIENT_ID".encode(FORMAT))
					client_id = client.recv(1024).decode(FORMAT)
					client_index = self.client_count() - 1
					client.send(f"CLIENT_INDEX:{client_index}".encode(FORMAT))

					self.nicknames.append(nickname)
					self.clients[client_id] = client

					print(f"[JOINING]: {address} joined the game as {nickname}.")
					on_client_connected(client_index, nickname, client_id)
					self.broadcast(client_id, f"NEW PLAYER JOINED:{client_index},{nickname},{client_id}")

					threading.Thread(target=self.handle_client, args=(client, address)).start()
				else:
					client.send(("[JOIN FAILED]: Connected successfully but the maximum number of clients has been reached. " +
								"Hence CAN NOT join the game.").encode(FORMAT))
					time.sleep(1)
					client.send(DISCONNECT_MESSAGE.encode(FORMAT))
					client.close()


if __name__ == "__main__":
	ip = socket.gethostbyname(socket.gethostname())
	port = 5050
	SocketServer(ip, port).start_server()