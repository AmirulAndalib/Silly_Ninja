import pygame
import random
import sys
import os
import math
import time

from scripts.tilemap import Tilemap
from scripts.entities import Player, Enemy
from scripts.clouds import Clouds
from scripts.visual_effects import Particle, Spark
from scripts.animation import Animation
from scripts.utils import load_image, load_images, fade_out
from scripts.socket.client import GameClient, MAX_CLIENT_COUNT


class GameBase:
	def __init__(self, clock, screen, outline_display, normal_display):
		self.clock = clock
		self.screen = screen
		self.outline_display = outline_display  # Outline display
		self.normal_display = normal_display  # Normal display

		# Assets database for images, audio,...
		# Values are lists for multiple images.
		self.assets = {
			"clouds": load_images("clouds"),
			"decor": load_images("tiles/decor"),
			"grass": load_images("tiles/grass"),
			"large_decor": load_images("tiles/large_decor"),
			"stone": load_images("tiles/stone"),

			"player/idle": Animation(load_images("entities/player/idle"), image_duration=6),
			"player/run": Animation(load_images("entities/player/run"), image_duration=4),
			"player/jump": Animation(load_images("entities/player/jump")),
			"player/slide": Animation(load_images("entities/player/slide")),
			"player/wall_slide": Animation(load_images("entities/player/wall_slide")),

			"enemy/idle": Animation(load_images("entities/enemy/idle"), image_duration=6),
			"enemy/run": Animation(load_images("entities/enemy/run"), image_duration=4),
			
			"particle/leaf": Animation(load_images("particles/leaf"), image_duration=20, loop=False),
			"particle/dust": Animation(load_images("particles/dust"), image_duration=6, loop=False),
			
			"background": load_image("background.png"),
			"gun": load_image("gun.png"),
			"projectile": load_image("projectile.png")
		}

		self.sounds = {
			"ambience": pygame.mixer.Sound("assets/sfx/ambience.wav"),
			"dash": pygame.mixer.Sound("assets/sfx/dash.wav"),
			"hit": pygame.mixer.Sound("assets/sfx/hit.wav"),
			"jump": pygame.mixer.Sound("assets/sfx/jump.wav"),
			"shoot": pygame.mixer.Sound("assets/sfx/shoot.wav")
		}

		self.sounds["ambience"].set_volume(0.2)
		self.sounds["dash"].set_volume(0.35)
		self.sounds["hit"].set_volume(0.9)
		self.sounds["jump"].set_volume(0.6)
		self.sounds["shoot"].set_volume(0.45)

		self.clouds = Clouds(self.assets["clouds"], count=16)

		self.tilemap = Tilemap(self, 16)

		self.movement = [False, False]

		self.screenshake = 0

		self.level_id = 0


	def load_level(self, id):
		self.tilemap.load(f"assets/maps/{id}.json")
		self.leaf_spawners = []
		for tree in self.tilemap.extract([("large_decor", 2)], keep=True):
			self.leaf_spawners.append(pygame.Rect(tree.pos[0] + 4, tree.pos[1] + 4, 23, 13))

		self.particles = []
		self.projectiles = []
		self.sparks = []

		self.camera_scroll = [0, 0]
		self.dead = 0
		self.transition = -30


	def run(self):
		self.sounds["ambience"].play(-1)


	def render_terrain(self, render_scroll):
		# Spawn leaf particles.
		for rect in self.leaf_spawners:
			if random.random() * 49999 < rect.width * rect.height:
				pos = (rect.x + random.random() * rect.width, rect.y + random.random() * rect.height)
				velocity = [random.random() * 0.1 - 0.2, random.random() * 0.2 + 0.1]
				start_frame = random.randint(0, 17)
				self.particles.append(Particle(self, "leaf", pos, velocity, start_frame))

		# Render clouds.
		self.clouds.update()
		self.clouds.render(self.normal_display, offset=render_scroll)

		# Render the tilemap.
		self.tilemap.render(self.outline_display, offset=render_scroll)


	def render_effects(self, render_scroll):
		# Render sparks.
		for spark in self.sparks.copy():
			died = spark.update()
			spark.render(self.outline_display, offset=render_scroll)
			if died:
				self.sparks.remove(spark)

		# Render the outline for sprites.
		display_mask = pygame.mask.from_surface(self.outline_display)
		display_silhouette = display_mask.to_surface(setcolor=(0, 0, 0, 180), unsetcolor=(0, 0, 0, 0))
		for offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
			self.normal_display.blit(display_silhouette, offset)

		# Render particles and remove expired ones.
		for particle in self.particles.copy():
			died = particle.update()
			particle.render(self.outline_display, offset=render_scroll)
			if particle.type == "leaf":
				particle.pos[0] += math.sin(particle.animation.frame * 0.035) * (random.random() * 0.3 + 0.2)
			if died:
				self.particles.remove(particle)


	def handle_level_transition(self):
		# Render the level transition effect.
		if self.transition:
			transition_surf = pygame.Surface(self.outline_display.get_size())
			pygame.draw.circle(transition_surf, (255, 255, 255), (self.outline_display.get_width() // 2, self.outline_display.get_height() // 2), (30 - abs(self.transition)) * 8)
			transition_surf.set_colorkey((255, 255, 255))
			self.outline_display.blit(transition_surf, (0, 0))


# The list of player serves as a template for each client.
PLAYERS = [
	Player("player_1", None, (50, 50), (8, 15), id="player_1", client_id=""),
	Player("player_2", None, (50, 50), (8, 15), id="player_2", client_id=""),
	Player("player_3", None, (50, 50), (8, 15), id="player_3", client_id=""),
	Player("player_4", None, (50, 50), (8, 15), id="player_4", client_id="")
]
CLIENT_ORDER = 1
LEVEL_ID = 0


# Global functions to modify the template.
def on_client_connected(player_index, nickname, client_id):
	global PLAYERS, CLIENT_ORDER
	PLAYERS[player_index].initialize_client(nickname, client_id)
	CLIENT_ORDER = min(CLIENT_ORDER + 1, MAX_CLIENT_COUNT - 1)


def on_client_disconnected(player_index):
	global PLAYERS, CLIENT_ORDER
	PLAYERS[player_index].unregister_client(player_index)
	CLIENT_ORDER = max(CLIENT_ORDER - 1, 1)


class GameForHost(GameBase):
	def __init__(self, clock, screen, outline_display, normal_display, server, host_ip, port, nickname):
		super().__init__(clock, screen, outline_display, normal_display)
		self.server = server
		
		# First 4 elements are players.
		self.entities = PLAYERS.copy()
		for player in self.entities:
			player.game = self

		self.player_index = -1
		self.client = GameClient(self.entities, self.tilemap, "host", ip=host_ip, port=port, nickname=nickname, on_connected=self.on_connected)
		self.spawn_pos = [0, 0]


	def get_main_player(self):
		return self.entities[self.player_index]


	def respawn(self):
		self.get_main_player().pos = self.spawn_pos


	def on_connected(self, client_id, nickname, player_index):
		# Initialize the main player if the connection is made.
		self.player_index = player_index
		self.get_main_player().initialize_client(nickname, client_id=client_id, id="main_player")


	def load_level(self, id):
		super().load_level(id)
		enemy_count = 1
		for spawner in self.tilemap.extract([("spawners", 0), ("spawners", 1)]):
			if spawner.variant == 0:
				# Set the spawn position for all 4 players at once.
				self.spawn_pos = spawner.pos
				for i in range(4):
					self.entities[i].pos = self.spawn_pos
					self.entities[i].air_time = 0
			else:
				self.entities.append(Enemy(self, spawner.pos, (8, 15), id=f"enemy_{enemy_count}", client_id=self.client.client_id))
				enemy_count += 1


	def start_server(self, status_text, on_server_started=None):
		self.server.start_server()
		status_text.set_text("Starting LAN server...")
		time.sleep(5)
		if self.server.running and on_server_started is not None:
			status_text.set_text("Server started, creating lobby...")
			if self.client.start() and on_server_started is not None:
				time.sleep(2)
				on_server_started()
			else:
				status_text.set_text("[ERROR]: Failed to make connection, check IP and port.")
		else:
			status_text.set_text("[TIMED OUT]: Server failed to start, check IP and port.")


	def launch_session(self, status_text, connected_game_clients):
		status_text.set_text("Launching session...")
		time.sleep(3)
		for client in connected_game_clients:
			client.load_level(LEVEL_ID)


	def run(self):
		super().run()

		running = True
		while running:
			self.outline_display.fill((0, 0, 0, 0))
			self.normal_display.blit(self.assets["background"], (0, 0))

			self.screenshake = max(self.screenshake - 1, 0)

			# Handle level transitions.
			if not len(self.entities[4:]):
				global LEVEL_ID
				self.transition += 1
				if self.transition > 30:
					LEVEL_ID = min(LEVEL_ID + 1, len(os.listdir("assets/maps")) - 1)
					self.load_level(LEVEL_ID)
			if self.transition < 0:
				self.transition += 1

			# Update the respawn timer.
			if self.dead:
				self.dead += 1
				if self.dead >= 10:
					self.transition = min(self.transition + 1, 30)
				if self.dead > 60:
					self.respawn()

			# Update the camera scroll.
			self.camera_scroll[0] += (self.get_main_player().rect().centerx - self.outline_display.get_width() / 2 - self.camera_scroll[0]) / 30
			self.camera_scroll[1] += (self.get_main_player().rect().centery - self.outline_display.get_height() / 2 - self.camera_scroll[1]) / 30
			render_scroll = (int(self.camera_scroll[0]), int(self.camera_scroll[1]))

			self.render_terrain(render_scroll)

			# Update and render the enemies on the main loop, only for the host.
			for enemy in self.entities[4:]:
				died = enemy.update(self.tilemap, movement=(0, 0))
				enemy.render(self.outline_display, offset=render_scroll)
				if died:
					self.entities.remove(enemy)

			# Update and render the main player and other initialized players.
			for player in self.entites[:4]:
				if not self.dead and player.id == "main_player":
					self.get_main_player().update(self.tilemap, movement=(self.movement[1] - self.movement[0], 0))
					self.get_main_player().render(self.outline_display, offset=render_scroll)
				elif player.initialized:
					player.render(self.outline_display, offset=render_scroll)

			# Render the gun projectiles.
			for projectile in self.projectiles.copy():
				# [[x, y], direction, alive_time]
				projectile.update()
				projectile.render(self.outline_display, offset=render_scroll)
				if self.tilemap.solid_check(projectile.pos):
					self.projectiles.remove(projectile)
					for i in range(4):
						self.sparks.append(Spark(projectile.pos, random.random() - 0.5 + (math.pi if projectile.direction > 0 else 0), random.random() + 2))
				elif projectile.alive_time > 360:
					self.projectiles.remove(projectile)
				
				# If the player gets shot.
				elif abs(self.get_main_player().dashing) < 50 and self.get_main_player().rect().collidepoint(projectile.pos):
					self.projectiles.remove(projectile)
					self.dead += 1
					self.screenshake = max(self.screenshake, 16)
					self.sounds["hit"].play()
					for i in range(30):
						angle = random.random() * math.pi * 2
						self.sparks.append(Spark(self.get_main_player().rect().center, angle, random.random() + 2))

						speed = random.random() * 5
						velocity = [math.cos(angle + math.pi) * speed * 0.5, math.sin(angle + math.pi) * speed * 0.5]
						self.particles.append(Particle(self, "dust", self.get_main_player().rect().center, velocity=velocity, start_frame=random.randint(0, 7)))

			self.render_effects(render_scroll)

			# Events handling.
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					self.server.shutdown()
					pygame.quit()
					sys.exit()
				if event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						self.server.shutdown()
						running = False
						fade_out((self.normal_display.get_width(), self.normal_display.get_height()), self.normal_display)
					if event.key == pygame.K_LEFT or event.key == pygame.K_a:
						self.movement[0] = True
					if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
						self.movement[1] = True
					if event.key == pygame.K_UP or event.key == pygame.K_SPACE:
						if self.get_main_player().jump():
							self.sounds["jump"].play()
					if event.key == pygame.K_LSHIFT:
						self.get_main_player().dash()
				if event.type == pygame.KEYUP:
					if event.key == pygame.K_LEFT or event.key == pygame.K_a:
						self.movement[0] = False
					if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
						self.movement[1] = False

			self.handle_level_transition()

			# Blit the outline display on top of the normal one.
			self.normal_display.blit(self.outline_display, (0, 0))

			# Render the players' name tags over anything else.
			for player in self.entities[:4]:
				player.render_name_tag(self.normal_display, offset=render_scroll)

			# Finally, scale and blit all of them on the main screen, along with the screenshake effect.
			screenshake_offset = (random.random() * self.screenshake - self.screenshake / 2, random.random() * self.screenshake - self.screenshake / 2)
			self.screen.blit(pygame.transform.scale(self.normal_display, self.screen.get_size()), screenshake_offset)
			
			pygame.display.update()
			self.clock.tick(60)


class GameForClient(GameBase):
	def __init__(self, clock, screen, outline_display, normal_display, host_ip, port, nickname):
		super().__init__(clock, screen, outline_display, normal_display)

		# First 4 elements are players.
		self.entities = PLAYERS.copy()
		for player in self.entities:
			player.game = self

		self.player_index = -1
		self.client = GameClient(self.entities, self.tilemap, f"client_{CLIENT_ORDER}", ip=host_ip, port=port, nickname=nickname, on_connected=self.on_connected)
		self.spawn_pos = [0, 0]


	def get_main_player(self):
		return self.entities[self.player_index]


	def respawn(self):
		self.get_main_player().pos = self.spawn_pos


	def disconnect_from_server(self):
		self.client.disconnect()


	def on_connected(self, client_id, nickname, player_index):
		# Initialize the main player if the connection is made.
		self.player_index = player_index
		self.get_main_player().initialize_client(nickname, client_id=client_id, id="main_player")


	def load_level(self, id):
		super().load_level(id)
		enemy_count = 1
		for spawner in self.tilemap.extract([("spawners", 0), ("spawners", 1)]):
			self.spawn_pos = spawner.pos
			if spawner.variant == 0:
				# Set the spawn position for all 4 players at once.
				for i in range(4):
					self.entities[i].pos = self.spawn_pos
					self.entities[i].air_time = 0
			else:
				self.entities.append(Enemy(self, spawner.pos, (8, 15), id=f"enemy_{enemy_count}", client_id=self.client.client_id))
				enemy_count += 1


	def run(self):
		super().run()

		running = True
		while running:
			self.outline_display.fill((0, 0, 0, 0))
			self.normal_display.blit(self.assets["background"], (0, 0))

			self.screenshake = max(self.screenshake - 1, 0)

			# Handle level transitions.
			if not len(self.entities[4:]):
				time.sleep(0.1)
				self.transition += 1
				if self.transition > 30:
					self.load_level(LEVEL_ID)
			if self.transition < 0:
				self.transition += 1

			# Update the respawn timer.
			if self.dead:
				self.dead += 1
				if self.dead >= 10:
					self.transition = min(self.transition + 1, 30)
				if self.dead > 60:
					self.respawn()

			# Update the camera scroll.
			self.camera_scroll[0] += (self.get_main_player().rect().centerx - self.outline_display.get_width() / 2 - self.camera_scroll[0]) / 30
			self.camera_scroll[1] += (self.get_main_player().rect().centery - self.outline_display.get_height() / 2 - self.camera_scroll[1]) / 30
			render_scroll = (int(self.camera_scroll[0]), int(self.camera_scroll[1]))

			self.render_terrain(render_scroll)

			# Render the enemies.
			for enemy in self.entities[4:]:
				enemy.render(self.outline_display, offset=render_scroll)

			# Update and render the main player and other initialized players.
			for player in self.entites[:4]:
				if not self.dead and player.id == "main_player":
					self.get_main_player().update(self.tilemap, movement=(self.movement[1] - self.movement[0], 0))
					self.get_main_player().render(self.outline_display, offset=render_scroll)
				elif player.initialized:
					player.render(self.outline_display, offset=render_scroll)

			# Render the gun projectiles.
			for projectile in self.projectiles.copy():
				# [[x, y], direction, alive_time]
				projectile.update()
				projectile.render(self.outline_display, offset=render_scroll)
				if self.tilemap.solid_check(projectile.pos):
					self.projectiles.remove(projectile)
					for i in range(4):
						self.sparks.append(Spark(projectile.pos, random.random() - 0.5 + (math.pi if projectile.direction > 0 else 0), random.random() + 2))
				elif projectile.alive_time > 360:
					self.projectiles.remove(projectile)
				
				# If the player gets shot.
				elif abs(self.get_main_player().dashing) < 50 and self.get_main_player().rect().collidepoint(projectile.pos):
					self.projectiles.remove(projectile)
					self.dead += 1
					self.screenshake = max(self.screenshake, 16)
					self.sounds["hit"].play()
					for i in range(30):
						angle = random.random() * math.pi * 2
						self.sparks.append(Spark(self.get_main_player().rect().center, angle, random.random() + 2))

						speed = random.random() * 5
						velocity = [math.cos(angle + math.pi) * speed * 0.5, math.sin(angle + math.pi) * speed * 0.5]
						self.particles.append(Particle(self, "dust", self.get_main_player().rect().center, velocity=velocity, start_frame=random.randint(0, 7)))

			self.render_effects(render_scroll)

			# Events handling.
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					self.disconnect_from_server()
					pygame.quit()
					sys.exit()
				if event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						self.disconnect_from_server()
						running = False
						fade_out((self.normal_display.get_width(), self.normal_display.get_height()), self.normal_display)
					if event.key == pygame.K_LEFT or event.key == pygame.K_a:
						self.movement[0] = True
					if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
						self.movement[1] = True
					if event.key == pygame.K_UP or event.key == pygame.K_SPACE:
						if self.get_main_player().jump():
							self.sounds["jump"].play()
					if event.key == pygame.K_LSHIFT:
						self.get_main_player().dash()
				if event.type == pygame.KEYUP:
					if event.key == pygame.K_LEFT or event.key == pygame.K_a:
						self.movement[0] = False
					if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
						self.movement[1] = False

			self.handle_level_transition()

			# Blit the outline display on top of the normal one.
			self.normal_display.blit(self.outline_display, (0, 0))

			# Render the players' name tags over anything else.
			for player in self.entities[:4]:
				player.render_name_tag(self.normal_display, offset=render_scroll)

			# Finally, scale and blit all of them on the main screen, along with the screenshake effect.
			screenshake_offset = (random.random() * self.screenshake - self.screenshake / 2, random.random() * self.screenshake - self.screenshake / 2)
			self.screen.blit(pygame.transform.scale(self.normal_display, self.screen.get_size()), screenshake_offset)
			
			pygame.display.update()
			self.clock.tick(60)


class GameSolo(GameBase):
	def __init__(self, clock, screen, outline_display, normal_display):
		super().__init__(clock, screen, outline_display, normal_display)
		self.player = Player("", self, (50, 50), (8, 15))
		self.load_level(self.level_id)


	def get_main_player(self):
		return self.player


	def load_level(self, id):
		super().load_level(id)
		self.enemies = []
		for spawner in self.tilemap.extract([("spawners", 0), ("spawners", 1)]):
			if spawner.variant == 0:
				self.player.pos = spawner.pos
				self.player.air_time = 0
			else:
				self.enemies.append(Enemy(self, spawner.pos, (8, 15)))

	def run(self):
		super().run()

		running = True
		while running:
			self.outline_display.fill((0, 0, 0, 0))
			self.normal_display.blit(self.assets["background"], (0, 0))

			self.screenshake = max(self.screenshake - 1, 0)

			# Handle level transitions.
			if not len(self.enemies):
				self.transition += 1
				if self.transition > 30:
					self.level_id = min(self.level_id + 1, len(os.listdir("assets/maps")) - 1)
					self.load_level(self.level_id)
			if self.transition < 0:
				self.transition += 1

			# Update the respawn timer.
			if self.dead:
				self.dead += 1
				if self.dead >= 10:
					self.transition = min(self.transition + 1, 30)
				if self.dead > 60:
					self.load_level(self.level_id)

			# Update the camera scroll.
			self.camera_scroll[0] += (self.player.rect().centerx - self.outline_display.get_width() / 2 - self.camera_scroll[0]) / 30
			self.camera_scroll[1] += (self.player.rect().centery - self.outline_display.get_height() / 2 - self.camera_scroll[1]) / 30
			render_scroll = (int(self.camera_scroll[0]), int(self.camera_scroll[1]))

			self.render_terrain(render_scroll)

			# Render the enemies.
			for enemy in self.enemies.copy():
				died = enemy.update(self.tilemap, movement=(0, 0))
				enemy.render(self.outline_display, offset=render_scroll)
				if died:
					self.enemies.remove(enemy)

			# Render the player.
			if not self.dead:
				self.player.update(self.tilemap, movement=(self.movement[1] - self.movement[0], 0))
				self.player.render(self.outline_display, offset=render_scroll)

			# Render the gun projectiles.
			for projectile in self.projectiles.copy():
				# [[x, y], direction, alive_time]
				projectile.update()
				projectile.render(self.outline_display, offset=render_scroll)
				if self.tilemap.solid_check(projectile.pos):
					self.projectiles.remove(projectile)
					for i in range(4):
						self.sparks.append(Spark(projectile.pos, random.random() - 0.5 + (math.pi if projectile.direction > 0 else 0), random.random() + 2))
				elif projectile.alive_time > 360:
					self.projectiles.remove(projectile)
				
				# If the player gets shot.
				elif abs(self.player.dashing) < 50 and self.player.rect().collidepoint(projectile.pos):
					self.projectiles.remove(projectile)
					self.dead += 1
					self.screenshake = max(self.screenshake, 16)
					self.sounds["hit"].play()
					for i in range(30):
						angle = random.random() * math.pi * 2
						self.sparks.append(Spark(self.player.rect().center, angle, random.random() + 2))

						speed = random.random() * 5
						velocity = [math.cos(angle + math.pi) * speed * 0.5, math.sin(angle + math.pi) * speed * 0.5]
						self.particles.append(Particle(self, "dust", self.player.rect().center, velocity=velocity, start_frame=random.randint(0, 7)))

			self.render_effects(render_scroll)

			# Events handling.
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					pygame.quit()
					sys.exit()
				if event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						running = False
						fade_out((self.normal_display.get_width(), self.normal_display.get_height()), self.normal_display)
					if event.key == pygame.K_LEFT or event.key == pygame.K_a:
						self.movement[0] = True
					if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
						self.movement[1] = True
					if event.key == pygame.K_UP or event.key == pygame.K_SPACE:
						if self.player.jump():
							self.sounds["jump"].play()
					if event.key == pygame.K_LSHIFT:
						self.player.dash()
				if event.type == pygame.KEYUP:
					if event.key == pygame.K_LEFT or event.key == pygame.K_a:
						self.movement[0] = False
					if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
						self.movement[1] = False

			self.handle_level_transition()

			# Blit the outline display on top of the normal one.
			self.normal_display.blit(self.outline_display, (0, 0))

			# Render world UI over anything else.
			self.player.name_text.render(self.normal_display, offset=render_scroll)

			# Finally, scale and blit all of them on the main screen, along with the screenshake effect.
			screenshake_offset = (random.random() * self.screenshake - self.screenshake / 2, random.random() * self.screenshake - self.screenshake / 2)
			self.screen.blit(pygame.transform.scale(self.normal_display, self.screen.get_size()), screenshake_offset)
			
			pygame.display.update()
			self.clock.tick(60)