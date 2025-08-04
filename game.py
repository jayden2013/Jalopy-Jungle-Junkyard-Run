import pygame
import random
import sys
import math

# ─── Configuration ───────────────────────────────────────────────────────────
WIDTH, HEIGHT                = 1024, 768
FPS                          = 60

NUM_PARTS                    = 5
NUM_ENEMIES                  = 3
PLAYER_SPEED                 = 4
ENEMY_SPEED                  = 2
MIN_ENEMY_SEPARATION         = 40    # pixels between regular enemies

# Thief settings
THIEF_SPEED      = 1
THIEF_DROP_MIN   = 3000
THIEF_DROP_MAX   = 30000
THIEF_COOLDOWN   = 500

# Long-line settings
LINE_PROBABILITY   = 0.5
WAIT_TIME          = 1200
COME_BACK_DELAY    = 5000

# Chair drop settings
CHAIR_DROP_INTERVAL   = 10000
CHAIR_DROP_CHANCE     = 0.5
CHAIR_INVINCIBILITY   = 2000

# Chair highlight
CHAIR_GLOW_RADIUS     = 25
CHAIR_GLOW_COLOR      = (255, 255, 0, 100)

# Boomerang settings
BOOMERANG_SPAWN_INTERVAL = 20000
BOOMERANG_SPAWN_CHANCE   = 0.3
BOOMERANG_RESPAWN_DELAY  = 10000
BOOMERANG_SPEED          = 0.015

# Speed-boost settings
SPEEDBOOST_SPAWN_INTERVAL = 30000
SPEEDBOOST_SPAWN_CHANCE   = 0.2
SPEEDBOOST_DURATION       = 10000
SPEEDBOOST_MULTIPLIER     = 2.0

# Super Boomer boss settings
BOSS_SPAWN_COUNT       = 1       # every 7 deliveries
WARNING_DURATION       = 1000    # ms of "SUPER BOOMER!" warning
BOSS_CHARGE_TIME       = 3000    # ms to charge before sprint
BOSS_SPRINT_SPEED      = 10      # px per frame
BOSS_PURSUIT_SPEED     = 1
BOSS_CHAIR_INTERVAL    = 2000    # ms between boss chair throws
BOSS_HIT_POINTS        = 5       # hits to kill boss

# Colors
BG_COLOR         = (50, 50, 50)
TEXT_COLOR       = (255, 255, 255)
LONG_LINE_COLOR  = (255, 50, 50)
BOSS_BAR_BG      = (100, 0, 0)
BOSS_BAR_FILL    = (255, 0, 0)
# ─────────────────────────────────────────────────────────────────────────────

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock  = pygame.time.Clock()
font   = pygame.font.SysFont(None, 36)

# ─── Intro ────────────────────────────────────────────────────────────────────
intro_font  = pygame.font.SysFont(None, 24, bold=True)
intro_lines = [
    "A long time ago, in a junkyard far, far away...", "",
    "You are the last guardian of the pristine MN12 Thunderbird.",
    "Its polished panels gleam in the dusty sunlight.", "",
    "But the Boomers, with their rusty relics, plot to seize its parts",
    "to fuel their sloppy rebuilds of their undead Thunderbirds.", "",
    "Time is short. Scour the yard, collect the parts,",
    "and assemble the final masterpiece", "before they strike!", "",
    "Press ENTER to begin..."
]
intro_surfs  = [intro_font.render(line, True, (255,255,0))
                for line in intro_lines]
scroll_y     = HEIGHT
scroll_speed = 0.05
state_intro  = True
# ─────────────────────────────────────────────────────────────────────────────

# ─── Load assets ─────────────────────────────────────────────────────────────
background = pygame.image.load("assets/background.png").convert()
background = pygame.transform.scale(background, (WIDTH, HEIGHT))

PART_IMAGE_FILES = ["assets/part1.png", "assets/part2.png", "assets/part3.png"]
part_textures    = []
for fn in PART_IMAGE_FILES:
    tex = pygame.image.load(fn).convert_alpha()
    tex = pygame.transform.scale(tex, (20,20))
    part_textures.append(tex)

CHAIR_IMAGE = pygame.image.load("assets/chair.png").convert_alpha()
CHAIR_IMAGE = pygame.transform.scale(CHAIR_IMAGE, (20,20))

