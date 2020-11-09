import pygame
import sys
import math
import network
import hashlib

# ------ 함수 ------ #


def intersect_line_line(line1, line2):
    def ccw(point1, point2, point3):
        return (point3[1] - point1[1]) * (point2[0] - point1[0]) > (point2[1] - point1[1]) * (point3[0] - point1[0])
    return ccw(line1[0], line2[0], line2[1]) != ccw(line1[1], line2[0], line2[1]) and ccw(line1[0], line1[1], line2[0]) != ccw(line1[0], line1[1], line2[1])


def intersect_rect_rect(rect1, rect2):
    if rect2[0] + rect2[2] >= rect1[0] >= rect2[0] - rect1[2] and rect2[1] + rect2[3] >= rect1[1] >= rect2[1] - rect1[3]:
        return True
    return False


def intersect_line_rect(rect1, line1):
    if intersect_line_line([[rect1[0], rect1[1]], [rect1[0] + rect1[2], rect1[1]]], line1) or intersect_line_line([[rect1[0], rect1[1] + rect1[3]], [rect1[0] + rect1[2], rect1[1] + rect1[3]]], line1):
        return True
    if intersect_line_line([[rect1[0], rect1[1]], [rect1[0], rect1[1] + rect1[3]]], line1) or intersect_line_line([[rect1[0] + rect1[2], rect1[1]], [rect1[0] + rect1[2], rect1[1] + rect1[3]]], line1):
        return True
    return False


# ------ 상수 ------ #

SCREEN_WIDTH = 1536  # 화면 가로 크기
SCREEN_HEIGHT = 790  # 화면 세로 크기
FPS = 60  # 1초당 재생되는 프레임 수

PLAYER_SIZE = 40  # 플레이어 가로 세로 크기
PLAYER_THICKNESS = 2  # 플레이어 정사각형 모델 테두리 두께
PLAYER_MAX_HP = 200  # 플레이어 최대 체력
SPAWN_X, SPAWN_Y = SCREEN_WIDTH // 2 - PLAYER_SIZE // 2, SCREEN_HEIGHT - PLAYER_SIZE
HP_HEIGHT = 10  # HP바 두께
HP_GAIN_RATE = 0.25  # HP 차는 속도
GRAVITY = 2  # 중력, Y축에 작용
FRICTION = 0.5  # 마찰력, X축에 작용
BULLET_THICKNESS = 3  # 총알 두께
BULLET_LENGTH = 40  # 총알 길이
BULLET_SPEED = 40  # 총알 속도
BULLET_COOLDOWN = 5  # 총알 딜레이
BULLET_DAMAGE = 10  # 총알 데미지
MAX_BULLET_CAPACITY = 6  # 탄창 크기
RELOAD_TIME = 60  # 재장전 시간
JUMP_Y_VELOCITY = 20  # 점프할 때 Y축 속도
ADDITIVE_X_VELOCITY = 1  # 좌우로 움직일때 더해지는 X축 속도
X_VELOCITY_CAP = 20  # X축 최대 속도
Y_VELOCITY_CAP = -35  # Y축 최대 속도
ELASTIC_MODULUS = -0.5  # 벽에 부딪칠 때의 탄성계수
COLLISION_THRESHOLD = 0.5  # 땅에 부딪칠 때 통과 예방 상수
PARTICLE_GROWTH_FACTOR = 5  # 파티클 커지는 속도
MAX_PARTICLE_MODULUS = 6  # 파티클의 최대 크기 조절
PARTICLE_WIDTH = 5  # 파티클 두께
DASH_MODULUS = 30  # 대쉬할 때 속도계수
MAX_DASH = 200  # 최대 대쉬 계수
WIN_SCORE = 1  # 이기기 위한 점수
NET = network.Network()  # 네트워크

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
ORANGE = (255, 140, 0)

# ------ 변수 ------ #

