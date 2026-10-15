"""
Pipiripium - MVP con laberinto artesanal + puzzle + boss
Requiere: pygame
Controles:
  WASD/Flechas -> mover
  Ratón        -> apuntar
  Click/Space  -> atacar
  ESC          -> salir

Objetivo del laberinto:
  1) Pisar las 3 placas (P) repartidas por el mapa.
  2) Al activarlas todas, se abre la puerta (D) inferior.
  3) Derrotar al boss (B) en la cámara final.
  4) Alcanzar la salida (X) de la esquina inferior derecha.

Señalización/relay: usa tu servidor STUN existente (TCP relay).
"""
import pygame, socket, threading, json, math, time, sys, random

# ==================== CONFIG ====================
RELAY_IP = "XX.XX.XX.XX"
RELAY_PORT = 5000

TILE = 32
FPS = 60
NET_HZ = 30
NET_DT = 1.0 / NET_HZ

# Combate
ATTACK_CD = 0.45
ATTACK_DURATION = 0.22
ATTACK_RANGE = 82
ARC_DEG = 110
DMG_ENEMY = 20
DMG_BOSS = 12
DMG_PVP = 15

PLAYER_SPEED = 220
PLAYER_RADIUS = 13
PLAYER_HP = 100

ENEMY_SPEED = 85
ENEMY_HP = 50
ENEMY_RADIUS = 12
ENEMY_TOUCH_DPS = 30

BOSS_SPEED = 62
BOSS_HP = 220
BOSS_RADIUS = 22
BOSS_TOUCH_DPS = 45

# Colores
C_BG = (14, 14, 22)
C_FLOOR = (26, 26, 38)
C_FLOOR_ALT = (31, 31, 46)
C_WALL = (58, 58, 82)
C_WALL_TOP = (82, 82, 110)
C_LOCAL = (90, 220, 255)
C_REMOTE = (255, 110, 200)
C_ATTACK = (255, 240, 120)
C_ENEMY = (255, 70, 70)
C_BOSS = (200, 60, 220)
C_DOOR_LOCKED = (190, 60, 60)
C_DOOR_OPEN = (100, 220, 140)
C_PLATE_OFF = (95, 95, 125)
C_PLATE_ON = (255, 220, 120)
C_EXIT_LOCK = (55, 55, 75)
C_EXIT = (100, 255, 140)
C_TEXT = (235, 235, 245)
C_DIM = (150, 150, 170)

# Mapa: 32x24 tiles
#  #  muro         .  suelo       S  spawn
#  e  enemigo      B  boss        P  placa (puzzle)
#  D  puerta       X  salida
MAP_STR = """\
################################
#..............................#
#..S...........................#
#..............................#
#..............................#
#..............e...............#
#..............................#
#..............................#
#....P.................P.......#
#..............................#
#..............................#
#..............e...............#
#..............................#
#..............................#
#..............P...............#
#..............................#
#..............................#
###############DD###############
#..............................#
#..............................#
#..............B...............#
#..............................#
#............................X.#
################################
"""


# ==================== NETWORK ====================
class Network:
    def __init__(self, ip, port):
        self.ip, self.port = ip, port
        self.sock = None
        self.running = False
        self.paired = False
        self.lock = threading.Lock()
        self.inbox = []
        self.outbox = []

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.ip, self.port))
        except Exception as e:
            print(f"[NET] no se pudo conectar: {e}")
            return False
        self.running = True
        threading.Thread(target=self._recv_loop, daemon=True).start()
        threading.Thread(target=self._send_loop, daemon=True).start()
        print(f"[NET] conectado a {self.ip}:{self.port}. Esperando peer...")
        return True

    def _recv_loop(self):
        buf = b""
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    self.running = False
                    break
                buf += data
                if not self.paired and b"CONECTADO" in buf:
                    i = buf.find(b"CONECTADO")
                    j = buf.find(b"\n", i)
                    j = j + 1 if j != -1 else i + len(b"CONECTADO")
                    buf = buf[:i] + buf[j:]
                    self.paired = True
                    print("[NET] emparejado.")
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line.decode("utf-8"))
                        with self.lock:
                            self.inbox.append(msg)
                    except Exception as e:
                        print(f"[NET] msg inválido: {e}")
            except Exception as e:
                print(f"[NET] recv err: {e}")
                self.running = False
                break

    def _send_loop(self):
        while self.running:
            msg = None
            with self.lock:
                if self.outbox:
                    msg = self.outbox.pop(0)
            if msg is None:
                time.sleep(0.004)
                continue
            try:
                self.sock.sendall(msg)
            except Exception as e:
                print(f"[NET] send err: {e}")
                self.running = False
                break

    def send(self, obj):
        if not self.running:
            return
        data = (json.dumps(obj) + "\n").encode("utf-8")
        with self.lock:
            self.outbox.append(data)

    def poll(self):
        with self.lock:
            msgs = self.inbox[:]
            self.inbox.clear()
        return msgs

    def close(self):
        self.running = False
        try:
            if self.sock: self.sock.close()
        except: pass