BOOMERANG_IMAGE = pygame.image.load("assets/boomerang.png").convert_alpha()
BOOMERANG_IMAGE = pygame.transform.scale(BOOMERANG_IMAGE, (20,20))

ENEMY_IMAGE = pygame.image.load("assets/enemy.png").convert_alpha()
ENEMY_IMAGE = pygame.transform.scale(ENEMY_IMAGE, (30,30))

NOS_IMAGE = pygame.image.load("assets/nos.png").convert_alpha()
NOS_IMAGE = pygame.transform.scale(NOS_IMAGE, (20,20))

PLAYER_IMAGE = pygame.image.load("assets/player.png").convert_alpha()
PLAYER_IMAGE = pygame.transform.scale(PLAYER_IMAGE, (30,30))

THIEF_IMAGE = pygame.image.load("assets/thief.png").convert_alpha()
THIEF_IMAGE = pygame.transform.scale(THIEF_IMAGE, (30,30))

SUPERBOOMER_IMAGE = pygame.image.load("assets/super_boomer.png").convert_alpha()
SUPERBOOMER_IMAGE = pygame.transform.scale(SUPERBOOMER_IMAGE, (80,80))
# ─────────────────────────────────────────────────────────────────────────────

def normalize(vx, vy):
    dist = math.hypot(vx, vy)
    return (vx/dist, vy/dist) if dist else (0,0)

# ─── Globals ─────────────────────────────────────────────────────────────────
delay_event           = None
current_carried_img   = None
delivered             = 0
game_over             = False
last_chair_drop       = pygame.time.get_ticks()
last_boom_spawn       = pygame.time.get_ticks()
last_speed_spawn      = pygame.time.get_ticks()
respawns              = []

# Boss state
boss                  = None
boss_warning_start    = None

# placeholder groups
parts                 = None
enemies               = None
thieves               = None
chairs                = None
boomerangs            = None
boomerang_projectiles = None
speed_items           = None
all_sprites           = None
# ─────────────────────────────────────────────────────────────────────────────

