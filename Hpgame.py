import sys
import math
import random
import pygame
import os

from scripts.Entities import PhysicsEntity, Player, Enemy
from scripts.utils import load_image, load_images, Animation
from scripts.tilemap import Tilemap
from scripts.clouds import Clouds
from scripts.particle import Particle
from scripts.spark import Spark
from scripts.ai_player import AIPlayer

class Game:
    def __init__(self):
        pygame.init() #essentially starts pygame with these variables assigned

        pygame.display.set_caption('HP game')
        self.screen = pygame.display.set_mode((1350, 750))#visual window dimensions
        self.display = pygame.Surface((500, 270), pygame.SRCALPHA)#allows assets to be drawn larger by using a smaller screen that is then adjusted to fit the main screen
        self.display_2 = pygame.Surface((500, 270))
        self.titlecard = True
        self.choosecharacter = False
        self.gameplay = False
        self.ai_enabled = False  # New flag for AI control
        self.characterlist = ['Okarin', 'Bobo',]#List of character names as appears in selection
        self.characters = ['Assets/images/Okarin.png', 'Assets/images/Bobo.png']#character images/sprites
        self.fps = pygame.time.Clock()
        self.i = 0 #increment used to choose character to load
        self.assets = {
            'decor': load_images('tiles/decor'),
            'grass': load_images('tiles/grass'),
            'large_decor': load_images('tiles/large_decor'),
            'stone': load_images('tiles/stone'),
            'background': load_image('background.png'),
            'clouds' : load_images('clouds'),
            'enemy/idle': Animation(load_images('entities/enemy/idle'), img_dur=6),
            'enemy/run': Animation(load_images('entities/enemy/run'), img_dur=4),
            'player/Bobo/idle' :  Animation(load_images('entities/player/Bobo/idle'), img_dur=6),
            'player/Bobo/run' :  Animation(load_images('entities/player/Bobo/run'), img_dur=4),
            'player/Bobo/jump' : Animation(load_images('entities/player/Bobo/jump')),
            'player/Bobo/slide' : Animation(load_images('entities/player/Bobo/slide')),
            'player/Bobo/wall_slide' : Animation(load_images('entities/player/Bobo/wall_slide')),
            'player/Okarin/idle' :  Animation(load_images('entities/player/Okarin/idle'), img_dur=6),
            'player/Okarin/run' :  Animation(load_images('entities/player/Okarin/run'), img_dur=4),
            'player/Okarin/jump' : Animation(load_images('entities/player/Okarin/jump')),
            'player/Okarin/slide' : Animation(load_images('entities/player/Okarin/slide')),
            'player/Okarin/wall_slide' : Animation(load_images('entities/player/Okarin/wall_slide')),
            'particle/leaf': Animation(load_images('particles/leaf'), img_dur=20, loop=False),
            'particle/particle': Animation(load_images('particles/particle'), img_dur=6, loop=False),
            'gun': load_image('gun.png'),
            'projectile': load_image('projectile.png'),
        }#assets to load

        self.sfx = {
            'jump' : pygame.mixer.Sound('Assets/sfx/jump.wav'),
            'dash' : pygame.mixer.Sound('Assets/sfx/dash.wav'),
            'hit' : pygame.mixer.Sound('Assets/sfx/hit.wav'),
            'shoot' : pygame.mixer.Sound('Assets/sfx/shoot.wav'),
        }

        self.sfx['shoot'].set_volume(0.3)
        self.sfx['hit'].set_volume(0.5)
        self.sfx['dash'].set_volume(0.2)
        self.sfx['jump'].set_volume(0.6)

        self.movement = [False, False]#x axis movement alone, left and right

        self.player = Player(self, (50, 50), (8, 17))#create a player

        self.tilemap = Tilemap(self, tile_size=16)#create a tilemap

        self.level = 0
        self.load_level(self.level)

        self.screenshake = 0
        
        # Initialize AI player
        self.ai_player = AIPlayer(self)

    def load_level(self, map_id):
        self.tilemap.load('Assets/maps/' + str(map_id) + '.json')
        
        self.leaf_spawners = []
        for tree in self.tilemap.extract([('large_decor', 2)], keep=True):
            self.leaf_spawners.append(pygame.Rect(4 + tree['pos'][0], 4 + tree['pos'][1], 23, 13))
    
        self.enemies = []
        for spawner in self.tilemap.extract([('spawners', 0), ('spawners', 1)]):
            if spawner['variant'] == 0:
                self.player.pos = spawner['pos']
                self.pos = spawner['pos']
                self.player.air_time = 0
            else:
                self.enemies.append(Enemy(self, spawner['pos'], (8, 15)))
        
        self.projectiles = []
        self.particles = []
        self.sparks = []
        
        self.scroll = [0, 0]
        self.dead = 0
        self.transition = -60

        self.clouds = Clouds(self.assets['clouds'], count=16)#create clouds

    def run(self):
        pygame.mixer.music.load('Assets/music.mp3')
        pygame.mixer.music.set_volume(0.1)
        pygame.mixer.music.play(-1)

        while True:
            self.display.fill((0, 0, 0, 0))
            self.display_2.blit(self.assets['background'], (0, 0))#use background image

            self.screenshake = max(0, self.screenshake - 1)

            if not len(self.enemies):
                self.transition += 1
                if self.transition > 60:
                    self.level = min(self.level + 1, len(os.listdir('Assets/maps')) - 1)
                    self.load_level(self.level)
            if self.transition < 0:
                self.transition += 1

            if self.dead:
                self.dead += 1
                if self.dead == 20:
                    self.transition = min(60, self.transition + 1)
                if self.dead > 40:
                    self.load_level(self.level)

            self.scroll[0] += (self.player.rect().centerx - self.display.get_width() / 2 - self.scroll[0]) / 25 #cretes a camera as scroll continues using player position etc, the further and quicker the player gets the quicker the camera is
            self.scroll[1] += (self.player.rect().centery - self.display.get_height() / 2 - self.scroll[1]) / 25
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))#the scroll we use to render approximating using int()

            for rect in self.leaf_spawners:
                if random.random() * 49999 < rect.width * rect.height:#in the area of our rectangle
                    pos = (rect.x + random.random() * rect.width, rect.y + random.random() * rect.height)
                    self.particles.append(Particle(self, 'leaf', pos, velocity=[-0.1, 0.3], frame=random.randint(0, 20)))

            self.clouds.update()#puts clouds on screen
            self.clouds.render(self.display_2, offset=render_scroll)#renders and scrolls clouds

            self.tilemap.render(self.display, offset=render_scroll)#renders and scrolls tilemaps

            for enemy in self.enemies.copy():
                kill = enemy.update(self.tilemap, (0, 0))
                enemy.render(self.display, offset=render_scroll)
                if kill:
                    self.enemies.remove(enemy)
                
            if not self.dead:
                self.player.update(self.tilemap, (self.movement[1] - self.movement[0], 0))
                self.player.render(self.display, offset=render_scroll)
    
            # [[x, y], direction, timer]
            for projectile in self.projectiles.copy():
                projectile[0][0] += projectile[1]
                projectile[2] += 1
                img = self.assets['projectile']
                self.display.blit(img, (projectile[0][0] - img.get_width() / 2 - render_scroll[0], projectile[0][1] - img.get_height() / 2 - render_scroll[1]))
                if self.tilemap.solid_check(projectile[0]):
                    self.projectiles.remove(projectile)
                    for i in range(4):
                        self.sparks.append(Spark(projectile[0], random.random() - 0.5 + (math.pi if projectile[1] > 0 else 0), 2 + random.random()))
                elif projectile[2] > 360:
                    self.projectiles.remove(projectile)
                elif abs(self.player.dashing) < 50:
                    if self.player.rect().collidepoint(projectile[0]):
                        self.projectiles.remove(projectile)
                        self.dead += 1
                        self.sfx['hit'].play()
                        self.screenshake = max(16, self.screenshake)
                        for i in range(30):
                            angle = random.random() * math.pi * 2
                            speed = random.random() * 5
                            self.sparks.append(Spark(self.player.rect().center, angle, 2 + random.random()))
                            self.particles.append(Particle(self, 'particle', self.player.rect().center, velocity=[math.cos(angle + math.pi) * speed * 0.5, math.sin(angle + math.pi) * speed * 0.5], frame=random.randint(0, 7)))

            for spark in self.sparks.copy():
                kill = spark.update()
                spark.render(self.display, offset=render_scroll)
                if kill:
                    self.sparks.remove(spark)

            display_mask = pygame.mask.from_surface(self.display)
            display_silhouette = display_mask.to_surface(setcolor=(0, 0, 0, 180), unsetcolor=(0, 0, 0, 0))
            for offset in [(-1, 0), (1, 0), (0,-1), (0, 1)]:
                self.display_2.blit(display_silhouette, offset)
            
            for particle in self.particles.copy():
                kill = particle.update()
                particle.render(self.display, offset=render_scroll)
                if particle.type == 'leaf':
                    particle.pos[0] += math.sin(particle.animation.frame * 0.035) * 0.3
                if kill:
                    self.particles.remove(particle)

            for event in pygame.event.get():
                self.screen.fill('black')#fills screen black to avoid stacking of elements
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                # Global TAB key handler for AI toggle
                if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB and self.gameplay:
                    self.ai_enabled = not self.ai_enabled
                    print("AI Control:", "Enabled" if self.ai_enabled else "Disabled")
                
                if self.titlecard:
                    self.titletext = pygame.font.Font("Assets/font.ttf", 43).render('Press ANY KEY to START ', True, '#b68f40')
                    self.enter = pygame.font.Font("Assets/font.ttf", 40).render('(TAB to toggle AI Tester)', True, 'white')
                    self.box = self.titletext.get_rect(center=(675, 300))
                    self.box2 = self.enter.get_rect(center=(675, 525))
                    self.screen.blit(self.titletext, self.box)
                    self.screen.blit(self.enter, self.box2)
                elif self.choosecharacter:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                            self.i = (self.i - 1) % 2
                        elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                            self.i = (self.i + 1) % 2
                        elif event.key == pygame.K_RETURN:
                            self.choosecharacter = False
                            self.transition = -60
                            self.gameplay = True

                    self.player = Player(self, (50, 50), (8, 17))
                    self.player.pos = self.pos
                    self.img = pygame.image.load(self.characters[self.i])
                    self.img_position = (600, 300)
                    self.arrow_left = pygame.font.Font('Assets/font.ttf', 75).render('<', True, 'white')
                    self.arrow_right = pygame.font.Font('Assets/font.ttf', 75).render('>', True, 'white')
                    self.arrow_left_box = self.arrow_left.get_rect(center=(150, 375))
                    self.arrow_right_box = self.arrow_right.get_rect(center=(1200, 375))
                    self.entertext = pygame.font.Font('Assets/font.ttf', 37).render('Press ENTER to SELECT CHARACTER', True, 'white')
                    self.charactertext = pygame.font.Font('Assets/font.ttf', 45).render(self.characterlist[self.i], True, 'white')
                    self.characterbox = self.charactertext.get_rect(center=(675, 600))
                    self.enterbox = self.entertext.get_rect(center=(675, 113))
                    self.screen.blit(self.arrow_left, self.arrow_left_box)
                    self.screen.blit(self.arrow_right, self.arrow_right_box)
                    self.screen.blit(self.img, self.img_position)
                    self.screen.blit(self.entertext, self.enterbox)
                    self.screen.blit(self.charactertext, self.characterbox)

                if self.titlecard and event.type == pygame.KEYDOWN:
                    self.titlecard = False
                    self.choosecharacter = True
                if self.gameplay and not self.ai_enabled:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                            self.movement[0] = True
                        if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                            self.movement[1] = True
                        if event.key == pygame.K_UP or event.key == pygame.K_w:
                            if self.player.jump():
                                self.sfx['jump'].play()
                        if event.key == pygame.K_x or event.key == pygame.K_LSHIFT:
                            self.player.dash()
                    if event.type == pygame.KEYUP:
                        if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                            self.movement[0] = False
                        if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                            self.movement[1] = False

            # Update AI if enabled
            if self.gameplay and self.ai_enabled and not self.dead:
                self.ai_player.update()

            if self.gameplay:
                # Add AI status indicator
                ai_text = pygame.font.Font("Assets/font.ttf", 20).render('AI: ' + ('ON' if self.ai_enabled else 'OFF') + ' (TAB to toggle)', True, 'white')
                self.screen.blit(ai_text, (20, 20))

            if self.gameplay:
                if self.transition:
                    transition_surf = pygame.Surface(self.display.get_size())
                    pygame.draw.circle(transition_surf, (255, 255, 255), (self.display.get_width() // 2, self.display.get_height() // 2), (60 - abs(self.transition)) * 8)
                    transition_surf.set_colorkey((255, 255, 255))
                    self.display.blit(transition_surf, (0, 0))
                self.display_2.blit(self.display, (0, 0))
                screenshake_offset = (random.random() * self.screenshake - self.screenshake / 2, random.random() * self.screenshake - self.screenshake / 2)
                self.screen.blit(pygame.transform.scale(self.display_2, self.screen.get_size()), screenshake_offset)#creates a display to increase size of small assets                  
            pygame.display.update() #constantly refreshes screen
            self.fps.tick(60)

Game().run() 