# ==================== TILEMAP ====================
class Tilemap:
    def __init__(self, s):
        rows = s.strip("\n").split("\n")
        self.grid = [list(r) for r in rows]
        self.h = len(self.grid)
        self.w = len(self.grid[0])
        self.door_tiles = []
        self.exit_tiles = []
        self.spawns = []
        self.enemy_spawns = []
        self.boss_spawn = None
        self.plate_tiles = []
        for y in range(self.h):
            for x in range(self.w):
                c = self.grid[y][x]
                if c == 'D':   self.door_tiles.append((x, y))
                elif c == 'X': self.exit_tiles.append((x, y))
                elif c == 'S': self.spawns.append((x, y))
                elif c == 'e': self.enemy_spawns.append((x, y))
                elif c == 'B': self.boss_spawn = (x, y)
                elif c == 'P': self.plate_tiles.append((x, y))

    def solid(self, tx, ty, door_open):
        if tx < 0 or ty < 0 or tx >= self.w or ty >= self.h:
            return True
        c = self.grid[ty][tx]
        if c == '#': return True
        if c == 'D' and not door_open: return True
        return False

    def collides(self, cx, cy, r, door_open):
        min_tx = int((cx - r) // TILE)
        max_tx = int((cx + r) // TILE)
        min_ty = int((cy - r) // TILE)
        max_ty = int((cy + r) // TILE)
        for ty in range(min_ty, max_ty + 1):
            for tx in range(min_tx, max_tx + 1):
                if self.solid(tx, ty, door_open):
                    rect = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
                    circle_rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
                    if rect.colliderect(circle_rect):
                        return True
        return False

    def try_move(self, x, y, dx, dy, r, door_open):
        nx = x + dx
        if not self.collides(nx, y, r, door_open):
            x = nx
        ny = y + dy
        if not self.collides(x, ny, r, door_open):
            y = ny
        return x, y

    def draw(self, surf, door_open, plates_state, boss_dead):
        for y in range(self.h):
            for x in range(self.w):
                c = self.grid[y][x]
                px, py = x * TILE, y * TILE
                if c == '#':
                    pygame.draw.rect(surf, C_WALL, (px, py, TILE, TILE))
                    pygame.draw.rect(surf, C_WALL_TOP, (px, py, TILE, 4))
                elif c == 'D':
                    color = C_DOOR_OPEN if door_open else C_DOOR_LOCKED
                    pygame.draw.rect(surf, color, (px + 2, py + 2, TILE - 4, TILE - 4))
                    pygame.draw.rect(surf, (0, 0, 0), (px + 2, py + 2, TILE - 4, TILE - 4), 2)
                elif c == 'X':
                    color = C_EXIT if boss_dead else C_EXIT_LOCK
                    pygame.draw.rect(surf, color, (px + 4, py + 4, TILE - 8, TILE - 8))
                else:
                    color = C_FLOOR_ALT if (x + y) % 2 == 0 else C_FLOOR
                    pygame.draw.rect(surf, color, (px, py, TILE, TILE))

        # Placas (encima del suelo)
        for (tx, ty) in self.plate_tiles:
            key = (tx, ty)
            on = plates_state.get(key, False)
            color = C_PLATE_ON if on else C_PLATE_OFF
            cx, cy = tx * TILE + TILE // 2, ty * TILE + TILE // 2
            pygame.draw.circle(surf, color, (cx, cy), TILE // 2 - 6)
            pygame.draw.circle(surf, (0, 0, 0), (cx, cy), TILE // 2 - 6, 2)


# ==================== ENTIDADES ====================
class Player:
    def __init__(self, x, y, color, name="P"):
        self.x, self.y = x, y
        self.radius = PLAYER_RADIUS
        self.speed = PLAYER_SPEED
        self.hp = PLAYER_HP
        self.max_hp = PLAYER_HP
        self.angle = 0.0
        self.color = color
        self.name = name
        self.attack_timer = 0.0
        self.attack_cd = 0.0
        self.hit_flash = 0.0
        self.dead = False

    def update_local(self, dt, keys, tilemap, door_open):
        if self.dead: return
        dx = dy = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1
        if dx or dy:
            m = math.hypot(dx, dy)
            dx = (dx / m) * self.speed * dt
            dy = (dy / m) * self.speed * dt
            self.x, self.y = tilemap.try_move(self.x, self.y, dx, dy, self.radius, door_open)

        mx, my = pygame.mouse.get_pos()
        self.angle = math.atan2(my - self.y, mx - self.x)

        if self.attack_timer > 0: self.attack_timer -= dt
        if self.attack_cd > 0:    self.attack_cd -= dt
        if self.hit_flash > 0:    self.hit_flash -= dt

    def try_attack(self):
        if self.dead or self.attack_cd > 0:
            return False
        self.attack_cd = ATTACK_CD
        self.attack_timer = ATTACK_DURATION
        return True

    def take_damage(self, amount):
        if self.dead: return
        self.hp -= amount
        self.hit_flash = 0.15
        if self.hp <= 0:
            self.hp = 0
            self.dead = True

    def in_arc(self, tx, ty, target_radius=0):
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d > ATTACK_RANGE + target_radius: return False
        if d < 1: return True
        ang = math.atan2(dy, dx)
        diff = (ang - self.angle + math.pi) % (2 * math.pi) - math.pi
        return abs(diff) < math.radians(ARC_DEG / 2)

    def draw(self, screen, facing=True, label=None):
        c = (255, 255, 255) if self.hit_flash > 0 else self.color
        if self.dead:
            c = (90, 90, 100)
        pygame.draw.circle(screen, c, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, (0, 0, 0), (int(self.x), int(self.y)), self.radius, 2)
        if not self.dead and facing:
            tip = (self.x + math.cos(self.angle) * (self.radius + 10),
                   self.y + math.sin(self.angle) * (self.radius + 10))
            pygame.draw.line(screen, (255, 255, 255), (self.x, self.y), tip, 3)
        if self.attack_timer > 0:
            a0 = self.angle - math.radians(ARC_DEG / 2)
            a1 = self.angle + math.radians(ARC_DEG / 2)
            pygame.draw.arc(screen, C_ATTACK,
                            pygame.Rect(self.x - ATTACK_RANGE, self.y - ATTACK_RANGE,
                                        ATTACK_RANGE * 2, ATTACK_RANGE * 2),
                            -a1, -a0, 4)
        # barra de vida
        bw = 46
        bx, by = self.x - bw / 2, self.y - self.radius - 14
        pygame.draw.rect(screen, (40, 0, 0), (bx, by, bw, 5))
        pygame.draw.rect(screen, (255, 60, 60), (bx, by, bw * (self.hp / self.max_hp), 5))


class Enemy:
    def __init__(self, x, y, eid):
        self.x, self.y = x, y
        self.radius = ENEMY_RADIUS
        self.speed = ENEMY_SPEED
        self.hp = ENEMY_HP
        self.max_hp = ENEMY_HP
        self.id = eid
        self.hit_flash = 0.0

    def update(self, dt, targets, tilemap, door_open):
        if self.hit_flash > 0: self.hit_flash -= dt
        alive = [t for t in targets if not t.dead]
        if not alive: return
        t = min(alive, key=lambda p: (p.x - self.x) ** 2 + (p.y - self.y) ** 2)
        dx, dy = t.x - self.x, t.y - self.y
        d = math.hypot(dx, dy)
        if d > 1:
            mv_x = (dx / d) * self.speed * dt
            mv_y = (dy / d) * self.speed * dt
            self.x, self.y = tilemap.try_move(self.x, self.y, mv_x, mv_y, self.radius, door_open)

    def draw(self, screen):
        c = (255, 255, 255) if self.hit_flash > 0 else C_ENEMY
        pygame.draw.circle(screen, c, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, (60, 0, 0), (int(self.x), int(self.y)), self.radius, 3)
        bw = 36
        bx, by = self.x - bw / 2, self.y - self.radius - 12
        pygame.draw.rect(screen, (40, 0, 0), (bx, by, bw, 4))
        pygame.draw.rect(screen, (255, 60, 60), (bx, by, bw * (self.hp / self.max_hp), 4))


class Boss:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.radius = BOSS_RADIUS
        self.speed = BOSS_SPEED
        self.hp = BOSS_HP
        self.max_hp = BOSS_HP
        self.hit_flash = 0.0
        self.dead = False

    def update(self, dt, targets, tilemap, door_open):
        if self.hit_flash > 0: self.hit_flash -= dt
        if self.dead: return
        alive = [t for t in targets if not t.dead]
        if not alive: return
        t = min(alive, key=lambda p: (p.x - self.x) ** 2 + (p.y - self.y) ** 2)
        dx, dy = t.x - self.x, t.y - self.y
        d = math.hypot(dx, dy)
        if d > 1:
            mv_x = (dx / d) * self.speed * dt
            mv_y = (dy / d) * self.speed * dt
            self.x, self.y = tilemap.try_move(self.x, self.y, mv_x, mv_y, self.radius, door_open)

    def draw(self, screen):
        c = (255, 255, 255) if self.hit_flash > 0 else C_BOSS
        pygame.draw.circle(screen, c, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, (60, 0, 90), (int(self.x), int(self.y)), self.radius, 4)
        # "ojos"
        pygame.draw.circle(screen, (255, 255, 255), (int(self.x - 7), int(self.y - 5)), 3)
        pygame.draw.circle(screen, (255, 255, 255), (int(self.x + 7), int(self.y - 5)), 3)
        bw = 70
        bx, by = self.x - bw / 2, self.y - self.radius - 16
        pygame.draw.rect(screen, (40, 0, 0), (bx, by, bw, 7))
        pygame.draw.rect(screen, (220, 50, 220), (bx, by, bw * (self.hp / self.max_hp), 7))


# ==================== HELPERS ====================
def circle_overlaps_tile(cx, cy, r, tx, ty):
    """Test AABB entre el círculo y la tile."""
    tile_rect = pygame.Rect(tx * TILE, ty * TILE, TILE, TILE)
    circle_rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
    return tile_rect.colliderect(circle_rect)


# ==================== MAIN ====================
def main():
    pygame.init()
    screen = pygame.display.set_mode((TILE * 32, TILE * 24))
    pygame.display.set_caption("Pipiripium - Laberinto MVP")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 14)
    med = pygame.font.SysFont("consolas", 18, bold=True)
    big = pygame.font.SysFont("consolas", 34, bold=True)

    net = Network(RELAY_IP, RELAY_PORT)
    if not net.connect():
        print("Revisa RELAY_IP/PORT.")
        return

    tilemap = Tilemap(MAP_STR)
    spawn_tx, spawn_ty = tilemap.spawns[0]
    spawn_x = spawn_tx * TILE + TILE // 2
    spawn_y = spawn_ty * TILE + TILE // 2

    local = Player(spawn_x, spawn_y, C_LOCAL)
    remote = Player(spawn_x + TILE, spawn_y, C_REMOTE)
    remote.angle = math.pi

    # Enemigos desde spawn del mapa
    enemies = []
    for i, (tx, ty) in enumerate(tilemap.enemy_spawns):
        enemies.append(Enemy(tx * TILE + TILE // 2, ty * TILE + TILE // 2, i))

    boss = None
    if tilemap.boss_spawn:
        bx, by = tilemap.boss_spawn
        boss = Boss(bx * TILE + TILE // 2, by * TILE + TILE // 2)

    plates_state = {(tx, ty): False for (tx, ty) in tilemap.plate_tiles}
    door_open = False
    boss_dead = False
    exit_rects = [pygame.Rect(tx * TILE, ty * TILE, TILE, TILE) for (tx, ty) in tilemap.exit_tiles]

    net_accum = 0.0
    end_state = None
    respawn_timer = 0.0

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)

        # ---------- eventos ----------
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_SPACE:
                    if local.try_attack():
                        net.send({"type": "attack",
                                  "x": round(local.x, 1), "y": round(local.y, 1),
                                  "angle": round(local.angle, 3)})
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if local.try_attack():
                    net.send({"type": "attack",
                              "x": round(local.x, 1), "y": round(local.y, 1),
                              "angle": round(local.angle, 3)})

        keys = pygame.key.get_pressed()
        if not end_state and not local.dead:
            local.update_local(dt, keys, tilemap, door_open)

        # ---------- red entrante ----------
        for msg in net.poll():
            t = msg.get("type")
            if t == "pos":
                remote.x = msg.get("x", remote.x)
                remote.y = msg.get("y", remote.y)
                remote.angle = msg.get("angle", remote.angle)
                hp = msg.get("hp", remote.hp)
                if hp < remote.hp:
                    remote.hit_flash = 0.15
                remote.hp = hp
                remote.dead = (hp <= 0)
            elif t == "attack":
                remote.attack_timer = ATTACK_DURATION
                remote.x = msg.get("x", remote.x)
                remote.y = msg.get("y", remote.y)
                remote.angle = msg.get("angle", remote.angle)
            elif t == "hit_me":
                local.take_damage(msg.get("dmg", DMG_PVP))
            elif t == "hit_e":
                eid = msg.get("eid", -1)
                dmg = msg.get("dmg", DMG_ENEMY)
                if 0 <= eid < len(enemies):
                    e = enemies[eid]
                    e.hp -= dmg
                    e.hit_flash = 0.15
            elif t == "hit_boss":
                if boss and not boss.dead:
                    boss.hp -= msg.get("dmg", DMG_BOSS)
                    boss.hit_flash = 0.15
            elif t == "plate":
                tx, ty = msg.get("tx"), msg.get("ty")
                if (tx, ty) in plates_state:
                    plates_state[(tx, ty)] = True
            elif t == "dead":
                remote.dead = True
                remote.hp = 0

        # ---------- ataques locales ----------
        if local.attack_timer > ATTACK_DURATION * 0.5:
            # PvE
            for e in enemies:
                if e.hp > 0 and e.hit_flash <= 0 and local.in_arc(e.x, e.y, e.radius):
                    e.hp -= DMG_ENEMY
                    e.hit_flash = 0.2
                    net.send({"type": "hit_e", "eid": e.id, "dmg": DMG_ENEMY})
            # Boss
            if boss and not boss.dead and boss.hit_flash <= 0 and local.in_arc(boss.x, boss.y, boss.radius):
                boss.hp -= DMG_BOSS
                boss.hit_flash = 0.2
                net.send({"type": "hit_boss", "dmg": DMG_BOSS})
                if boss.hp <= 0:
                    boss.hp = 0
                    boss.dead = True
                    boss_dead = True
            # PvP
            if (not remote.dead) and local.in_arc(remote.x, remote.y, remote.radius):
                net.send({"type": "hit_me", "dmg": DMG_PVP})

        # ---------- placas de presión ----------
        if not local.dead:
            for (tx, ty) in tilemap.plate_tiles:
                if not plates_state[(tx, ty)]:
                    if circle_overlaps_tile(local.x, local.y, local.radius, tx, ty):
                        plates_state[(tx, ty)] = True
                        net.send({"type": "plate", "tx": tx, "ty": ty})

        # ---------- puerta ----------
        if not door_open and all(plates_state.values()):
            door_open = True

        # ---------- boss ----------
        if boss and not boss.dead and boss_dead:
            boss.dead = True
        if boss and not boss.dead:
            targets = [local, remote]
            boss.update(dt, targets, tilemap, door_open)
            # daño por contacto
            for p in targets:
                if p.dead: continue
                if math.hypot(boss.x - p.x, boss.y - p.y) < boss.radius + p.radius:
                    if p is local:
                        local.take_damage(BOSS_TOUCH_DPS * dt)
                        if local.dead:
                            net.send({"type": "dead"})

        # ---------- enemigos ----------
        for e in enemies:
            if e.hp > 0:
                e.update(dt, [local, remote], tilemap, door_open)
                for p in [local, remote]:
                    if p.dead: continue
                    if math.hypot(e.x - p.x, e.y - p.y) < e.radius + p.radius:
                        if p is local:
                            local.take_damage(ENEMY_TOUCH_DPS * dt)
                            if local.dead:
                                net.send({"type": "dead"})
        # limpiar enemigos muertos
        enemies = [e for e in enemies if e.hp > 0]

        # ---------- respawn local ----------
        if local.dead:
            respawn_timer += dt
            if respawn_timer > 2.5:
                local.dead = False
                local.hp = local.max_hp
                local.x, local.y = spawn_x, spawn_y
                respawn_timer = 0.0
        else:
            respawn_timer = 0.0

        # ---------- red saliente ----------
        net_accum += dt
        if net_accum >= NET_DT:
            net_accum = 0.0
            net.send({"type": "pos",
                      "x": round(local.x, 1), "y": round(local.y, 1),
                      "angle": round(local.angle, 3), "hp": round(local.hp, 1)})

        # ---------- condición de fin ----------
        if not end_state and not local.dead:
            for r in exit_rects:
                if boss_dead and r.colliderect(pygame.Rect(
                        local.x - local.radius, local.y - local.radius,
                        local.radius * 2, local.radius * 2)):
                    end_state = "win"
                    break

        # ---------- render ----------
        screen.fill(C_BG)
        tilemap.draw(screen, door_open, plates_state, boss_dead)

        # enemigos
        for e in enemies: e.draw(screen)
        # boss
        if boss and not boss.dead: boss.draw(screen)

        # jugadores
        remote.draw(screen)
        local.draw(screen)

        # ---- HUD ----
        plates_on = sum(1 for v in plates_state.values() if v)
        plates_total = len(plates_state)
        status = "PAIRED" if net.paired else "Esperando peer..."
        s_color = (100, 255, 140) if net.paired else (255, 200, 100)
        screen.blit(font.render(f"[{status}]", True, s_color), (10, 8))
        screen.blit(font.render(f"HP: {int(local.hp)}/{local.max_hp}", True, C_TEXT), (10, 26))
        screen.blit(font.render(f"Placas: {plates_on}/{plates_total}", True,
                                (255, 220, 120) if plates_on < plates_total else (100, 255, 140)),
                    (10, 44))
        screen.blit(font.render(f"Enemigos: {len(enemies)}", True, C_TEXT), (10, 62))
        if boss and not boss.dead:
            screen.blit(font.render(f"BOSS HP: {int(boss.hp)}/{boss.max_hp}", True, C_BOSS), (10, 80))
        elif boss_dead:
            screen.blit(font.render("BOSS DERROTADO - Ve a la salida", True, (100, 255, 140)), (10, 80))
        screen.blit(font.render("WASD mover | Ratón apuntar | Click/Space atacar | ESC salir",
                                True, C_DIM), (10, TILE * 24 - 22))

        if local.dead and not end_state:
            txt = big.render("RESPAWNING...", True, (255, 100, 100))
            screen.blit(txt, (screen.get_width() // 2 - txt.get_width() // 2,
                              screen.get_height() // 2 - 20))

        if end_state:
            txt = big.render("EXPEDITION COMPLETE", True, (100, 255, 140))
            screen.blit(txt, (screen.get_width() // 2 - txt.get_width() // 2,
                              screen.get_height() // 2 - 20))
            pygame.display.flip()
            pygame.time.wait(2200)
            running = False

        pygame.display.flip()

    net.close()
    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
