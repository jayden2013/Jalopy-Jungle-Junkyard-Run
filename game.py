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
THIEF_SPEED      = 1        # slower than regular enemies
THIEF_COLOR      = (0, 150, 255)
THIEF_DROP_MIN   = 3000     # ms before dropping a stolen part
THIEF_DROP_MAX   = 30000    # ms before dropping a stolen part
THIEF_COOLDOWN   = 500      # ms after drop before able to re-steal

# Long-line settings
LINE_PROBABILITY   = 0.5
WAIT_TIME          = 1200    # ms before able to deliver or leave & return
COME_BACK_DELAY    = 5000    # ms long-line max wait

# Chair drop settings
CHAIR_DROP_INTERVAL   = 10000  # ms between chair-drop waves
CHAIR_DROP_CHANCE     = 0.5    # each enemy has 50% chance to drop
CHAIR_INVINCIBILITY   = 2000   # ms chairs are invincible after being placed

# Chair highlight settings
CHAIR_GLOW_RADIUS     = 25
CHAIR_GLOW_COLOR      = (255, 255, 0, 100)   # yellow, semi-transparent

# Boomerang settings
BOOMERANG_SPAWN_INTERVAL = 20000   # ms between spawn attempts
BOOMERANG_SPAWN_CHANCE   = 0.3     # 30% chance each interval
BOOMERANG_RESPAWN_DELAY  = 10000   # ms before a hit enemy respawns
BOOMERANG_SPEED          = 0.015   # controls flight & return speed

# Speed-boost settings
SPEEDBOOST_SPAWN_INTERVAL = 30000   # ms between spawn attempts
SPEEDBOOST_SPAWN_CHANCE   = 0.2     # 20% chance each interval
SPEEDBOOST_DURATION       = 10000    # ms boost lasts
SPEEDBOOST_MULTIPLIER     = 2.0     # speed × multiplier

# Colors
BG_COLOR         = (50, 50, 50)
PLAYER_COLOR     = (0, 200, 0)
TEXT_COLOR       = (255, 255, 255)
LONG_LINE_COLOR  = (255, 50, 50)
# ─────────────────────────────────────────────────────────────────────────────

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock  = pygame.time.Clock()
font   = pygame.font.SysFont(None, 36)

# ─── Star Wars–style Intro ───────────────────────────────────────────────────
intro_font  = pygame.font.SysFont(None, 24, bold=True)
intro_lines = [
    "A long time ago, in a junkyard far, far away...",
    "",
    "You are the last guardian of the pristine MN12 Thunderbird.",
    "Its polished panels gleam in the dusty sunlight.",
    "",
    "But the Boomers, with their rusty relics, plot to seize its parts",
    "to fuel their sloppy rebuilds of their undead Thunderbirds.",
    "",
    "Time is short. Scour the yard, collect the parts,",
    "and assemble the final masterpiece",
    "before they strike!",
    "",
    "Press ENTER to begin..."
]
intro_surfs  = [intro_font.render(line, True, (255, 255, 0)) for line in intro_lines]
scroll_y     = HEIGHT
scroll_speed = 0.05  # pixels per ms
state_intro  = True
# ─────────────────────────────────────────────────────────────────────────────

# ─── Load assets ─────────────────────────────────────────────────────────────
background = pygame.image.load("assets/background.png").convert()
background = pygame.transform.scale(background, (WIDTH, HEIGHT))

PART_IMAGE_FILES = ["assets/part1.png", "assets/part2.png", "assets/part3.png"]
part_textures    = []
for fn in PART_IMAGE_FILES:
    tex = pygame.image.load(fn).convert_alpha()
    tex = pygame.transform.scale(tex, (20, 20))
    part_textures.append(tex)

# load chair PNG
CHAIR_IMAGE = pygame.image.load("assets/chair.png").convert_alpha()
CHAIR_IMAGE = pygame.transform.scale(CHAIR_IMAGE, (20, 20))