# ─── Game Objects ────────────────────────────────────────────────────────────
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = PLAYER_IMAGE
        self.rect  = self.image.get_rect(center=(WIDTH//2, HEIGHT//2))
        self.mask  = pygame.mask.from_surface(self.image)
        self.carrying         = False
        self.has_boomerang    = False
        self.speed_multiplier = 1.0
        self.boost_end_time   = 0

    def update(self, keys):
        now = pygame.time.get_ticks()
        if now > self.boost_end_time:
            self.speed_multiplier = 1.0
        speed = PLAYER_SPEED * self.speed_multiplier
        dx = dy = 0
        if keys[pygame.K_LEFT]:   dx = -speed
        if keys[pygame.K_RIGHT]:  dx =  speed
        if keys[pygame.K_UP]:      dy = -speed
        if keys[pygame.K_DOWN]:    dy =  speed
        self.rect.x = max(0, min(WIDTH-self.rect.w, self.rect.x + dx))
        self.rect.y = max(0, min(HEIGHT-self.rect.h, self.rect.y + dy))

class Part(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = random.choice(part_textures)
        self.rect  = self.image.get_rect(center=pos)
        self.mask  = pygame.mask.from_surface(self.image)
        self.forbidden_thief = None
        glow_r = 20
        self.glow = pygame.Surface((glow_r*2,glow_r*2), pygame.SRCALPHA)
        pygame.draw.circle(self.glow, (255,255,0,100),
                           (glow_r,glow_r), glow_r)

class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = ENEMY_IMAGE
        self.rect  = self.image.get_rect(center=pos)
        self.mask  = pygame.mask.from_surface(self.image)

class Thief(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = THIEF_IMAGE
        self.rect  = self.image.get_rect(center=pos)
        self.mask  = pygame.mask.from_surface(self.image)
        angle       = random.uniform(0,2*math.pi)
        self.direction      = (math.cos(angle), math.sin(angle))
        self.carrying       = False
        self.carried_image  = None
        self.drop_time      = None
        self.cooldown_until = 0

    def update(self):
        now = pygame.time.get_ticks()
        if self.carrying and now >= self.drop_time:
            dropped = Part(self.rect.center)
            dropped.image           = self.carried_image
            dropped.rect            = dropped.image.get_rect(center=self.rect.center)
            dropped.mask            = pygame.mask.from_surface(dropped.image)
            dropped.forbidden_thief = self
            parts.add(dropped); all_sprites.add(dropped)
            self.carrying           = False
            self.carried_image      = None
            self.drop_time          = None
            self.cooldown_until     = now + THIEF_COOLDOWN
            return

        if now >= self.cooldown_until and not self.carrying:
            if player.carrying and pygame.sprite.collide_mask(self, player):
                self.carrying      = True
                self.carried_image = current_carried_img
                player.carrying    = False
                self.drop_time     = now + random.randint(THIEF_DROP_MIN,THIEF_DROP_MAX)
            else:
                for p in parts:
                    if p.forbidden_thief is self: continue
                    if pygame.sprite.collide_mask(self, p):
                        self.carrying      = True
                        self.carried_image = p.image
                        p.kill()
                        self.drop_time     = now + random.randint(THIEF_DROP_MIN,THIEF_DROP_MAX)
                        break

        if not self.carrying:
            candidates = [p for p in parts if p.forbidden_thief is not self]
            if candidates:
                target = min(candidates,
                             key=lambda p: (p.rect.centerx-self.rect.centerx)**2
                                         + (p.rect.centery-self.rect.centery)**2)
                dx, dy = target.rect.centerx-self.rect.centerx, target.rect.centery-self.rect.centery
                dir_x, dir_y = normalize(dx, dy)
            else:
                dir_x, dir_y = self.direction
        else:
            dir_x, dir_y = self.direction

        self.rect.x += dir_x * THIEF_SPEED
        self.rect.y += dir_y * THIEF_SPEED
        bounced = False
        if self.rect.left < 0 or self.rect.right > WIDTH:
            dir_x = -dir_x; bounced = True
        if self.rect.top < 0 or self.rect.bottom > HEIGHT:
            dir_y = -dir_y; bounced = True
        if bounced or random.random()<0.02:
            ang = random.uniform(0,2*math.pi)
            dir_x, dir_y = math.cos(ang), math.sin(ang)
        self.direction = (dir_x, dir_y)

class Cashier(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = pygame.Surface((30,30), pygame.SRCALPHA)
        self.rect  = self.image.get_rect(center=pos)

class Chair(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = CHAIR_IMAGE
        self.rect  = self.image.get_rect(center=pos)
        self.mask  = pygame.mask.from_surface(self.image)
        self.spawn_time = pygame.time.get_ticks()
        self.glow = pygame.Surface((CHAIR_GLOW_RADIUS*2,CHAIR_GLOW_RADIUS*2),
                                   pygame.SRCALPHA)
        pygame.draw.circle(self.glow, CHAIR_GLOW_COLOR,
                           (CHAIR_GLOW_RADIUS,CHAIR_GLOW_RADIUS),
                           CHAIR_GLOW_RADIUS)

class BoomerangItem(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = BOOMERANG_IMAGE
        self.rect  = self.image.get_rect(center=pos)
        self.mask  = pygame.mask.from_surface(self.image)
        glow_r = 25
        self.glow = pygame.Surface((glow_r*2,glow_r*2),pygame.SRCALPHA)
        pygame.draw.circle(self.glow, CHAIR_GLOW_COLOR,
                           (glow_r,glow_r), glow_r)

class BoomerangProjectile(pygame.sprite.Sprite):
    def __init__(self, start_pos):
        super().__init__()
        self.image = BOOMERANG_IMAGE
        self.rect  = self.image.get_rect(center=start_pos)
        self.mask  = pygame.mask.from_surface(self.image)
        self.start   = pygame.math.Vector2(start_pos)
        self.end     = pygame.math.Vector2(start_pos)
        mx, my      = pygame.mouse.get_pos()
        dirv        = pygame.math.Vector2(mx,my)-self.start
        if dirv.length()==0:
            dirv = pygame.math.Vector2(1,0)
        dirv        = dirv.normalize()*150
        self.control = self.start + dirv + pygame.math.Vector2(0,-75)
        self.t       = 0.0
        self.speed   = BOOMERANG_SPEED
        self.returning=False

    def update(self):
        now = pygame.time.get_ticks()
        if not self.returning:
            self.t += self.speed
            if self.t >= 1.0:
                self.t        = 1.0
                self.returning=True
        else:
            self.t -= self.speed
            if self.t <= 0.0:
                self.kill()
                return

        p = (self.start*(1-self.t)**2 +
             self.control*2*(1-self.t)*self.t +
             self.end*self.t**2)
        self.rect.center = (round(p.x), round(p.y))

        # hit regular enemies
        hit = pygame.sprite.spritecollideany(self, enemies,
                                            pygame.sprite.collide_mask)
        if hit:
            hit.kill()
            respawns.append(now + BOOMERANG_RESPAWN_DELAY)
        # hit boss?
        global boss
        if boss and pygame.sprite.collide_mask(self, boss):
            boss.health -= 1
            self.kill()
            if boss.health <= 0:
                boss.kill()
                boss = None

class SpeedBoostItem(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = NOS_IMAGE
        self.rect  = self.image.get_rect(center=pos)
        self.mask  = pygame.mask.from_surface(self.image)
        glow_r = 25
        self.glow = pygame.Surface((glow_r*2,glow_r*2),pygame.SRCALPHA)
        pygame.draw.circle(self.glow, (255,150,0,120),
                           (glow_r,glow_r),glow_r)

class SuperBoomer(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = SUPERBOOMER_IMAGE
        self.rect  = self.image.get_rect(center=(WIDTH//2, HEIGHT//2))
        self.mask  = pygame.mask.from_surface(self.image)
        self.health          = BOSS_HIT_POINTS
        self.state           = "charging"
        self.state_start     = pygame.time.get_ticks()
        self.last_chair_throw= pygame.time.get_ticks()
        self.sprint_dir = (0,0)
        self.sprint_target = None
    def update(self):
        now = pygame.time.get_ticks()

        # State machine for charging, sprinting, and pursuit
        if self.state == "charging":
            # After charge time, begin sprint attack
            if now - self.state_start >= BOSS_CHARGE_TIME:
                # lock onto player's position
                px, py = player.rect.center
                dx = px - self.rect.centerx
                dy = py - self.rect.centery
                dir_x, dir_y = normalize(dx, dy)
                self.sprint_dir    = (dir_x, dir_y)
                self.sprint_target = (px, py)
                self.state = "sprinting"
                self.state_start = now

        elif self.state == "sprinting":
            # sprint along locked direction
            self.rect.x += self.sprint_dir[0] * BOSS_SPRINT_SPEED
            self.rect.y += self.sprint_dir[1] * BOSS_SPRINT_SPEED
            # clamp on-screen
            self.rect.x = max(0, min(self.rect.x, WIDTH - self.rect.width))
            self.rect.y = max(0, min(self.rect.y, HEIGHT - self.rect.height))
            # check if reached target
            tx, ty = self.sprint_target
            if math.hypot(self.rect.centerx - tx, self.rect.centery - ty) < BOSS_SPRINT_SPEED:
                self.state       = "pursuing"
                self.state_start = now

        elif self.state == "pursuing":
            # Move toward the player
            dx = player.rect.centerx - self.rect.centerx
            dy = player.rect.centery - self.rect.centery
            dist = math.hypot(dx, dy)
            if dist != 0:
                self.rect.x += BOSS_PURSUIT_SPEED * dx / dist
                self.rect.y += BOSS_PURSUIT_SPEED * dy / dist
            # Clamp inside screen bounds
            self.rect.x = max(0, min(self.rect.x, WIDTH - self.rect.width))
            self.rect.y = max(0, min(self.rect.y, HEIGHT - self.rect.height))
            # After cooldown, go back to charging for the next attack
            if now - self.state_start >= BOSS_CHARGE_TIME:
                self.state = "charging"
                self.state_start = now

        # Continue throwing chairs on interval
        if now - self.last_chair_throw >= BOSS_CHAIR_INTERVAL:
            c = Chair(self.rect.center)
            chairs.add(c)
            all_sprites.add(c)
            self.last_chair_throw = now

# ─── Handlers ─────────────────────────────────────────────────────────────────
def handle_delivery():
    global delivered, delay_event, current_carried_img, boss_warning_start
    delivered += 1
    if delivered % 10 == 0:
        tx = random.randint(50, WIDTH-50)
        ty = random.randint(50, HEIGHT-50)
        new_thief = Thief((tx,ty))
        thieves.add(new_thief); all_sprites.add(new_thief)
    # trigger boss warning
    if delivered % BOSS_SPAWN_COUNT == 0:
        boss_warning_start = pygame.time.get_ticks()
    delay_event         = None
    current_carried_img = None
    player.carrying     = False
    x = random.randint(50, WIDTH-150)
    y = random.randint(50, HEIGHT-150)
    p = Part((x,y)); parts.add(p); all_sprites.add(p)
    e = Enemy((WIDTH-15,15)); enemies.add(e); all_sprites.add(e)

def reset_game():
    global parts, enemies, thieves, chairs
    global boomerangs, boomerang_projectiles, speed_items, all_sprites
    global delivered, game_over, delay_event, current_carried_img
    global last_chair_drop, last_boom_spawn, last_speed_spawn, respawns
    global boss, boss_warning_start

    delivered            = 0
    game_over            = False
    delay_event          = None
    current_carried_img  = None
    last_chair_drop      = pygame.time.get_ticks()
    last_boom_spawn      = pygame.time.get_ticks()
    last_speed_spawn     = pygame.time.get_ticks()
    respawns.clear()

    boss                 = None
    boss_warning_start   = None

    player.carrying        = False
    player.has_boomerang   = False
    player.speed_multiplier= 1.0
    player.boost_end_time  = 0
    player.rect.center     = (WIDTH//2, HEIGHT//2)

    all_sprites            = pygame.sprite.Group(player, cashier)

    parts                  = pygame.sprite.Group()
    for _ in range(NUM_PARTS):
        x = random.randint(50, WIDTH-150)
        y = random.randint(50, HEIGHT-150)
        p = Part((x,y)); parts.add(p); all_sprites.add(p)

    enemies                = pygame.sprite.Group()
    safe_dist              = 150
    for _ in range(NUM_ENEMIES):
        while True:
            ex = random.randint(50, WIDTH-50)
            ey = random.randint(50, HEIGHT-50)
            if math.hypot(ex-WIDTH//2, ey-HEIGHT//2) > safe_dist:
                break
        e = Enemy((ex,ey)); enemies.add(e); all_sprites.add(e)

    thieves                = pygame.sprite.Group()
    tx = random.randint(50, WIDTH-50)
    ty = random.randint(50, HEIGHT-50)
    t  = Thief((tx,ty)); thieves.add(t); all_sprites.add(t)

    chairs                 = pygame.sprite.Group()
    boomerangs             = pygame.sprite.Group()
    boomerang_projectiles  = pygame.sprite.Group()
    speed_items            = pygame.sprite.Group()

    bx = random.randint(50, WIDTH-50)
    by = random.randint(50, HEIGHT-50)
    b  = BoomerangItem((bx,by))
    boomerangs.add(b); all_sprites.add(b)

# ─── Init & Loop ───────────────────────────────────────────────────────────────
player  = Player()
cashier = Cashier((20, HEIGHT-20))
reset_game()

while True:
    dt  = clock.tick(FPS)
    now = pygame.time.get_ticks()

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RETURN:
                if state_intro:
                    state_intro = False
                elif game_over:
                    reset_game()
            if ev.key == pygame.K_SPACE and player.has_boomerang and not boomerang_projectiles:
                proj = BoomerangProjectile(player.rect.center)
                boomerang_projectiles.add(proj); all_sprites.add(proj)
                player.has_boomerang = False

    if state_intro:
        scroll_y -= dt * scroll_speed
        screen.fill((0,0,0))
        for i, surf in enumerate(intro_surfs):
            x = (WIDTH - surf.get_width()) // 2
            y = scroll_y + i*30
            screen.blit(surf, (x,y))
        if scroll_y + len(intro_surfs)*30 < 0:
            state_intro = False
        pygame.display.flip()
        continue

    # ── Super Boomer warning & spawn ─────────────────────────────────────────
    if boss_warning_start is not None:
        if now - boss_warning_start < WARNING_DURATION:
            screen.fill((0,0,0))
            warning = font.render("SUPER BOOMER!", True, (255,0,0))
            wx = (WIDTH - warning.get_width())//2
            screen.blit(warning, (wx, HEIGHT//2 - warning.get_height()//2))
            pygame.display.flip()
            continue
        else:
            boss = SuperBoomer()
            all_sprites.add(boss)
            boss_warning_start = None

    # ── Game Update ──────────────────────────────────────────────────────────
    if not game_over:
        keys    = pygame.key.get_pressed()
        old_pos = player.rect.topleft
        player.update(keys)

        # block through chairs/thieves using pixel masks
        if pygame.sprite.spritecollideany(player, chairs,
                                          pygame.sprite.collide_mask):
            player.rect.topleft = old_pos
        if pygame.sprite.spritecollideany(player, thieves,
                                          pygame.sprite.collide_mask):
            player.rect.topleft = old_pos

        # boss collision = death
        if boss and pygame.sprite.collide_mask(player, boss):
            game_over = True

        # thief-steal fallback with mask
        for t in thieves:
            if (player.carrying and not t.carrying
                and pygame.sprite.collide_mask(player, t)):
                t.carrying      = True
                t.carried_image = current_carried_img
                player.carrying = False
                current_carried_img = None
                t.drop_time = now + random.randint(THIEF_DROP_MIN,THIEF_DROP_MAX)

        # update enemies & clear chairs
        for e in enemies:
            dx, dy = player.rect.centerx-e.rect.centerx, player.rect.centery-e.rect.centery
            nx, ny = normalize(dx, dy)
            mvx, mvy = nx*ENEMY_SPEED, ny*ENEMY_SPEED
            sx = sy = 0
            for o in enemies:
                if o is not e:
                    dx2, dy2 = e.rect.centerx-o.rect.centerx, e.rect.centery-o.rect.centery
                    d = math.hypot(dx2, dy2)
                    if 0 < d < MIN_ENEMY_SEPARATION:
                        rx, ry = dx2/d, dy2/d
                        sx += rx; sy += ry
            if sx or sy:
                sd = math.hypot(sx, sy)
                sx, sy = sx/sd, sy/sd
                mvx += sx*ENEMY_SPEED; mvy += sy*ENEMY_SPEED

            e.rect.x += mvx
            e.rect.y += mvy

            hit_chair = pygame.sprite.spritecollideany(e, chairs,
                                                      pygame.sprite.collide_mask)
            if hit_chair and now - hit_chair.spawn_time >= CHAIR_INVINCIBILITY:
                hit_chair.kill()

        # drop chairs
        if now - last_chair_drop >= CHAIR_DROP_INTERVAL:
            for e in enemies:
                if random.random() < CHAIR_DROP_CHANCE:
                    chair = Chair(e.rect.center)
                    chairs.add(chair); all_sprites.add(chair)
            last_chair_drop = now

        # update thieves
        for t in thieves:
            t.update()

        # pickup parts
        if not player.carrying:
            hit = pygame.sprite.spritecollideany(player, parts,
                                                pygame.sprite.collide_mask)
            if hit:
                current_carried_img = hit.image
                hit.kill()
                player.carrying = True
        else:
            if delay_event is None and pygame.sprite.collide_rect(player,cashier):
                if random.random() < LINE_PROBABILITY:
                    delay_event = {
                        'start_time': now,
                        'next_available_time': now + COME_BACK_DELAY
                    }
                else:
                    handle_delivery()
            elif delay_event and pygame.sprite.collide_rect(player,cashier):
                elapsed = now - delay_event['start_time']
                if elapsed >= WAIT_TIME or now >= delay_event['next_available_time']:
                    handle_delivery()

        # spawn/pickup boomerang
        if now - last_boom_spawn >= BOOMERANG_SPAWN_INTERVAL:
            if (random.random() < BOOMERANG_SPAWN_CHANCE
                and not boomerangs and not player.has_boomerang):
                bx, by = (random.randint(50,WIDTH-50),
                          random.randint(50,HEIGHT-50))
                b = BoomerangItem((bx,by))
                boomerangs.add(b); all_sprites.add(b)
            last_boom_spawn = now

        if not player.has_boomerang and not boomerang_projectiles:
            hit_b = pygame.sprite.spritecollideany(player, boomerangs,
                                                  pygame.sprite.collide_mask)
            if hit_b:
                player.has_boomerang = True
                hit_b.kill()

        for proj in boomerang_projectiles:
            proj.update()

        # spawn/pickup speed-boost
        if now - last_speed_spawn >= SPEEDBOOST_SPAWN_INTERVAL:
            if random.random() < SPEEDBOOST_SPAWN_CHANCE and not speed_items:
                sx, sy = (random.randint(50,WIDTH-50),
                          random.randint(50,HEIGHT-50))
                sb = SpeedBoostItem((sx,sy))
                speed_items.add(sb); all_sprites.add(sb)
            last_speed_spawn = now

        hit_sb = pygame.sprite.spritecollideany(player, speed_items,
                                                pygame.sprite.collide_mask)
        if hit_sb:
            hit_sb.kill()
            player.speed_multiplier = SPEEDBOOST_MULTIPLIER
            player.boost_end_time   = now + SPEEDBOOST_DURATION

        # respawn enemies
        for ts in respawns[:]:
            if now >= ts:
                while True:
                    ex = random.randint(50,WIDTH-50)
                    ey = random.randint(50,HEIGHT-50)
                    if math.hypot(ex-player.rect.centerx,
                                  ey-player.rect.centery)>150:
                        break
                new_e = Enemy((ex,ey))
                enemies.add(new_e); all_sprites.add(new_e)
                respawns.remove(ts)

        # update boss
        if boss:
            boss.update()

        # game over
        if pygame.sprite.spritecollideany(player, enemies,
                                          pygame.sprite.collide_mask):
            game_over = True

    # ── Render ─────────────────────────────────────────────────────────────────
    screen.blit(background, (0,0))

    for part in parts:
        glow_rect = part.glow.get_rect(center=part.rect.center)
        screen.blit(part.glow, glow_rect)
    for chair in chairs:
        glow_rect = chair.glow.get_rect(center=chair.rect.center)
        screen.blit(chair.glow, glow_rect)
    for b in boomerangs:
        glow_rect = b.glow.get_rect(center=b.rect.center)
        screen.blit(b.glow, glow_rect)
    for sb in speed_items:
        glow_rect = sb.glow.get_rect(center=sb.rect.center)
        screen.blit(sb.glow, glow_rect)

    all_sprites.draw(screen)

    # thief-carried part above head
    for t in thieves:
        if t.carrying and t.carried_image:
            tx = t.rect.centerx - t.carried_image.get_width()//2
            ty = t.rect.top - t.carried_image.get_height() - 5
            screen.blit(t.carried_image, (tx, ty))

    # player-carried part above head
    if player.carrying and current_carried_img:
        px = player.rect.centerx - current_carried_img.get_width()//2
        py = player.rect.top - current_carried_img.get_height() - 5
        screen.blit(current_carried_img, (px, py))

    # draw boss health bar
    if boss:
        bar_w, bar_h = 200, 20
        bx = (WIDTH - bar_w)//2
        by = HEIGHT - bar_h - 10
        pygame.draw.rect(screen, BOSS_BAR_BG, (bx,by,bar_w,bar_h))
        fill = int(bar_w * boss.health / BOSS_HIT_POINTS)
        pygame.draw.rect(screen, BOSS_BAR_FILL, (bx,by,fill,bar_h))

    hud = font.render(f"Score: {delivered}", True, TEXT_COLOR)
    screen.blit(hud, (10,10))

    if player.has_boomerang:
        icon = pygame.transform.scale(BOOMERANG_IMAGE, (24,24))
        screen.blit(icon, (10 + hud.get_width()+10, 8))
    if pygame.time.get_ticks() < player.boost_end_time:
        sb_icon = pygame.transform.scale(NOS_IMAGE, (24,24))
        screen.blit(sb_icon, (10 + hud.get_width()+40, 8))

    if delay_event and player.carrying and pygame.sprite.collide_rect(player,cashier):
        banner = pygame.Surface((WIDTH,80), pygame.SRCALPHA)
        banner.fill((0,0,0,180))
        screen.blit(banner, (0, HEIGHT//2-40))
        elapsed   = now - delay_event['start_time']
        remaining = max(0, WAIT_TIME- elapsed)
        secs      = (remaining+999)//1000
        msg       = font.render(f"Long line… wait {secs}s or leave & return",
                                True, LONG_LINE_COLOR)
        mx = WIDTH//2 - msg.get_width()//2
        my = HEIGHT//2 - msg.get_height()//2
        screen.blit(msg, (mx, my))
        bx2, by2 = WIDTH//2-150, my+msg.get_height()+10
        pygame.draw.rect(screen,(100,100,100),(bx2, by2, 300,20))
        prog = min(1, elapsed/WAIT_TIME)
        pygame.draw.rect(screen,LONG_LINE_COLOR,(bx2,by2,300*prog,20))

    if game_over:
        over = font.render("Game Over! You got caught! Press ENTER to restart.",
                           True, TEXT_COLOR)
        ox = WIDTH//2 - over.get_width()//2
        oy = HEIGHT//2
        screen.blit(over, (ox, oy))

    pygame.display.flip()
