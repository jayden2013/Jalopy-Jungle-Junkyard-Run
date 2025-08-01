import pygame
import random
import sys
import math

# ─── Configuration ───────────────────────────────────────────────────────────
WIDTH, HEIGHT        = 800, 600
FPS                  = 60
NUM_PARTS            = 5
NUM_ENEMIES          = 3
PLAYER_SPEED         = 4
ENEMY_SPEED          = 2
MIN_ENEMY_SEPARATION = 40    # pixels between regular enemies

# Thief settings
THIEF_SPEED      = 1        # slower than regular enemies
THIEF_COLOR      = (0, 150, 255)
THIEF_DROP_MIN   = 3000     # ms before dropping a stolen part (3s)
THIEF_DROP_MAX   = 30000    # ms before dropping a stolen part (30s)
THIEF_COOLDOWN   = 500      # ms after drop before able to re-steal

# Long-line settings
LINE_PROBABILITY   = 0.5
WAIT_TIME          = 1200   # now 1.2 seconds
COME_BACK_DELAY    = 5000

# Colors
BG_COLOR        = (50, 50, 50)
PLAYER_COLOR    = (0, 200, 0)
TEXT_COLOR      = (255, 255, 255)
LONG_LINE_COLOR = (255, 50, 50)
# ──────────────────────────────────────────────────────────────────────────────

pygame.init()
screen     = pygame.display.set_mode((WIDTH, HEIGHT))
clock      = pygame.time.Clock()
font       = pygame.font.SysFont(None, 36)

