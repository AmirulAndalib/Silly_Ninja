import socket
import threading
import traceback
import time
import os


FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!leave"
MAX_CLIENT_COUNT = 4
os.system("")  # Enable ANSI escape characters in terminal.


class ClientDisconnectException(Exception):
	pass


class ChatClient:
	def __init__(self, ip="", port=5050, nickname="Default_Client"):
		self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server_ip = ip
		self.port = port
		self.nickname = nickname
		self.running = True


	def receive(self):
		while self.running:
			try:
				message = self.client_socket.recv(1024).decode(FORMAT)
				if message == "NICKNAME":
					self.client_socket.send(self.nickname.encode(FORMAT))
				elif message == DISCONNECT_MESSAGE:
					raise ClientDisconnectException("You have disconnected from the server.")
				else:
					print(message)
			
			except ClientDisconnectException as cde:
				self.running = False
				print(f"[DISCONNECTED]: {cde}")
				self.client_socket.close()
			
			except Exception:
				self.running = False
				print(f"[ERROR]: An unexpected error occurred!\n{traceback.format_exc()}")
				self.client_socket.close()


	def send(self):
		while self.running:
			try:
				user_input = input().strip()
				message = f"{self.nickname}: {user_input}"
				print("\033[1A" + "\033[K", end='')  # Clear the submitted input line using ANSI escape characters.
				self.client_socket.send(message.encode(FORMAT))
				
				if user_input == DISCONNECT_MESSAGE:
					raise ClientDisconnectException("Closing connection...")
			
			except ClientDisconnectException as cde:
				self.running = False
				print(f"[DISCONNECTING]: {cde}")
				self.client_socket.close()

			except Exception:
				self.running = False
				print(f"[ERROR]: An unexpected error occurred!\n{traceback.format_exc()}")
				self.client_socket.close()


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
	def __init__(self, entities, tilemap, client_id, ip="", port=5050, nickname="Default_Client", on_connected=None):
		super().__init__(ip=ip, port=port, nickname=nickname)
		self.entities = entities  # A list of entities to update.
		self.tilemap = tilemap
		self.client_id = client_id  # Host, Client1, Client2,...
		self.client_index = -1
		self.on_connected = on_connected


	def disconnect(self):
		self.running = False
		time.sleep(0.1)
		self.client_socket.send(DISCONNECT_MESSAGE.encode(FORMAT))
		self.client_socket.close()
		print(f"[DISCONNECTING]: You have disconnected from the server.")


	def receive(self):
		while self.running:
			try:
				message = self.client_socket.recv(1024).decode(FORMAT)

				if message == DISCONNECT_MESSAGE:
					raise ClientDisconnectException("You have disconnected from the server.")
				elif "CLIENT_INDEX" in message and self.on_connected is not None:
					self.client_index = int(message.split(":")[1])
					self.on_connected(self.client_id, self.nickname, self.client_index)
				elif message == "NICKNAME":
					self.client_socket.send(self.nickname.encode(FORMAT))
				elif message == "CLIENT_ID":
					self.client_socket.send(self.client_id.encoded(FORMAT))
				elif "NEW PLAYER JOINED" in message:
					player_infos = message.split(":")[1].split(",")  # [index, nickname, client_id]
					self.entities[int(player_infos[0])].initialize_client(player_infos[1], player_infos[2])
				elif "PLAYER LEFT" in message:
					player_index = int(message.split(":")[1])
					self.entities[player_index].unregister_client(player_index)
				else:
					message_segments = message.split(";")
					sender_id = message_segments[0]
					for movement in message_segments[1:]:
						infos = movement.split(",")
						for entity in self.entities.copy():
							# Only update other clients' players and enemies.
							if entity.id == infos[0]:
								# [player_ID, last_movement[0], last_movement[1]]
								if entity.type == "player" and entity.id != "main_player" and entity.last_movement != tuple(map(int, infos[1:])):
									entity.update(self.tilemap, movement=tuple(map(int, infos[1:])))
								# [enemy_ID, walking, is_death]
								elif entity.type == "enemy" and sender_id == "host" and entity.walking != 0:
									entity.update(self.tilemap, walking=int(infos[1]))
									if bool(infos[2]):
										self.entities.remove(entity)
								break
		
			except ClientDisconnectException as cde:
				self.running = False
				print(f"[DISCONNECTING]: {cde}")
				self.client_socket.close()
			
			except Exception:
				self.running = False
				print(f"[ERROR]: An unexpected error occurred!\n{traceback.format_exc()}")
				self.client_socket.close()


	def send(self):
		while self.running:
			try:
				message = [self.client_id]
				
				# Send info of both entity types if this is the host.
				# Otherwise only send info of the corresponding client's player.
				for entity in self.entities.copy():
					if entity.type == "player" and entity.id == "main_player":
						message.append(f"player_{self.client_index + 1},{entity.last_movement[0]},{entity.last_movement[1]}")
					elif entity.type == "enemy" and self.client_id == "host":
						message.append(f"{entity.id},{entity.walking},{entity.is_death}")

				message = ";".join(message)
				print(message)
				self.client_socket.send(message.encode(FORMAT))

			except Exception:
				self.running = False
				print(f"[ERROR]: An unexpected error occurred!\n{traceback.format_exc()}")
				self.client_socket.close()


	def start(self):
		try:
			print(f"[CONNECTING]: Attempting to connect to Server ({self.server_ip} - port {self.port})...")
			self.client_socket.connect((self.server_ip, self.port))

			threading.Thread(target=self.receive).start()
			threading.Thread(target=self.send).start()
			return True
		
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