# load boomerang PNG
BOOMERANG_IMAGE = pygame.image.load("assets/boomerang.png").convert_alpha()
BOOMERANG_IMAGE = pygame.transform.scale(BOOMERANG_IMAGE, (20, 20))

# load NOS speed‐boost icon
NOS_IMAGE = pygame.image.load("assets/nos.png").convert_alpha()
NOS_IMAGE = pygame.transform.scale(NOS_IMAGE, (20, 20))

# load player sprite
PLAYER_IMAGE = pygame.image.load("assets/player.png").convert_alpha()
PLAYER_IMAGE = pygame.transform.scale(PLAYER_IMAGE, (30, 30))
# ─────────────────────────────────────────────────────────────────────────────

# ─── Helpers & Globals ────────────────────────────────────────────────────────
def normalize(vx, vy):
    dist = math.hypot(vx, vy)
    return (vx/dist, vy/dist) if dist else (0,0)

delay_event         = None
current_carried_img = None
delivered           = 0
game_over           = False
last_chair_drop     = pygame.time.get_ticks()
last_boom_spawn     = pygame.time.get_ticks()
last_speed_spawn    = pygame.time.get_ticks()
respawns            = []

# placeholder globals for sprite groups
parts                 = None
enemies               = None
thieves               = None
chairs                = None
boomerangs            = None
boomerang_projectiles = None
speed_items           = None
all_sprites           = None
# ──────────────────────────────────────────────────────────────────────────────