# ─── Star Wars–style Intro ───────────────────────────────────────────────────
intro_font    = pygame.font.SysFont(None, 24, bold=True)
intro_lines   = [
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
intro_surfs   = [intro_font.render(line, True, (255, 255, 0)) for line in intro_lines]
scroll_y      = HEIGHT
scroll_speed  = 0.05  # pixels per ms
state_intro   = True
# ──────────────────────────────────────────────────────────────────────────────

# ─── Load assets ─────────────────────────────────────────────────────────────
background = pygame.image.load("assets/background.png").convert()
background = pygame.transform.scale(background, (WIDTH, HEIGHT))

PART_IMAGE_FILES = ["assets/part1.png", "assets/part2.png", "assets/part3.png"]
part_textures    = []
for fn in PART_IMAGE_FILES:
    tex = pygame.image.load(fn).convert_alpha()
    tex = pygame.transform.scale(tex, (20, 20))
    part_textures.append(tex)
# ──────────────────────────────────────────────────────────────────────────────

# ─── Helpers & Globals ────────────────────────────────────────────────────────
def normalize(vx, vy):
    dist = math.hypot(vx, vy)
    return (vx/dist, vy/dist) if dist else (0,0)

delay_event         = None   # for long-line mechanic
current_carried_img = None   # sprite held by player
delivered           = 0
game_over           = False
# ──────────────────────────────────────────────────────────────────────────────

# ─── Game Objects ──────────────────────────────────────────────────────────────
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        diameter = 30
        self.image = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        pygame.draw.circle(
            self.image,
            PLAYER_COLOR,
            (diameter//2, diameter//2),
            diameter//2
        )
        self.rect     = self.image.get_rect(center=(WIDTH//2, HEIGHT//2))
        self.carrying = False

    def update(self, keys):
        dx = dy = 0
        if keys[pygame.K_LEFT]:   dx = -PLAYER_SPEED
        if keys[pygame.K_RIGHT]:  dx =  PLAYER_SPEED
        if keys[pygame.K_UP]:      dy = -PLAYER_SPEED
        if keys[pygame.K_DOWN]:    dy =  PLAYER_SPEED
        old = self.rect.topleft
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
            dropped.image            = self.carried_image
            dropped.rect             = dropped.image.get_rect(center=self.rect.center)
            dropped.forbidden_thief  = self
            parts.add(dropped); all_sprites.add(dropped)
            self.carrying            = False
            self.carried_image       = None
            self.drop_time           = None
            self.cooldown_until      = now + THIEF_COOLDOWN
            return

        # Steal & ground-steal logic (only when not carrying)
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
                target = min(candidates, key=lambda p:
                             (p.rect.centerx-self.rect.centerx)**2
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
        if bounced or random.random() < 0.02:
            ang = random.uniform(0, 2*math.pi)
            dir_x, dir_y = math.cos(ang), math.sin(ang)
        self.direction = (dir_x, dir_y)

class Cashier(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = pygame.Surface((30,30), pygame.SRCALPHA)
        self.rect  = self.image.get_rect(center=pos)

# ─── Setup & Handlers ───────────────────────────────────────────────────────
player  = Player()
cashier = Cashier((20, HEIGHT-20))

def handle_delivery():
    global delivered, delay_event, current_carried_img
    delivered += 1

    # spawn a new thief every 10 parts delivered
    if delivered % 10 == 0:
        tx = random.randint(50, WIDTH-50)
        ty = random.randint(50, HEIGHT-50)
        new_thief = Thief((tx, ty))
        thieves.add(new_thief)
        all_sprites.add(new_thief)

    delay_event         = None
    current_carried_img = None
    player.carrying     = False
    x, y = random.randint(50, WIDTH-150), random.randint(50, HEIGHT-150)
    p = Part((x,y)); parts.add(p); all_sprites.add(p)
    e = Enemy((WIDTH-15,15)); enemies.add(e); all_sprites.add(e)

def reset_game():
    global parts, enemies, thieves, all_sprites, delivered, game_over, delay_event, current_carried_img
    delivered           = 0
    game_over           = False
    delay_event         = None
    current_carried_img = None
    player.rect.center  = (WIDTH//2, HEIGHT//2)
    player.carrying     = False

    all_sprites = pygame.sprite.Group(player, cashier)

    # parts
    parts = pygame.sprite.Group()
    for _ in range(NUM_PARTS):
        x, y = random.randint(50, WIDTH-150), random.randint(50, HEIGHT-150)
        p = Part((x,y)); parts.add(p); all_sprites.add(p)

    # enemies (safe distance from player)
    enemies = pygame.sprite.Group()
    safe_dist = 150
    for _ in range(NUM_ENEMIES):
        while True:
            ex = random.randint(50, WIDTH-50)
            ey = random.randint(50, HEIGHT-50)
            if math.hypot(ex - WIDTH//2, ey - HEIGHT//2) > safe_dist:
                break
        e = Enemy((ex,ey)); enemies.add(e); all_sprites.add(e)

    # single thief
    thieves = pygame.sprite.Group()
    tx, ty = random.randint(50, WIDTH-50), random.randint(50, HEIGHT-50)
    t = Thief((tx,ty)); thieves.add(t); all_sprites.add(t)

    globals().update({
        'parts': parts,
        'enemies': enemies,
        'thieves': thieves,
        'all_sprites': all_sprites
    })

# ─── Main Loop ───────────────────────────────────────────────────────────────
reset_game()
while True:
    dt = clock.tick(FPS)

    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
            if state_intro:
                state_intro = False
            elif game_over:
                reset_game()

    # Intro (only happens once)
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

    # ─── Game Update (frozen on Game Over) ──────────────────────────────
    if not game_over:
        keys    = pygame.key.get_pressed()
        old_pos = player.rect.topleft
        player.update(keys)

        # thief steals only if not already carrying
        now = pygame.time.get_ticks()
        for t in thieves:
            if (player.carrying
                and not t.carrying
                and player.rect.colliderect(t.rect)):
                t.carrying      = True
                t.carried_image = current_carried_img
                player.carrying = False
                current_carried_img = None
                t.drop_time = now + random.randint(THIEF_DROP_MIN, THIEF_DROP_MAX)

        # block through thieves
        if pygame.sprite.spritecollideany(player, thieves):
            player.rect.topleft = old_pos

        # update enemies
        for e in enemies:
            dx, dy = player.rect.centerx - e.rect.centerx, player.rect.centery - e.rect.centery
            nx, ny = normalize(dx, dy)
            mvx, mvy = nx*ENEMY_SPEED, ny*ENEMY_SPEED
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
            e.rect.x += mvx; e.rect.y += mvy

        # update thieves
        for t in thieves:
            t.update()

        # pickup/delivery
        if not player.carrying:
            hit = pygame.sprite.spritecollideany(player, parts)
            if hit:
                current_carried_img = hit.image
                hit.kill()
                player.carrying = True
        else:
            now = pygame.time.get_ticks()
            if delay_event is None and pygame.sprite.collide_rect(player, cashier):
                if random.random() < LINE_PROBABILITY:
                    delay_event = {'start_time': now, 'next_available_time': now + COME_BACK_DELAY}
                else:
                    handle_delivery()
            elif delay_event and pygame.sprite.collide_rect(player, cashier):
                if (now - delay_event['start_time'] >= WAIT_TIME
                    or now >= delay_event['next_available_time']):
                    handle_delivery()

        if pygame.sprite.spritecollideany(player, enemies):
            game_over = True

    # ─── Rendering ────────────────────────────────────────────────────────────
    screen.blit(background, (0,0))

    # glow + parts
    for part in parts:
        glow_rect = part.glow.get_rect(center=part.rect.center)
        screen.blit(part.glow, glow_rect)
    all_sprites.draw(screen)

    # thief’s carried part
    for t in thieves:
        if t.carrying and t.carried_image:
            ix = t.rect.centerx - t.carried_image.get_width()//2
            iy = t.rect.centery - t.carried_image.get_height()//2
            screen.blit(t.carried_image, (ix, iy))

    # player’s carried part
    if player.carrying and current_carried_img:
        px = player.rect.centerx - current_carried_img.get_width()//2
        py = player.rect.top - current_carried_img.get_height() - 5
        screen.blit(current_carried_img, (px, py))

    # HUD
    hud = font.render(f"Score: {delivered}", True, TEXT_COLOR)
    screen.blit(hud, (10,10))

    # long-line overlay
    if delay_event and player.carrying and pygame.sprite.collide_rect(player, cashier):
        now = pygame.time.get_ticks()
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

    # Game Over message
    if game_over:
        over = font.render(
            "Game Over! You got caught!  Press ENTER to restart.",
            True, TEXT_COLOR
        )
        ox = WIDTH//2 - over.get_width()//2
        oy = HEIGHT//2
        screen.blit(over, (ox, oy))

    pygame.display.flip()
