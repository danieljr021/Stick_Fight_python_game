import pygame
import sys
import os

pygame.init()

# -------------------
# Configurações
# -------------------
WIDTH, HEIGHT = 1000, 500
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Stick Fight - Melhorado")
FPS = 60
CLOCK = pygame.time.Clock()

# Cores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 20, 60)
GREEN = (34, 177, 76)
BLUE = (30, 120, 220)
YELLOW = (240, 200, 0)

# Fontes
FONT = pygame.font.SysFont(None, 28)
BIG_FONT = pygame.font.SysFont(None, 56)

# Caminhos possíveis para a imagem de fundo (usa a que existir)
BACKGROUND_FILES = ["fundo.png", "ORS97Z0.jpg", "ORS97Z0.png"]
bg_path = None
for f in BACKGROUND_FILES:
    if os.path.exists(f):
        bg_path = f
        break

if bg_path:
    BACKGROUND = pygame.image.load(bg_path).convert()
    BACKGROUND = pygame.transform.scale(BACKGROUND, (WIDTH, HEIGHT))
else:
    BACKGROUND = None  # fallback: desenhar céu/chão simples

# Chão: definimos CHAO_Y baseado na imagem se possível (pode ajustar)
# Se houver fundo, ajuste fino:
CHAO_Y = HEIGHT - 100  # default
if BACKGROUND:
    # tentativa simples: ajuste para que 'chão' fique por volta de y=HEIGHT-100
    CHAO_Y = HEIGHT - 100

# Jogo
ROUND_TIME = 90  # segundos

# -------------------
# Utilitários
# -------------------
def draw_text(surface, text, font, color, x, y):
    img = font.render(text, True, color)
    surface.blit(img, (x, y))