# ─── Game Objects ────────────────────────────────────────────────────────────
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # use the loaded sprite instead of drawing a circle
        self.image = PLAYER_IMAGE
        self.rect  = self.image.get_rect(center=(WIDTH//2, HEIGHT//2))
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
        self.forbidden_thief = None
        glow_r = 20
        self.glow = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
        pygame.draw.circle(self.glow, (255,255,0,100),
                           (glow_r, glow_r), glow_r)

class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = pygame.Surface((30,30), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (200,0,0), (15,15), 15)
        self.rect  = self.image.get_rect(center=pos)

class Thief(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image          = pygame.Surface((30,30), pygame.SRCALPHA)
        pygame.draw.circle(self.image, THIEF_COLOR, (15,15), 15)
        self.rect           = self.image.get_rect(center=pos)
        angle               = random.uniform(0, 2*math.pi)
        self.direction      = (math.cos(angle), math.sin(angle))
        self.carrying       = False
        self.carried_image  = None
        self.drop_time      = None
        self.cooldown_until = 0

    def update(self):
        now = pygame.time.get_ticks()

        # Drop logic
        if self.carrying and now >= self.drop_time:
            dropped = Part(self.rect.center)
            dropped.image           = self.carried_image
            dropped.rect            = dropped.image.get_rect(center=self.rect.center)
            dropped.forbidden_thief = self
            parts.add(dropped); all_sprites.add(dropped)
            self.carrying           = False
            self.carried_image      = None
            self.drop_time          = None
            self.cooldown_until     = now + THIEF_COOLDOWN
            return

        # Steal logic
        if now >= self.cooldown_until and not self.carrying:
            if player.carrying and self.rect.colliderect(player.rect):
                self.carrying      = True
                self.carried_image = current_carried_img
                player.carrying    = False
                self.drop_time     = now + random.randint(THIEF_DROP_MIN, THIEF_DROP_MAX)
            else:
                for p in parts:
                    if p.forbidden_thief is self: continue
                    if self.rect.colliderect(p.rect):
                        self.carrying      = True
                        self.carried_image = p.image
                        p.kill()
                        self.drop_time     = now + random.randint(THIEF_DROP_MIN, THIEF_DROP_MAX)
                        break

        # Movement
        if not self.carrying:
            candidates = [p for p in parts if p.forbidden_thief is not self]
            if candidates:
                target = min(candidates,
                             key=lambda p: (p.rect.centerx - self.rect.centerx)**2
                                         + (p.rect.centery - self.rect.centery)**2)
                dx, dy = target.rect.centerx - self.rect.centerx, target.rect.centery - self.rect.centery
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
        if bounced or random.random() < 0.02:
            ang = random.uniform(0, 2*math.pi)
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
        self.spawn_time = pygame.time.get_ticks()
        # glow halo
        self.glow = pygame.Surface((CHAIR_GLOW_RADIUS*2, CHAIR_GLOW_RADIUS*2),
                                   pygame.SRCALPHA)
        pygame.draw.circle(self.glow, CHAIR_GLOW_COLOR,
                           (CHAIR_GLOW_RADIUS, CHAIR_GLOW_RADIUS),
                           CHAIR_GLOW_RADIUS)

class BoomerangItem(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = BOOMERANG_IMAGE
        self.rect  = self.image.get_rect(center=pos)
        glow_r = 25
        self.glow = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
        pygame.draw.circle(self.glow, CHAIR_GLOW_COLOR,
                           (glow_r, glow_r), glow_r)

class BoomerangProjectile(pygame.sprite.Sprite):
    def __init__(self, start_pos):
        super().__init__()
        self.image = BOOMERANG_IMAGE
        self.rect  = self.image.get_rect(center=start_pos)
        self.start    = pygame.math.Vector2(start_pos)
        self.end      = pygame.math.Vector2(start_pos)
        mx, my       = pygame.mouse.get_pos()
        dirv         = pygame.math.Vector2(mx, my) - self.start
        if dirv.length() == 0:
            dirv = pygame.math.Vector2(1,0)
        dirv         = dirv.normalize() * 150
        self.control = self.start + dirv + pygame.math.Vector2(0, -75)
        self.t        = 0.0
        self.speed    = BOOMERANG_SPEED
        self.returning = False

    def update(self):
        now = pygame.time.get_ticks()
        if not self.returning:
            self.t += self.speed
            if self.t >= 1.0:
                self.t       = 1.0
                self.returning = True
        else:
            self.t -= self.speed
            if self.t <= 0.0:
                self.kill()
                return

        p = (self.start * (1-self.t)**2 +
             self.control * 2*(1-self.t)*self.t +
             self.end * self.t**2)
        self.rect.center = (round(p.x), round(p.y))

        hit = pygame.sprite.spritecollideany(self, enemies)
        if hit:
            hit.kill()
            respawns.append(now + BOOMERANG_RESPAWN_DELAY)

class SpeedBoostItem(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = NOS_IMAGE
        self.rect  = self.image.get_rect(center=pos)
        glow_r = 25
        self.glow = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
        pygame.draw.circle(self.glow, (255,150,0,120),
                           (glow_r, glow_r), glow_r)
# ──────────────────────────────────────────────────────────────────────────────

def handle_delivery():
    global delivered, delay_event, current_carried_img
    delivered += 1
    if delivered % 10 == 0:
        tx = random.randint(50, WIDTH-50)
        ty = random.randint(50, HEIGHT-50)
        new_thief = Thief((tx, ty))
        thieves.add(new_thief); all_sprites.add(new_thief)

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

    delivered            = 0
    game_over            = False
    delay_event          = None
    current_carried_img  = None
    last_chair_drop      = pygame.time.get_ticks()
    last_boom_spawn      = pygame.time.get_ticks()
    last_speed_spawn     = pygame.time.get_ticks()
    respawns.clear()

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
            if math.hypot(ex - WIDTH//2, ey - HEIGHT//2) > safe_dist:
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

    # spawn initial boomerang
    bx = random.randint(50, WIDTH-50)
    by = random.randint(50, HEIGHT-50)
    b  = BoomerangItem((bx,by))
    boomerangs.add(b); all_sprites.add(b)

# initialize everything
player  = Player()
cashier = Cashier((20, HEIGHT-20))
reset_game()

# ─── Main Loop ───────────────────────────────────────────────────────────────
while True:
    dt  = clock.tick(FPS)
    now = pygame.time.get_ticks()

    # Event Handling
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

    # Intro Scene
    if state_intro:
        scroll_y -= dt * scroll_speed
        screen.fill((0,0,0))
        for i, surf in enumerate(intro_surfs):
            x = (WIDTH - surf.get_width()) // 2
            y = scroll_y + i * 30
            screen.blit(surf, (x, y))
        if scroll_y + len(intro_surfs)*30 < 0:
            state_intro = False
        pygame.display.flip()
        continue

    # Game Update
    if not game_over:
        keys    = pygame.key.get_pressed()
        old_pos = player.rect.topleft
        player.update(keys)

        # block through chairs
        if pygame.sprite.spritecollideany(player, chairs):
            player.rect.topleft = old_pos

        # block through thieves
        if pygame.sprite.spritecollideany(player, thieves):
            player.rect.topleft = old_pos

        # thief-steal fallback
        for t in thieves:
            if (player.carrying and not t.carrying
                and player.rect.colliderect(t.rect)):
                t.carrying      = True
                t.carried_image = current_carried_img
                player.carrying = False
                current_carried_img = None
                t.drop_time = now + random.randint(THIEF_DROP_MIN, THIEF_DROP_MAX)

        # update enemies
        for e in enemies:
            dx, dy = player.rect.centerx - e.rect.centerx, player.rect.centery - e.rect.centery
            nx, ny = normalize(dx, dy)
            mvx, mvy = nx*ENEMY_SPEED, ny*ENEMY_SPEED

            # separation
            sx = sy = 0
            for o in enemies:
                if o is not e:
                    dx2, dy2 = e.rect.centerx - o.rect.centerx, e.rect.centery - o.rect.centery
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

            # clear chairs after invincibility
            hit_chair = pygame.sprite.spritecollideany(e, chairs)
            if hit_chair and now - hit_chair.spawn_time >= CHAIR_INVINCIBILITY:
                hit_chair.kill()

        # drop chairs periodically
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
            hit = pygame.sprite.spritecollideany(player, parts)
            if hit:
                current_carried_img = hit.image
                hit.kill()
                player.carrying = True
        else:
            if delay_event is None and pygame.sprite.collide_rect(player, cashier):
                if random.random() < LINE_PROBABILITY:
                    delay_event = {
                        'start_time': now,
                        'next_available_time': now + COME_BACK_DELAY
                    }
                else:
                    handle_delivery()
            elif delay_event and pygame.sprite.collide_rect(player, cashier):
                elapsed = now - delay_event['start_time']
                if elapsed >= WAIT_TIME or now >= delay_event['next_available_time']:
                    handle_delivery()

        # spawn boomerang pickups
        if now - last_boom_spawn >= BOOMERANG_SPAWN_INTERVAL:
            if (random.random() < BOOMERANG_SPAWN_CHANCE
                and not boomerangs and not player.has_boomerang):
                bx = random.randint(50, WIDTH-50)
                by = random.randint(50, HEIGHT-50)
                b  = BoomerangItem((bx,by))
                boomerangs.add(b); all_sprites.add(b)
            last_boom_spawn = now

        # pickup boomerang
        if not player.has_boomerang and not boomerang_projectiles:
            hit_b = pygame.sprite.spritecollideany(player, boomerangs)
            if hit_b:
                player.has_boomerang = True
                hit_b.kill()

        # update boomerang projectiles
        for proj in boomerang_projectiles:
            proj.update()

        # spawn speed-boost pickups
        if now - last_speed_spawn >= SPEEDBOOST_SPAWN_INTERVAL:
            if random.random() < SPEEDBOOST_SPAWN_CHANCE and not speed_items:
                sx = random.randint(50, WIDTH-50)
                sy = random.randint(50, HEIGHT-50)
                sb = SpeedBoostItem((sx,sy))
                speed_items.add(sb); all_sprites.add(sb)
            last_speed_spawn = now

        # pickup speed-boost
        hit_sb = pygame.sprite.spritecollideany(player, speed_items)
        if hit_sb:
            hit_sb.kill()
            player.speed_multiplier = SPEEDBOOST_MULTIPLIER
            player.boost_end_time   = now + SPEEDBOOST_DURATION

        # handle enemy respawns
        for ts in respawns[:]:
            if now >= ts:
                while True:
                    ex = random.randint(50, WIDTH-50)
                    ey = random.randint(50, HEIGHT-50)
                    if math.hypot(ex - player.rect.centerx, ey - player.rect.centery) > 150:
                        break
                new_e = Enemy((ex, ey))
                enemies.add(new_e); all_sprites.add(new_e)
                respawns.remove(ts)

        # check for game over
        if pygame.sprite.spritecollideany(player, enemies):
            game_over = True

    # ── Rendering ───────────────────────────────────────────────────────────────
    screen.blit(background, (0,0))

    # glow around parts
    for part in parts:
        glow_rect = part.glow.get_rect(center=part.rect.center)
        screen.blit(part.glow, glow_rect)

    # glow around chairs
    for chair in chairs:
        glow_rect = chair.glow.get_rect(center=chair.rect.center)
        screen.blit(chair.glow, glow_rect)

    # glow around boomerang pickups
    for b in boomerangs:
        glow_rect = b.glow.get_rect(center=b.rect.center)
        screen.blit(b.glow, glow_rect)

    # glow around speed-boost items
    for sb in speed_items:
        glow_rect = sb.glow.get_rect(center=sb.rect.center)
        screen.blit(sb.glow, glow_rect)

    all_sprites.draw(screen)

    # draw thief-carried parts
    for t in thieves:
        if t.carrying and t.carried_image:
            ix = t.rect.centerx - t.carried_image.get_width()//2
            iy = t.rect.centery - t.carried_image.get_height()//2
            screen.blit(t.carried_image, (ix, iy))

    # draw player-carried part
    if player.carrying and current_carried_img:
        px = player.rect.centerx - current_carried_img.get_width()//2
        py = player.rect.top   - current_carried_img.get_height() - 5
        screen.blit(current_carried_img, (px, py))

    # HUD: Score
    hud = font.render(f"Score: {delivered}", True, TEXT_COLOR)
    screen.blit(hud, (10,10))

    # Weapon overlay: boomerang icon
    if player.has_boomerang:
        icon = pygame.transform.scale(BOOMERANG_IMAGE, (24,24))
        screen.blit(icon, (10 + hud.get_width() + 10, 8))

    # Speed-boost overlay: NOS icon when active
    if pygame.time.get_ticks() < player.boost_end_time:
        sb_icon = pygame.transform.scale(NOS_IMAGE, (24,24))
        screen.blit(sb_icon, (10 + hud.get_width() + 40, 8))

    # long-line overlay
    if delay_event and player.carrying and pygame.sprite.collide_rect(player, cashier):
        banner = pygame.Surface((WIDTH,80), pygame.SRCALPHA)
        banner.fill((0,0,0,180))
        screen.blit(banner, (0, HEIGHT//2 - 40))
        elapsed   = now - delay_event['start_time']
        remaining = max(0, WAIT_TIME - elapsed)
        secs      = (remaining + 999)//1000
        msg_text  = f"Long line… wait {secs}s or leave & return"
        msg       = font.render(msg_text, True, LONG_LINE_COLOR)
        mx = WIDTH//2 - msg.get_width()//2
        my = HEIGHT//2 - msg.get_height()//2
        screen.blit(msg, (mx, my))
        bx, by = WIDTH//2 - 150, my + msg.get_height() + 10
        pygame.draw.rect(screen, (100,100,100), (bx, by, 300, 20))
        prog = min(1, elapsed / WAIT_TIME)
        pygame.draw.rect(screen, LONG_LINE_COLOR, (bx, by, 300*prog, 20))

    # game over message
    if game_over:
        over = font.render(
            "Game Over! You got caught!  Press ENTER to restart.",
            True, TEXT_COLOR
        )
        ox = WIDTH//2 - over.get_width()//2
        oy = HEIGHT//2
        screen.blit(over, (ox, oy))

    pygame.display.flip()