player_2_connected = False
username_text, password_text, confirm_password_text, error_text = "", "", "", ""
screen, current_screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF), "LOGIN_SCREEN_1"
player_1_bullets, player_2_bullets, bullet_time_left = [], [], 0
particles = []
platforms = [[0, SCREEN_HEIGHT - 100, 300, 20],  # L1H_1
             [SCREEN_WIDTH - 300, SCREEN_HEIGHT - 100, 300, 20],  # L1H_2
             [SCREEN_WIDTH // 2 - 400, SCREEN_HEIGHT - 250, 800, 20],  # L2H_1
             [0, SCREEN_HEIGHT - 400, 500, 20],  # L3H_1
             [SCREEN_WIDTH - 500, SCREEN_HEIGHT - 400, 500, 20],  # L3H_2
             [SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 400, 200, 20],  # L3H_3
             [SCREEN_WIDTH // 2 - 500, SCREEN_HEIGHT - 600, 400, 20],  # L4H_1
             [SCREEN_WIDTH // 2 + 100, SCREEN_HEIGHT - 600, 400, 20],  # L4H_2
             [SCREEN_WIDTH // 2 - 10, SCREEN_HEIGHT - 230, 20, 150]]  # L1V_1
death_objects = []
send_data = ""

# ------ 클래스 ------ #


class Player:
    def __init__(self):
        self.username = ""
        self.pos_x = SPAWN_X
        self.pos_y = SPAWN_Y
        self.former_x = SPAWN_X
        self.former_y = SPAWN_Y
        self.vel_x = 0
        self.vel_y = 0
        self.score = 0
        self.able_to_jump = 2
        self.dash = 1
        self.dash_bar = MAX_DASH
        self.hp = PLAYER_MAX_HP
        self.magazine = MAX_BULLET_CAPACITY
        self.reload_state = 0
        self.rp = 0

    def update_position(self):
        self.pos_y -= self.vel_y
        self.vel_y -= GRAVITY
        if self.vel_y < Y_VELOCITY_CAP:
            self.vel_y = Y_VELOCITY_CAP

        self.pos_x -= self.vel_x
        if abs(self.vel_x) >= FRICTION:
            if self.vel_x > 0:
                self.vel_x -= FRICTION
            elif self.vel_x < 0:
                self.vel_x += FRICTION
        elif FRICTION > abs(self.vel_x) > 0:
            self.vel_x = 0

    def check_key_update(self):
        global current_screen, username_text, password_text, confirm_password_text, error_text, player_1_bullets, bullet_time_left, send_data
        send_data = ""
        if current_screen == "LOGIN_SCREEN_1":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        username_text, password_text = "", ""
                    elif event.key == pygame.K_F1:
                        current_screen = "CREATE_ACCOUNT_SCREEN_1"
                        username_text, password_text, error_text = "", "", ""
                    elif event.key == pygame.K_RETURN:
                        username_exists = False
                        reply = NET.send("REQUEST_USER_DATABASE")
                        user_database = reply.split()
                        for i in range(len(user_database) // 3):
                            if username_text == user_database[3 * i]:
                                username_exists = True

                        if username_exists:
                            current_screen = "LOGIN_SCREEN_2"
                            error_text = ""
                        else:
                            username_text = ""
                            error_text = "No username exists!"
                    elif event.key == pygame.K_BACKSPACE:
                        username_text = username_text[:-1]
                    else:
                        username_text += event.unicode
        elif current_screen == "LOGIN_SCREEN_2":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        current_screen = "LOGIN_SCREEN_1"
                        username_text, password_text, error_text = "", "", ""
                    elif event.key == pygame.K_F1:
                        current_screen = "CREATE_ACCOUNT_SCREEN_1"
                        username_text, password_text, error_text = "", "", ""
                    elif event.key == pygame.K_RETURN:
                        encoded_text = hashlib.md5(password_text.encode("utf-8"))
                        encoded_text = encoded_text.hexdigest()

                        reply = NET.send("REQUEST_USER_DATABASE")
                        user_database = reply.split()

                        if user_database[user_database.index(username_text) + 1] == encoded_text:
                            current_screen = "GAME_SCREEN"
                            error_text = ""
                            self.username = username_text
                            self.rp = user_database[user_database.index(username_text) + 2]
                        else:
                            password_text = ""
                            error_text = "Incorrect password!"
                    elif event.key == pygame.K_BACKSPACE:
                        password_text = password_text[:-1]
                    else:
                        password_text += event.unicode
        elif current_screen == "CREATE_ACCOUNT_SCREEN_1":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        username_text, password_text = "", ""
                    elif event.key == pygame.K_F1:
                        current_screen = "LOGIN_SCREEN_1"
                        username_text, password_text, error_text = "", "", ""
                    elif event.key == pygame.K_RETURN and username_text != "":
                        username_exists = False
                        reply = NET.send("REQUEST_USER_DATABASE")
                        user_database = reply.split()
                        for i in range(len(user_database) // 3):
                            if username_text == user_database[3 * i]:
                                username_exists = True

                        if not username_exists:
                            current_screen = "CREATE_ACCOUNT_SCREEN_2"
                            error_text = ""
                        else:
                            username_text = ""
                            error_text = "That username already exists!"
                    elif event.key == pygame.K_BACKSPACE:
                        username_text = username_text[:-1]
                    else:
                        username_text += event.unicode
        elif current_screen == "CREATE_ACCOUNT_SCREEN_2":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        current_screen = "CREATE_ACCOUNT_SCREEN_1"
                        username_text, password_text = "", ""
                    elif event.key == pygame.K_F1:
                        current_screen = "LOGIN_SCREEN_1"
                        username_text, password_text, error_text = "", "", ""
                    elif event.key == pygame.K_RETURN and password_text != "":
                        current_screen = "CREATE_ACCOUNT_SCREEN_3"
                    elif event.key == pygame.K_BACKSPACE:
                        password_text = password_text[:-1]
                    else:
                        password_text += event.unicode
        elif current_screen == "CREATE_ACCOUNT_SCREEN_3":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        current_screen = "CREATE_ACCOUNT_SCREEN_1"
                        username_text, password_text, confirm_password_text = "", "", ""
                    elif event.key == pygame.K_F1:
                        current_screen = "LOGIN_SCREEN_1"
                        username_text, password_text, confirm_password_text, error_text = "", "", "", ""
                    elif event.key == pygame.K_RETURN:
                        if confirm_password_text == password_text:
                            NET.send("ADD_USER_DATABASE " + username_text + " " + password_text)
                            username_text, password_text, confirm_password_text, error_text = "", "", "", ""
                            current_screen = "LOGIN_SCREEN_1"
                        else:
                            confirm_password_text = ""
                            error_text = "Password doesn't match!"
                    elif event.key == pygame.K_BACKSPACE:
                        confirm_password_text = confirm_password_text[:-1]
                    else:
                        confirm_password_text += event.unicode
        elif current_screen == "WIN_SCREEN" or current_screen == "LOSE_SCREEN":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F1:
                        current_screen = "LOGIN_SCREEN_1"
                        username_text, password_text = "", ""
        elif current_screen == "GAME_SCREEN":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and self.able_to_jump != 0:
                        self.vel_y = JUMP_Y_VELOCITY
                        self.able_to_jump -= 1

                    if event.key == pygame.K_w and self.dash_bar == MAX_DASH:
                        self.dash = DASH_MODULUS
                        self.dash_bar = 0
                    elif not event.key == pygame.K_w:
                        self.dash = 1

                    if event.key == pygame.K_r and self.magazine != MAX_BULLET_CAPACITY:
                        self.magazine = 0

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1 and bullet_time_left == 0 and self.magazine > 0:
                        self.magazine -= 1

                        mx, my = pygame.mouse.get_pos()
                        px, py = self.pos_x + PLAYER_SIZE // 2, self.pos_y + PLAYER_SIZE // 2
                        theta = math.acos((mx - px) / math.sqrt((mx - px) ** 2 + (my - py) ** 2))

                        if my > py:
                            theta *= -1
                        send_data += "," + str(px) + "," + str(py) + "," + str(theta)
                        bullet_time_left = BULLET_COOLDOWN
                        player_1_bullets.append([px, py, theta])

            key_event = pygame.key.get_pressed()
            if key_event[pygame.K_a] and self.vel_x < X_VELOCITY_CAP:
                self.vel_x += ADDITIVE_X_VELOCITY * self.dash
            if key_event[pygame.K_d] and self.vel_x > -X_VELOCITY_CAP:
                self.vel_x -= ADDITIVE_X_VELOCITY * self.dash

            self.dash_bar += 1
            if self.dash_bar > MAX_DASH:
                self.dash_bar = MAX_DASH

            if self.magazine == 0:
                self.reload_state += 1
            if self.reload_state == RELOAD_TIME:
                self.magazine = MAX_BULLET_CAPACITY
                self.reload_state = 0

    def gain_hp(self):
        if self.pos_x == self.former_x and self.pos_y == self.former_y:
            self.hp += HP_GAIN_RATE

        if self.hp > PLAYER_MAX_HP:
            self.hp = PLAYER_MAX_HP

    def check_collision_bounds(self):
        if self.pos_x <= 0:
            self.pos_x = 0
            self.vel_x *= ELASTIC_MODULUS
        if self.pos_x + PLAYER_SIZE >= SCREEN_WIDTH:
            self.pos_x = SCREEN_WIDTH - PLAYER_SIZE
            self.vel_x *= ELASTIC_MODULUS
        if self.pos_y <= 0:
            self.pos_y = 0
            self.vel_y = -1
        if self.pos_y + PLAYER_SIZE >= SCREEN_HEIGHT:
            self.pos_y = SCREEN_HEIGHT - PLAYER_SIZE
            self.vel_y = 0
            self.able_to_jump = 2

    def check_collision_platforms(self):
        global platforms
        for i in range(len(platforms)):
            if intersect_rect_rect([self.pos_x, self.pos_y, PLAYER_SIZE, PLAYER_SIZE], platforms[i]):
                center_player_x = self.former_x + PLAYER_SIZE // 2
                center_player_y = self.former_y + PLAYER_SIZE // 2
                center_platform_x = platforms[i][0] + platforms[i][2] // 2
                center_platform_y = platforms[i][1] + platforms[i][3] // 2

                slope_ul = (platforms[i][1] - center_platform_y) / (platforms[i][0] - center_platform_x)

                if center_platform_x == center_player_x:
                    slope_player = 9999
                else:
                    slope_player = (center_platform_y - center_player_y) / (center_platform_x - center_player_x)

                if abs(slope_player) >= abs(slope_ul):
                    if center_player_y <= center_platform_y:
                        self.pos_y = platforms[i][1] - PLAYER_SIZE
                        self.vel_y = 0
                        self.able_to_jump = 2
                    else:
                        self.pos_y = platforms[i][1] + platforms[i][3]
                        self.vel_y = -1
                else:
                    self.vel_x *= ELASTIC_MODULUS
                    if center_player_x <= center_platform_x:
                        self.pos_x = platforms[i][0] - PLAYER_SIZE
                    else:
                        self.pos_x = platforms[i][0] + platforms[i][2]

    def check_collision_death_objects(self):
        global death_objects
        for i in range(len(death_objects)):
            if intersect_rect_rect([self.pos_x, self.pos_y, PLAYER_SIZE, PLAYER_SIZE], death_objects[i]):
                self.hp = 0

    @staticmethod
    def check_collision_player_1_bullets():
        global player_1_bullets, particles, platforms
        for i in range(len(player_1_bullets)):
            predict_x = player_1_bullets[i][0] + BULLET_LENGTH * math.cos(player_1_bullets[i][2])
            predict_y = player_1_bullets[i][1] - BULLET_LENGTH * math.sin(player_1_bullets[i][2])

            if predict_x < 0 or predict_x > SCREEN_WIDTH or predict_y < 0 or predict_y > SCREEN_HEIGHT:
                particles.append([int(predict_x), int(predict_y), 1])
                del player_1_bullets[i]
                break

            temp = False
            for j in range(len(platforms)):
                if intersect_line_rect(platforms[j], [[player_1_bullets[i][0], player_1_bullets[i][1]], [predict_x, predict_y]]):
                    particles.append([int(predict_x), int(predict_y), 1])
                    del player_1_bullets[i]
                    temp = True
                    break
            if temp:
                break

    def check_collision_player_2_bullets(self):
        global player_2_bullets, particles, platforms
        for i in range(len(player_2_bullets)):
            predict_x = player_2_bullets[i][0] + BULLET_LENGTH * math.cos(player_2_bullets[i][2])
            predict_y = player_2_bullets[i][1] - BULLET_LENGTH * math.sin(player_2_bullets[i][2])

            if intersect_line_rect([self.pos_x, self.pos_y, PLAYER_SIZE, PLAYER_SIZE], [[int(player_2_bullets[i][0]), int(player_2_bullets[i][1])], [predict_x, predict_y]]):
                self.hp -= BULLET_DAMAGE
                break

            if predict_x < 0 or predict_x > SCREEN_WIDTH or predict_y < 0 or predict_y > SCREEN_HEIGHT:
                particles.append([int(predict_x), int(predict_y), 1])
                del player_2_bullets[i]
                break

            temp = False
            for j in range(len(platforms)):
                if intersect_line_rect(platforms[j], [[player_2_bullets[i][0], player_2_bullets[i][1]], [predict_x, predict_y]]):
                    particles.append([int(predict_x), int(predict_y), 1])
                    del player_2_bullets[i]
                    temp = True
                    break
            if temp:
                break

    def check_collision(self):
        self.check_collision_bounds()
        self.check_collision_platforms()
        self.check_collision_death_objects()
        self.check_collision_player_1_bullets()
        self.check_collision_player_2_bullets()


class Canvas:
    def __init__(self):
        self.jump_indicator_sprite = pygame.image.load("Sprites//HUD//Jump_Indicator.png")
        self.bullet_indicator_sprite = pygame.image.load("Sprites//HUD//Bullet_Indicator.png")
        self.map_1_sprite = pygame.image.load("Sprites//Maps//Map_1.png").convert()
        self.fnt_YuGothR = pygame.font.Font("C://Windows//Fonts//YuGothR.ttc", 36)

    @staticmethod
    def draw_player(player, color):
        global screen
        pygame.draw.rect(screen, color, (int(player.pos_x), int(player.pos_y), PLAYER_SIZE, PLAYER_SIZE), PLAYER_THICKNESS)
        pygame.draw.rect(screen, color, (int(player.pos_x), int(player.pos_y) - 2 * HP_HEIGHT, int(PLAYER_SIZE * (player.hp / PLAYER_MAX_HP)), HP_HEIGHT))

    @staticmethod
    def draw_player_1_bullets():
        global player_1_bullets
        for i in range(len(player_1_bullets)):
            temp_x = int(player_1_bullets[i][0] + BULLET_LENGTH * math.cos(player_1_bullets[i][2]))
            temp_y = int(player_1_bullets[i][1] - BULLET_LENGTH * math.sin(player_1_bullets[i][2]))
            pygame.draw.line(screen, GREEN, (int(player_1_bullets[i][0]), int(player_1_bullets[i][1])), (temp_x, temp_y), BULLET_THICKNESS)
            player_1_bullets[i][0] = int(player_1_bullets[i][0] + BULLET_SPEED * math.cos(player_1_bullets[i][2]))
            player_1_bullets[i][1] = int(player_1_bullets[i][1] - BULLET_SPEED * math.sin(player_1_bullets[i][2]))

    @staticmethod
    def draw_player_2_bullets():
        global player_2_bullets
        for i in range(len(player_2_bullets)):
            temp_x = int(player_2_bullets[i][0] + BULLET_LENGTH * math.cos(player_2_bullets[i][2]))
            temp_y = int(player_2_bullets[i][1] - BULLET_LENGTH * math.sin(player_2_bullets[i][2]))
            pygame.draw.line(screen, RED, (int(player_2_bullets[i][0]), int(player_2_bullets[i][1])), (temp_x, temp_y), BULLET_THICKNESS)
            player_2_bullets[i][0] = int(player_2_bullets[i][0] + BULLET_SPEED * math.cos(player_2_bullets[i][2]))
            player_2_bullets[i][1] = int(player_2_bullets[i][1] - BULLET_SPEED * math.sin(player_2_bullets[i][2]))

    @staticmethod
    def draw_platforms():
        global platforms
        for i in range(len(platforms)):
            pygame.draw.rect(screen, WHITE, platforms[i])

    @staticmethod
    def draw_death_objects():
        global death_objects
        for i in range(len(death_objects)):
            pygame.draw.rect(screen, ORANGE, death_objects[i])

    @staticmethod
    def draw_particles():
        global particles
        for i in range(len(particles)):
            pygame.draw.circle(screen, RED, (particles[i][0], particles[i][1]), particles[i][2] * PARTICLE_GROWTH_FACTOR, PARTICLE_WIDTH)
            if particles[i][2] > MAX_PARTICLE_MODULUS:
                del particles[i]
                break
            else:
                particles[i][2] += 1

    def draw_ui(self, player_1):
        for i in range(player_1.able_to_jump):
            screen.blit(self.jump_indicator_sprite, (10 + i * 30, SCREEN_HEIGHT - 30))

        if player_1.dash_bar == MAX_DASH:
            pygame.draw.rect(screen, BLUE, (80, SCREEN_HEIGHT - 30, player_1.dash_bar // 2, 20))
        else:
            pygame.draw.rect(screen, RED, (80, SCREEN_HEIGHT - 30, player_1.dash_bar // 2, 20))
            pygame.draw.rect(screen, BLUE, (80 + player_1.dash_bar // 2, SCREEN_HEIGHT - 30, MAX_DASH // 2 - player_1.dash_bar // 2, 20))

        for i in range(player_1.magazine):
            screen.blit(self.bullet_indicator_sprite, (10 + i * 30, SCREEN_HEIGHT - 60))

        if player_1.magazine == 0:
            pygame.draw.rect(screen, RED, (10, SCREEN_HEIGHT - 70, RELOAD_TIME, 30))
            pygame.draw.rect(screen, WHITE, (10, SCREEN_HEIGHT - 70, player_1.reload_state, 30))

    def display_canvas(self, player_1, player_2):
        global player_2_connected, current_screen, screen, username_text, password_text, confirm_password_text, error_text
        if player_2_connected and current_screen == "GAME_SCREEN":
            screen.blit(self.map_1_sprite, [0, 0])
            self.draw_player(player_2, RED)
            self.draw_player(player_1, GREEN)

            self.draw_player_1_bullets()
            self.draw_player_2_bullets()
            self.draw_particles()
            self.draw_ui(player_1)

            # self.draw_platforms()
            # self.draw_death_objects()

            player_1_score = self.fnt_YuGothR.render(player_1.username + "'s Score: " + str(player_1.score), True, WHITE)
            player_2_score = self.fnt_YuGothR.render(player_2.username + "'s Score: " + str(player_2.score), True, WHITE) if player_2.username != "" else self.fnt_YuGothR.render("Player 2 is still logging in...", True, WHITE)
            player_1_rp = self.fnt_YuGothR.render("Ranked Points: " + str(player_1.rp), True, WHITE)
            player_2_rp = self.fnt_YuGothR.render("Ranked Points: " + str(player_2.rp), True, WHITE) if player_2.username != "" else self.fnt_YuGothR.render("", True, WHITE)

            screen.blit(player_1_score, [10, 10])
            screen.blit(player_2_score, [SCREEN_WIDTH - player_2_score.get_width() - 10, 10])
            screen.blit(player_1_rp, [10, 50])
            screen.blit(player_2_rp, [SCREEN_WIDTH - player_2_rp.get_width() - 10, 50])
        elif not player_2_connected and current_screen == "GAME_SCREEN":
            player_2_not_connected = self.fnt_YuGothR.render("Opponent is currently offline!", True, WHITE)

            screen.fill(BLACK)
            screen.blit(player_2_not_connected, [100, SCREEN_HEIGHT // 2 - player_2_not_connected.get_height() // 2])
        elif current_screen == "LOGIN_SCREEN_1":
            login = self.fnt_YuGothR.render("LOGIN", True, WHITE)
            username = self.fnt_YuGothR.render("Username: " + username_text, True, WHITE)
            password = self.fnt_YuGothR.render("Password: " + "*" * len(password_text), True, WHITE)
            create_new_account = self.fnt_YuGothR.render("Create New Account [F1]", True, WHITE)
            error = self.fnt_YuGothR.render(error_text, True, RED)

            screen.fill(BLACK)
            screen.blit(login, [100, 100])
            screen.blit(username, [100, SCREEN_HEIGHT // 2 - 100 - username.get_height() // 2])
            screen.blit(password, [100, SCREEN_HEIGHT // 2 - password.get_height() // 2])
            screen.blit(create_new_account, [100, SCREEN_HEIGHT // 2 + 100 - create_new_account.get_height() // 2])
            screen.blit(error, [750, SCREEN_HEIGHT // 2 - 100 - error.get_height() // 2])

            pygame.draw.rect(screen, WHITE, (100 + username.get_width(), SCREEN_HEIGHT // 2 - 100 + username.get_height() // 2, 20, 5))
        elif current_screen == "LOGIN_SCREEN_2":
            login = self.fnt_YuGothR.render("LOGIN", True, WHITE)
            username = self.fnt_YuGothR.render("Username: " + username_text, True, WHITE)
            password = self.fnt_YuGothR.render("Password: " + "*" * len(password_text), True, WHITE)
            create_new_account = self.fnt_YuGothR.render("Create New Account [F1]", True, WHITE)
            error = self.fnt_YuGothR.render(error_text, True, RED)

            screen.fill(BLACK)
            screen.blit(login, [100, 100])
            screen.blit(username, [100, SCREEN_HEIGHT // 2 - 100 - username.get_height() // 2])
            screen.blit(password, [100, SCREEN_HEIGHT // 2 - password.get_height() // 2])
            screen.blit(create_new_account, [100, SCREEN_HEIGHT // 2 + 100 - create_new_account.get_height() // 2])
            screen.blit(error, [750, SCREEN_HEIGHT // 2 - error.get_height() // 2])

            pygame.draw.rect(screen, WHITE, (100 + password.get_width(), SCREEN_HEIGHT // 2 + password.get_height() // 2, 20, 5))
        elif current_screen == "CREATE_ACCOUNT_SCREEN_1":
            create_account = self.fnt_YuGothR.render("CREATE ACCOUNT", True, WHITE)
            username = self.fnt_YuGothR.render("Username: " + username_text, True, WHITE)
            password = self.fnt_YuGothR.render("Password: " + "*" * len(password_text), True, WHITE)
            confirm_password = self.fnt_YuGothR.render("Confirm Password: " + "*" * len(confirm_password_text), True, WHITE)
            back = self.fnt_YuGothR.render("Back [F1]", True, WHITE)
            error = self.fnt_YuGothR.render(error_text, True, RED)

            screen.fill(BLACK)
            screen.blit(create_account, [100, 100])
            screen.blit(username, [100, SCREEN_HEIGHT // 2 - 150 - username.get_height() // 2])
            screen.blit(password, [100, SCREEN_HEIGHT // 2 - 50 - password.get_height() // 2])
            screen.blit(confirm_password, [100, SCREEN_HEIGHT // 2 + 50 - confirm_password.get_height() // 2])
            screen.blit(back, [100, SCREEN_HEIGHT // 2 + 150 - back.get_height() // 2])
            screen.blit(error, [750, SCREEN_HEIGHT // 2 - 150 - error.get_height() // 2])

            pygame.draw.rect(screen, WHITE, (100 + username.get_width(), SCREEN_HEIGHT // 2 - 150 + username.get_height() // 2, 20, 5))
        elif current_screen == "CREATE_ACCOUNT_SCREEN_2":
            create_account = self.fnt_YuGothR.render("CREATE ACCOUNT", True, WHITE)
            username = self.fnt_YuGothR.render("Username: " + username_text, True, WHITE)
            password = self.fnt_YuGothR.render("Password: " + "*" * len(password_text), True, WHITE)
            confirm_password = self.fnt_YuGothR.render("Confirm Password: " + "*" * len(confirm_password_text), True, WHITE)
            back = self.fnt_YuGothR.render("Back [F1]", True, WHITE)

            screen.fill(BLACK)
            screen.blit(create_account, [100, 100])
            screen.blit(username, [100, SCREEN_HEIGHT // 2 - 150 - username.get_height() // 2])
            screen.blit(password, [100, SCREEN_HEIGHT // 2 - 50 - password.get_height() // 2])
            screen.blit(confirm_password, [100, SCREEN_HEIGHT // 2 + 50 - confirm_password.get_height() // 2])
            screen.blit(back, [100, SCREEN_HEIGHT // 2 + 150 - back.get_height() // 2])

            pygame.draw.rect(screen, WHITE, (100 + password.get_width(), SCREEN_HEIGHT // 2 - 50 + password.get_height() // 2, 20, 5))
        elif current_screen == "CREATE_ACCOUNT_SCREEN_3":
            create_account = self.fnt_YuGothR.render("CREATE ACCOUNT", True, WHITE)
            username = self.fnt_YuGothR.render("Username: " + username_text, True, WHITE)
            password = self.fnt_YuGothR.render("Password: " + "*" * len(password_text), True, WHITE)
            confirm_password = self.fnt_YuGothR.render("Confirm Password: " + "*" * len(confirm_password_text), True, WHITE)
            back = self.fnt_YuGothR.render("Back [F1]", True, WHITE)
            error = self.fnt_YuGothR.render(error_text, True, RED)

            screen.fill(BLACK)
            screen.blit(create_account, [100, 100])
            screen.blit(username, [100, SCREEN_HEIGHT // 2 - 150 - username.get_height() // 2])
            screen.blit(password, [100, SCREEN_HEIGHT // 2 - 50 - password.get_height() // 2])
            screen.blit(confirm_password, [100, SCREEN_HEIGHT // 2 + 50 - confirm_password.get_height() // 2])
            screen.blit(back, [100, SCREEN_HEIGHT // 2 + 150 - back.get_height() // 2])
            screen.blit(error, [750, SCREEN_HEIGHT // 2 + 50 - error.get_height() // 2])

            pygame.draw.rect(screen, WHITE, (100 + confirm_password.get_width(), SCREEN_HEIGHT // 2 + 50 + confirm_password.get_height() // 2, 20, 5))
        elif current_screen == "WIN_SCREEN":
            win = self.fnt_YuGothR.render("You won!", True, WHITE)
            back = self.fnt_YuGothR.render("Back to login screen [F1]", True, WHITE)

            screen.fill(BLACK)
            screen.blit(win, [100, SCREEN_HEIGHT // 2 - 100 - win.get_height() // 2])
            screen.blit(back, [100, SCREEN_HEIGHT // 2 + 100 - back.get_height() // 2])
        elif current_screen == "LOSE_SCREEN":
            lose = self.fnt_YuGothR.render("You lost!", True, WHITE)
            back = self.fnt_YuGothR.render("Back to login screen [F1]", True, WHITE)

            screen.fill(BLACK)
            screen.blit(lose, [100, SCREEN_HEIGHT // 2 - 100 - lose.get_height() // 2])
            screen.blit(back, [100, SCREEN_HEIGHT // 2 + 100 - back.get_height() // 2])


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("SINGULARITY")

        self.canvas = Canvas()
        self.player_1 = Player()
        self.player_2 = Player()

    def update_player_values(self):
        self.player_1.update_position()

        if self.player_1.hp <= 0:
            self.player_1.pos_x, self.player_1.pos_y = SPAWN_X, SPAWN_Y
            self.player_1.vel_x, self.player_1.vel_y = 0, 0
            self.player_1.dash_bar = MAX_DASH
            self.player_1.hp = PLAYER_MAX_HP
            self.player_2.score += 1

        self.player_1.gain_hp()

    def send_receive_data(self):
        global send_data, player_2_connected

        send_data = str(NET.id) + ":" + str(self.player_1.pos_x) + "," + str(self.player_1.pos_y) + "," + str(self.player_2.score) + "," + str(self.player_1.hp) + "," + str(self.player_1.username) + "," + str(self.player_1.rp) + send_data
        reply = NET.send(send_data)

        if reply.split(":")[1] != "-100,-100":
            player_2_connected = True
            receive_data = reply.split(":")[1].split(",")
            self.player_2.pos_x, self.player_2.pos_y = int(float(receive_data[0])), int(float(receive_data[1]))
            self.player_1.score = int(float(receive_data[2]))
            self.player_2.hp = int(float(receive_data[3]))
            self.player_2.username = str(receive_data[4])
            self.player_2.rp = str(receive_data[5])

            receive_data = receive_data[6:]
            for i in range(len(receive_data) // 3):
                player_2_bullets.append([float(receive_data[i * 3]), float(receive_data[i * 3 + 1]), float(receive_data[i * 3 + 2])])
        else:
            player_2_connected = False

        if not player_2_connected: self.player_2.pos_x, self.player_2.pos_y = -100, -100

    def finalized_update(self):
        global current_screen, player_1_bullets, player_2_bullets, bullet_time_left, particles
        self.player_1.former_x, self.player_1.former_y = self.player_1.pos_x, self.player_1.pos_y
        if bullet_time_left != 0: bullet_time_left -= 1

        if self.player_1.score == WIN_SCORE:
            if self.player_1.username != "":
                NET.send("UPDATE_SCORE_POSITIVE " + str(self.player_1.username))
                self.player_1 = Player()
                self.player_2 = Player()
                player_1_bullets, player_2_bullets, bullet_time_left, particles = [], [], 0, []
                current_screen = "WIN_SCREEN"
        elif self.player_2.score == WIN_SCORE:
            if self.player_1.username != "":
                NET.send("UPDATE_SCORE_NEGATIVE " + str(self.player_1.username))
                self.player_1 = Player()
                self.player_2 = Player()
                player_1_bullets, player_2_bullets, bullet_time_left, particles = [], [], 0, []
                current_screen = "LOSE_SCREEN"
        pygame.display.update()

    def start_game_logic(self):
        clock = pygame.time.Clock()
        while True:
            clock.tick(FPS)

            # ------ 키보드/마우스 입력 감지 ------- #

            self.player_1.check_key_update()

            # ------ 플레이어 변수 업데이트 ------ #

            self.update_player_values()

            # ------ 충돌 감지 ------ #

            self.player_1.check_collision()

            # ------ 네트워크 ------ #

            self.send_receive_data()

            # ------ 화면에 표시 ------ #

            self.canvas.display_canvas(self.player_1, self.player_2)

            # ------ 최종 변수 변경 ------ #

            self.finalized_update()


# ------ 메인 ------ #

game = Game()
game.start_game_logic()
