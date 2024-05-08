import socket
import threading
import traceback
import os
from scripts.socket.server import ClientDisconnectException

FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!leave"
os.system("")  # Enable ANSI escape characters in terminal.

class ChatClient:
	def __init__(self, ip="", port=5050, nickname="Default_Client"):
		self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server_ip = ""
		self.port = 5050
		self.nickname = nickname
		self.forced_close = False


	def receive(self):
		while True:
			try:
				message = self.client_socket.recv(1024).decode(FORMAT)
				if message == "NICKNAME":
					self.client_socket.send(self.nickname.encode(FORMAT))
				elif message == DISCONNECT_MESSAGE:
					self.forced_close = True
					raise ClientDisconnectException("You have disconnected from the server.")
				else:
					print(message)
			
			except ClientDisconnectException as cde:
				print(f"[DISCONNECTING]: {cde}")
				self.client_socket.close()
				break
			
			except Exception:
				print(f"[ERROR]: An unexpected error occurred!\n{traceback.format_exc()}")
				self.client_socket.close()
				break


	def send(self):
		while True:
			try:
				user_input = input().strip()
				if user_input == DISCONNECT_MESSAGE or self.forced_close:
					raise ClientDisconnectException("You have disconnected from the server.")
				
				message = f"{self.nickname}: {user_input}"
				print("\033[1A" + "\033[K", end='')  # Clear the submitted input line using ANSI escape characters.
				self.client_socket.send(message.encode(FORMAT))
			
			except ClientDisconnectException as cde:
				print(f"[DISCONNECTING]: {cde}")
				break

			except Exception:
				print(f"[ERROR]: An unexpected error occurred!\n{traceback.format_exc()}")
				self.client_socket.close()
				break


	def start(self):
		while True:
			connection_scope = input("Enter connection scope (\"Local\" or \"Public\"): ").strip().lower()
			if connection_scope != "local" and connection_scope != "public":
				print("[ERROR]: Please enter a valid scope (\"Local\" or \"Public\").")
			else:
				break

		while True:
			try:
				self.server_ip = input(F"Enter server's {connection_scope} IP: ").strip()
				self.port = int(input("Enter port number.\n(DEFAULT: '5050' for local connection, '5001' for public connection): ").strip())
				break
			
			except ValueError:
				print("[ERROR]: Port number must be an integer.")

		try:
			self.nickname = input("Choose a nickname: ")
			print(f"[CONNECTING]: Attempting to connect to Server ({self.server_ip} - port {self.port})...")
			self.client_socket.connect((self.server_ip, self.port))

			threading.Thread(target=self.receive).start()
			threading.Thread(target=self.send).start()
		
		except ConnectionRefusedError:
			print("[ERROR]: Connect failed, please check the server's IP and Port, then try again.")
			print(traceback.format_exc())
			self.client_socket.close()
		
		except (ConnectionResetError, ConnectionAbortedError):
			print("[ERROR]: Connection disrupted, possibly due to a forcibly closed session from the server side or network error.")
			print(traceback.format_exc())
			self.client_socket.close()


class GameClient(ChatClient):
	def __init__(self, entities, client_id, ip="", port=5050, nickname="Default_Client"):
		super().__init__(ip=ip, port=port, nickname=nickname)
		self.entities = entities
		self.client_id = client_id


	def receive(self):
		while True:
			try:
				message = self.client_socket.recv(1024).decode(FORMAT)
				if message == "NICKNAME":
					self.client_socket.send(self.nickname.encode(FORMAT))
				elif message == DISCONNECT_MESSAGE:
					self.forced_close = True
					raise ClientDisconnectException("You have disconnected from the server.")
			
			except ClientDisconnectException as cde:
				print(f"[DISCONNECTING]: {cde}")
				self.client_socket.close()
				break
			
			except Exception:
				print(f"[ERROR]: An unexpected error occurred!\n{traceback.format_exc()}")
				self.client_socket.close()
				break


	def send(self):
		while True:
			try:
				if self.forced_close:
					raise ClientDisconnectException("You have disconnected from the server.")
				
				message = [self.client_id]
				if self.client_id == "host":
					for entity in self.entities:
						message.append(f"{entity.id};{entity.last_movement[0]};{entity.last_movement[1]}")
					message = ",".join(message)
					print(message)
					self.client_socket.send(message.encode(FORMAT))
				
				else:
					message.append(f"{self.entities[0].id};{self.entities[0].last_movement[0]};{self.entities[0].last_movement[1]}")
					message = ",".join(message)
					print(message)
					self.client_socket.send(message.encode(FORMAT))
			
			except ClientDisconnectException as cde:
				print(f"[DISCONNECTING]: {cde}")
				break

			except Exception:
				print(f"[ERROR]: An unexpected error occurred!\n{traceback.format_exc()}")
				self.client_socket.close()
				break


	def start(self):
		try:
			print(f"[CONNECTING]: Attempting to connect to Server ({self.server_ip} - port {self.port})...")
			self.client_socket.connect((self.server_ip, self.port))

			threading.Thread(target=self.receive).start()
			threading.Thread(target=self.send).start()
		
		except ConnectionRefusedError:
			print("[ERROR]: Connect failed, please check the server's IP and Port, then try again.")
			print(traceback.format_exc())
			self.client_socket.close()
		
		except (ConnectionResetError, ConnectionAbortedError):
			print("[ERROR]: Connection disrupted, possibly due to a forcibly closed session from the server side or network error.")
			print(traceback.format_exc())
			self.client_socket.close()


if __name__ == "__main__":
	ChatClient().start()