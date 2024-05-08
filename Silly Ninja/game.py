import pygame
import random
import sys
import os
import math

from scripts.tilemap import Tilemap
from scripts.entities import Player, Enemy
from scripts.clouds import Clouds
from scripts.visual_effects import Particle, Spark
from scripts.animation import Animation
from scripts.utils import load_image, load_images, fade_out
from scripts.socket.server import GameServer, MAX_CLIENT_COUNT, DISCONNECT_MESSAGE
from scripts.socket.client import GameClient


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


class GameForHost(GameBase):
	def __init__(self, clock, screen, outline_display, normal_display, host_ip, port, nickname):
		super().__init__(clock, screen, outline_display, normal_display)
		self.players = [Player(nickname, self, (50, 50), (8, 15), id="host")]
		self.server = GameServer(host_ip, port, on_new_connection=self.on_new_connection)


	def on_new_connection(self):
		pass


	def load_level(self, id):
		super().load_level(id)


	def run(self):
		super().run()


class GameForClient(GameBase):
	def __init__(self, clock, screen, outline_display, normal_display, host_ip, port):
		super().__init__(clock, screen, outline_display, normal_display)


	def load_level(self, id):
		super().load_level(id)


	def run(self):
		super().run()


class GameSolo(GameBase):
	def __init__(self, clock, screen, outline_display, normal_display):
		super().__init__(clock, screen, outline_display, normal_display)
		self.player = Player("", self, (50, 50), (8, 15))
		self.load_level(self.level_id)


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

			# Handle screen transitions.
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

			# Render the enemies.
			for enemy in self.enemies.copy():
				kill = enemy.update(self.tilemap, movement=(0, 0))
				enemy.render(self.outline_display, offset=render_scroll)
				if kill:
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

			# Render sparks.
			for spark in self.sparks.copy():
				kill = spark.update()
				spark.render(self.outline_display, offset=render_scroll)
				if kill:
					self.sparks.remove(spark)

			# Render the outline for sprites.
			display_mask = pygame.mask.from_surface(self.outline_display)
			display_silhouette = display_mask.to_surface(setcolor=(0, 0, 0, 180), unsetcolor=(0, 0, 0, 0))
			for offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
				self.normal_display.blit(display_silhouette, offset)

			# Render particles and remove expired ones.
			for particle in self.particles.copy():
				kill = particle.update()
				particle.render(self.outline_display, offset=render_scroll)
				if particle.type == "leaf":
					particle.pos[0] += math.sin(particle.animation.frame * 0.035) * (random.random() * 0.3 + 0.2)
				if kill:
					self.particles.remove(particle)

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

			# Render the level transition effect.
			if self.transition:
				transition_surf = pygame.Surface(self.outline_display.get_size())
				pygame.draw.circle(transition_surf, (255, 255, 255), (self.outline_display.get_width() // 2, self.outline_display.get_height() // 2), (30 - abs(self.transition)) * 8)
				transition_surf.set_colorkey((255, 255, 255))
				self.outline_display.blit(transition_surf, (0, 0))

			# Blit the outline display on top of the normal one.
			self.normal_display.blit(self.outline_display, (0, 0))
			# Render world UI over anything else.
			self.player.name_text.render(self.normal_display, offset=render_scroll)

			# Finally, scale and blit all of them on the main screen, along with the screenshake effect.
			screenshake_offset = (random.random() * self.screenshake - self.screenshake / 2, random.random() * self.screenshake - self.screenshake / 2)
			self.screen.blit(pygame.transform.scale(self.normal_display, self.screen.get_size()), screenshake_offset)
			
			pygame.display.update()
			self.clock.tick(60)