# -------------------
# Lutador
# -------------------
class Fighter:
    def __init__(self, x, color, controls=None, ia=False, difficulty="Médio"):
        # rect usado para posição/colisão
        self.rect = pygame.Rect(x, CHAO_Y - 110, 40, 110)  # largura, altura
        self.color = color
        self.max_hp = 100
        self.hp = self.max_hp

        # movimento e física
        self.speed = 5
        self.vel_y = 0
        self.on_ground = True
        self.jump_strength = 15
        self.gravity = 1

        # ataque
        # ranges (em pixels)
        self.punch_range = 55
        self.kick_range = 95
        # danos
        self.punch_damage = 6
        self.kick_damage = 12
        # cooldowns em ms
        self.punch_cooldown = 500
        self.kick_cooldown = 900
        # timers
        self.last_punch = -9999
        self.last_kick = -9999

        # controle (None se IA)
        self.controls = controls
        self.ia = ia
        self.target = None  # outro fighter

        # IA params
        self.difficulty = difficulty
        if ia:
            if difficulty == "Fácil":
                self.speed = 3
                self.ia_reaction = 700  # ms entre decisões
                self.ia_aggression = 0.6  # prob escolher atacar quando em range
            elif difficulty == "Médio":
                self.speed = 4
                self.ia_reaction = 450
                self.ia_aggression = 0.75
            else:  # Difícil
                self.speed = 5
                self.ia_reaction = 300
                self.ia_aggression = 0.9
            self.ia_last_action = 0

        # animação simples: estado de ataque para desenhar braço/perna estendidos
        self.attacking = None  # "punch" or "kick" or None
        self.attacking_timer = 0
        self.attacking_duration = 140  # ms

    # função que tenta socar (chave de evento)
    def try_punch(self, current_time, other):
        if current_time - self.last_punch >= self.punch_cooldown:
            # checa alcance horizontal e vertical (praticamente no chão)
            dx = abs((self.rect.centerx) - (other.rect.centerx))
            dy = abs((self.rect.bottom) - (other.rect.bottom))
            if dx <= self.punch_range and dy < 40:
                other.receive_damage(self.punch_damage)
            self.last_punch = current_time
            self.attacking = "punch"
            self.attacking_timer = current_time

    def try_kick(self, current_time, other):
        if current_time - self.last_kick >= self.kick_cooldown:
            dx = abs((self.rect.centerx) - (other.rect.centerx))
            dy = abs((self.rect.bottom) - (other.rect.bottom))
            if dx <= self.kick_range and dy < 50:
                other.receive_damage(self.kick_damage)
            self.last_kick = current_time
            self.attacking = "kick"
            self.attacking_timer = current_time

    def receive_damage(self, dmg):
        self.hp -= dmg
        if self.hp < 0:
            self.hp = 0

    def move_horizontal(self, left=False, right=False):
        if left:
            self.rect.x -= self.speed
        if right:
            self.rect.x += self.speed
        # limites tela
        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(WIDTH, self.rect.right)

    def jump(self):
        if self.on_ground:
            self.vel_y = -self.jump_strength
            self.on_ground = False

    def apply_gravity(self):
        self.vel_y += self.gravity
        self.rect.y += int(self.vel_y)
        # colisão chão
        if self.rect.bottom >= CHAO_Y:
            self.rect.bottom = CHAO_Y
            self.vel_y = 0
            self.on_ground = True

    def update(self, keys, current_time):
        # IA ou jogador
        if self.ia:
            self.ai_behavior(current_time)
        else:
            # controles: left, right, jump, attack (same key for punch/kick? we'll map attack to alternating)
            if self.controls:
                if keys[self.controls["left"]]:
                    self.move_horizontal(left=True)
                if keys[self.controls["right"]]:
                    self.move_horizontal(right=True)
                # jump only on keydown event (handled externally)
                # attack events handled externally on KEYDOWN to avoid spam
        # física
        self.apply_gravity()

        # animação timer
        if self.attacking:
            if current_time - self.attacking_timer > self.attacking_duration:
                self.attacking = None

    def ai_behavior(self, current_time):
        if not self.target:
            return
        # decide ação a cada ia_reaction ms
        if current_time - getattr(self, "ia_last_action", 0) < self.ia_reaction:
            return
        self.ia_last_action = current_time

        # distância horizontal
        dx = (self.target.rect.centerx) - (self.rect.centerx)
        absdx = abs(dx)

        # se estiver fora do kick range, aproxime-se
        if absdx > self.kick_range - 10:
            # mover em direção ao jogador
            if dx > 0:
                self.move_horizontal(right=True)
            else:
                self.move_horizontal(left=True)
            # pequena chance de pular quando perto de borda (evita ficar preso)
            # nada mais
            return

        # se estiver dentro kick range, decidir atacar com probabilidade
        import random
        r = random.random()
        # se em punch range, prefira punch
        if absdx <= self.punch_range:
            if r < self.ia_aggression:
                self.try_punch(current_time, self.target)
            else:
                # às vezes tente kick se tiver oportunidade
                if r < self.ia_aggression + 0.15:
                    self.try_kick(current_time, self.target)
        else:
            # entre punch_range e kick_range — tentar kick com probabilidade
            if r < self.ia_aggression:
                self.try_kick(current_time, self.target)
            else:
                # ou ficar se reposicionando levemente
                if dx > 0:
                    self.move_horizontal(right=True)
                else:
                    self.move_horizontal(left=True)

    def draw(self, surface):
        cx = self.rect.centerx
        top = self.rect.top
        bottom = self.rect.bottom

        # cabeça
        pygame.draw.circle(surface, self.color, (cx, top + 12), 12)
        # tronco
        pygame.draw.line(surface, self.color, (cx, top + 24), (cx, bottom - 30), 4)

        # braços (pos depend on attack)
        arm_y = top + 40
        if self.attacking == "punch":
            # braço de soco estendido para frente (assumimos direção para centro da tela)
            direction = 1 if (self.target and self.target.rect.centerx > cx) else -1
            pygame.draw.line(surface, self.color, (cx, arm_y), (cx + (20 * direction), arm_y - 6), 4)
            # outro braço recuado
            pygame.draw.line(surface, self.color, (cx, arm_y), (cx - (12 * direction), arm_y - 10), 4)
        elif self.attacking == "kick":
            # braços recuados neutros
            pygame.draw.line(surface, self.color, (cx, arm_y), (cx - 15, arm_y - 10), 4)
            pygame.draw.line(surface, self.color, (cx, arm_y), (cx + 15, arm_y - 10), 4)
        else:
            # braços neutros
            pygame.draw.line(surface, self.color, (cx, arm_y), (cx - 15, arm_y - 10), 4)
            pygame.draw.line(surface, self.color, (cx, arm_y), (cx + 15, arm_y - 10), 4)

        # pernas (se kicking, mostrar perna esticada)
        leg_top_x = cx
        leg_top_y = bottom - 30
        if self.attacking == "kick":
            # chute para frente (direction)
            direction = 1 if (self.target and self.target.rect.centerx > cx) else -1
            # perna de chute esticada
            pygame.draw.line(surface, self.color, (leg_top_x, leg_top_y), (leg_top_x + 20 * direction, leg_top_y + 30), 4)
            # outra perna de apoio
            pygame.draw.line(surface, self.color, (leg_top_x, leg_top_y), (leg_top_x - 10 * direction, leg_top_y + 30), 4)
        else:
            # pernas neutras (leves abertura)
            pygame.draw.line(surface, self.color, (leg_top_x, leg_top_y), (leg_top_x - 12, leg_top_y + 30), 4)
            pygame.draw.line(surface, self.color, (leg_top_x, leg_top_y), (leg_top_x + 12, leg_top_y + 30), 4)

        # hitbox debug (opcional)
        # pygame.draw.rect(surface, (200,200,200), self.rect, 1)

    def draw_healthbar(self, surface, x, y):
        w = 220
        h = 22
        pygame.draw.rect(surface, RED, (x, y, w, h))
        hp_w = max(0, int(w * (self.hp / self.max_hp)))
        pygame.draw.rect(surface, GREEN, (x, y, hp_w, h))
        txt = FONT.render(f"{int(self.hp)}/{self.max_hp}", True, WHITE)
        surface.blit(txt, (x + w//2 - txt.get_width()//2, y + 1))


# -------------------
# Menus e telas
# -------------------
def main_menu():
    while True:
        SCREEN.fill(BLACK)
        draw_text_centered(SCREEN, "Jogo de Luta 2D", BIG_FONT, WHITE, 0, -100)
        draw_text_centered(SCREEN, "1 - Jogo Solo", FONT, WHITE, 0, -10)
        draw_text_centered(SCREEN, "2 - Multijogador Local", FONT, WHITE, 0, 30)
        draw_text_centered(SCREEN, "Esc - Sair", FONT, WHITE, 0, 80)
        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1:
                    diff = difficulty_menu()
                    run_game(solo=True, difficulty=diff)
                elif e.key == pygame.K_2:
                    run_game(solo=False, difficulty="Médio")
                elif e.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

def draw_text_centered(surface, text, font, color, x_offset=0, y_offset=0):
    img = font.render(text, True, color)
    x = WIDTH//2 - img.get_width()//2 + x_offset
    y = HEIGHT//2 - img.get_height()//2 + y_offset
    surface.blit(img, (x,y))

def difficulty_menu():
    while True:
        SCREEN.fill(BLACK)
        draw_text_centered(SCREEN, "Escolha a dificuldade", BIG_FONT, WHITE, 0, -120)
        draw_text_centered(SCREEN, "1 - Fácil", FONT, WHITE, 0, -20)
        draw_text_centered(SCREEN, "2 - Médio", FONT, WHITE, 0, 20)
        draw_text_centered(SCREEN, "3 - Difícil", FONT, WHITE, 0, 60)
        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_1:
                    return "Fácil"
                elif e.key == pygame.K_2:
                    return "Médio"
                elif e.key == pygame.K_3:
                    return "Difícil"

def game_over_screen(winner_text):
    while True:
        SCREEN.fill(BLACK)
        draw_text_centered(SCREEN, winner_text, BIG_FONT, YELLOW, 0, -60)
        draw_text_centered(SCREEN, "R - Reiniciar | M - Menu | Q - Sair", FONT, WHITE, 0, 40)
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r:
                    return "RESTART"
                elif e.key == pygame.K_m:
                    return "MENU"
                elif e.key == pygame.K_q:
                    pygame.quit(); sys.exit()

# -------------------
# Loop do jogo
# -------------------
def run_game(solo=False, difficulty="Médio"):
    # Criar lutadores
    p1_controls = {"left": pygame.K_a, "right": pygame.K_d, "jump": pygame.K_w, "punch": pygame.K_SPACE, "kick": pygame.K_LSHIFT}
    p1 = Fighter(180, BLUE, controls=p1_controls, ia=False)
    if solo:
        p2 = Fighter(WIDTH - 220, RED, controls=None, ia=True, difficulty=difficulty)
    else:
        p2_controls = {"left": pygame.K_LEFT, "right": pygame.K_RIGHT, "jump": pygame.K_UP, "punch": pygame.K_RETURN, "kick": pygame.K_RSHIFT}
        p2 = Fighter(WIDTH - 220, RED, controls=p2_controls, ia=False)

    p1.target = p2
    p2.target = p1

    start_ticks = pygame.time.get_ticks()
    time_left = ROUND_TIME

    running = True
    last_count_update = start_ticks

    # Para evitar spamming por segurar o botão, tratamos ataques em KEYDOWN (evento)
    while running:
        dt = CLOCK.tick(FPS)
        current_time = pygame.time.get_ticks()

        # atualizar timer (segundos inteiros)
        if current_time - last_count_update >= 1000:
            time_left -= 1
            last_count_update = current_time

        # eventos
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if e.type == pygame.KEYDOWN:
                # p1 ataques
                if not p1.ia:
                    if e.key == p1.controls["punch"]:
                        p1.try_punch(current_time, p1.target)
                    if e.key == p1.controls["kick"]:
                        p1.try_kick(current_time, p1.target)
                    if e.key == p1.controls["jump"]:
                        p1.jump()
                # p2 ataques (se humano)
                if not p2.ia and p2.controls:
                    if e.key == p2.controls["punch"]:
                        p2.try_punch(current_time, p2.target)
                    if e.key == p2.controls["kick"]:
                        p2.try_kick(current_time, p2.target)
                    if e.key == p2.controls["jump"]:
                        p2.jump()

                # menu quick actions
                if e.key == pygame.K_ESCAPE:
                    # voltar ao menu
                    return

        # teclas de movimento (mantidas)
        keys = pygame.key.get_pressed()

        # movimentação/atualização
        if not p1.ia:
            # left/right movement is handled by controls in update using keys
            if keys[p1.controls["left"]]:
                p1.move_horizontal(left=True)
            if keys[p1.controls["right"]]:
                p1.move_horizontal(right=True)
        p1.update(keys, current_time)

        if p2.ia:
            p2.update(keys, current_time)
        else:
            if keys[p2.controls["left"]]:
                p2.move_horizontal(left=True)
            if keys[p2.controls["right"]]:
                p2.move_horizontal(right=True)
            p2.update(keys, current_time)

        # desenho
        if BACKGROUND:
            SCREEN.blit(BACKGROUND, (0,0))
        else:
            SCREEN.fill((135,206,235))  # sky
            pygame.draw.rect(SCREEN, (100,60,20), (0, CHAO_Y, WIDTH, HEIGHT - CHAO_Y))  # ground

        # HUD: barras de vida
        p1.draw_healthbar(SCREEN, 30, 20)
        p2.draw_healthbar(SCREEN, WIDTH - 250, 20)

        # desenhar tempo central
        draw_text_centered(SCREEN, f"{time_left}", BIG_FONT, WHITE, 0, -200)

        # desenhar lutadores
        p1.draw(SCREEN)
        p2.draw(SCREEN)

        # condições de fim
        winner = None
        if p1.hp <= 0 and p2.hp <= 0:
            winner = "Empate!"
        elif p1.hp <= 0:
            winner = "Jogador 2 venceu!"
        elif p2.hp <= 0:
            winner = "Jogador 1 venceu!"
        elif time_left <= 0:
            # decide por maior HP
            if p1.hp > p2.hp:
                winner = "Jogador 1 venceu!"
            elif p2.hp > p1.hp:
                winner = "Jogador 2 venceu!"
            else:
                winner = "Empate!"

        pygame.display.flip()

        if winner:
            action = game_over_screen(winner)
            if action == "RESTART":
                return run_game(solo=solo, difficulty=difficulty)
            elif action == "MENU":
                return
            else:
                return

# -------------------
# Entrada
# -------------------
if __name__ == "__main__":
    main_menu()
