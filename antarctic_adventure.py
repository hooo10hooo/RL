import pygame
import random
import math

# --- 1. 게임 설정 ---
# 화면 크기
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
# 색상
SKY_BLUE = (123, 183, 239)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PENGUIN_YELLOW = (255, 224, 102)
OBSTACLE_BROWN = (139, 69, 19)
FISH_SILVER = (192, 192, 192)
ORANGE = (255, 165, 0)
DARK_BLUE = (0, 50, 100)
# 게임 설정
FPS = 60
HORIZON_Y = SCREEN_HEIGHT // 2 - 50 # 지평선 위치
PLAYER_BASE_Y_OFFSET = 60 # 화면 하단에서의 플레이어 y 오프셋
PROJECTION_SCALE_FACTOR = 1.0 # 원근 투영 스케일 계수

FISH_JUMP_VELOCITY = 10 # 물고기 점프 초기 속도 (충돌 가능하도록 하향 조정)
OBJECT_GRAVITY = 0.2 # 물고기에 적용될 중력 (조정)

# --- 2. 플레이어 클래스 ---
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # 펭귄 모양 그리기 (투명 배경)
        self.base_image = pygame.Surface((40, 50), pygame.SRCALPHA)
        # 몸통
        pygame.draw.ellipse(self.base_image, BLACK, (5, 0, 30, 45))
        # 배
        pygame.draw.ellipse(self.base_image, WHITE, (10, 10, 20, 30))
        # 눈
        pygame.draw.circle(self.base_image, BLACK, (15, 20), 2)
        pygame.draw.circle(self.base_image, BLACK, (25, 20), 2)
        # 부리
        pygame.draw.polygon(self.base_image, ORANGE, [(20, 25), (17, 29), (23, 29)])
        # 발
        pygame.draw.ellipse(self.base_image, ORANGE, (10, 43, 10, 7))
        pygame.draw.ellipse(self.base_image, ORANGE, (20, 43, 10, 7))
        self.image = self.base_image
        self.rect = self.image.get_rect(midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - PLAYER_BASE_Y_OFFSET))
        
        self.x_pos = 0  # 트랙 중앙을 0으로, -1 ~ 1 사이 값
        self.speed = 0.02
        
        self.is_jumping = False
        self.jump_velocity = 20
        self.gravity = 1
        self.y_velocity = 0
        self.base_y = self.rect.y

    def update(self, *args, **kwargs): # 그룹 업데이트를 위해 유연한 인자 수용
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.x_pos -= self.speed
        if keys[pygame.K_RIGHT]:
            self.x_pos += self.speed
        self.x_pos = max(-1.0, min(1.0, self.x_pos)) # 트랙 이탈 방지

        # 점프 로직
        if self.is_jumping:
            self.rect.y -= self.y_velocity
            self.y_velocity -= self.gravity
            if self.rect.y >= self.base_y:
                self.rect.y = self.base_y
                self.is_jumping = False
        
        # 플레이어의 x좌표를 화면 좌표로 변환
        self.rect.centerx = SCREEN_WIDTH // 2 + self.x_pos * (SCREEN_WIDTH // 3)

    def jump(self):
        if not self.is_jumping:
            self.is_jumping = True
            self.y_velocity = self.jump_velocity

# --- 3. 월드 오브젝트 클래스 (장애물, 아이템) ---
class WorldObject(pygame.sprite.Sprite):
    def __init__(self, obj_type):
        super().__init__()
        self.obj_type = obj_type
        self.world_x = random.uniform(-0.8, 0.8) # 트랙 위의 x 위치
        self.world_z = 100.0 # 깊이 (카메라로부터의 거리)

        self.airborne_y = 0 # 공중 y 위치 (점프용)
        self.y_velocity = 0 # y축 속도 (점프용)
        self.has_jumped = False # 물고기 점프 상태 플래그
        
        if self.obj_type == 'obstacle':
            # 얼음 구멍 모양 그리기 (투명 배경)
            self.base_image = pygame.Surface((150, 60), pygame.SRCALPHA)
            pygame.draw.ellipse(self.base_image, DARK_BLUE, self.base_image.get_rect())
            pygame.draw.ellipse(self.base_image, WHITE, self.base_image.get_rect(), 4) # 테두리
        elif self.obj_type == 'fish':
            # 물고기 모양 그리기 (투명 배경)
            self.base_image = pygame.Surface((60, 38), pygame.SRCALPHA)
            # 몸통
            pygame.draw.ellipse(self.base_image, FISH_SILVER, (0, 8, 45, 22))
            # 꼬리
            pygame.draw.polygon(self.base_image, FISH_SILVER, [(42, 19), (60, 8), (60, 30)])
            # 눈
            pygame.draw.circle(self.base_image, BLACK, (15, 18), 3)

        self.image = self.base_image
        self.rect = self.image.get_rect()

    def update(self, scroll_speed):
        self.world_z -= scroll_speed
        if self.world_z < 0.1:
            self.kill() # 화면 뒤로 사라지면 제거
        else:
            # 점프 로직 (물고기만)
            if self.obj_type == 'fish':
                # 특정 Z 거리에 도달하면 점프 시작
                if not self.has_jumped and self.world_z < 25: # 더 가까이 왔을 때 점프
                    self.has_jumped = True
                    self.y_velocity = FISH_JUMP_VELOCITY

                # 점프가 시작된 후에만 물리 계산 수행
                if self.has_jumped:
                    self.airborne_y += self.y_velocity
                    self.y_velocity -= OBJECT_GRAVITY
                    if self.airborne_y < 0:
                        self.airborne_y = 0
                        self.y_velocity = 0

            self.project()

    def project(self):
        # 유사 3D 효과를 위한 원근 투영
        # z가 작을수록(가까울수록) 화면에 크게, 아래에 표시됨
        scale = PROJECTION_SCALE_FACTOR / self.world_z
        screen_x = SCREEN_WIDTH / 2 + self.world_x * (SCREEN_WIDTH / 2) * scale
        screen_y = HORIZON_Y + (SCREEN_HEIGHT - HORIZON_Y) * scale
        screen_y -= self.airborne_y * scale # 점프 높이 적용 (원근에 따라 스케일링)
        
        # 크기 조절
        width = self.base_image.get_width() * scale
        height = self.base_image.get_height() * scale
        
        self.image = pygame.transform.scale(self.base_image, (max(1, int(width)), max(1, int(height))))
        self.rect = self.image.get_rect(midbottom=(screen_x, screen_y))

# --- 4. 메인 게임 함수 ---
def game_loop(screen, clock, font):
    """
    게임의 한 판을 실행하는 메인 루프입니다.
    - 게임 종료 시 (창 닫기): False를 반환합니다.
    - 게임 재시작 시 ('R' 키): True를 반환합니다.
    """

    # 게임 변수
    score = 0
    game_speed = 0.3 # 초기 속도 대폭 하향
    game_over = False

    # 스프라이트 그룹
    all_sprites = pygame.sprite.Group()
    world_objects = pygame.sprite.Group()
    player = Player()
    all_sprites.add(player)

    # 첫 장애물이 더 빨리 나오도록 타이머 초기값 조정
    # 약 1.5초(90프레임) 후에 첫 장애물이 등장하도록 설정합니다.
    spawn_threshold = 60 / (game_speed + 0.1)
    object_spawn_timer = max(0, spawn_threshold - 90) # 90프레임(1.5초) 후에 등장
    
    running = True
    while running:
        # --- 이벤트 처리 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False # 전체 프로그램 종료 신호
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.jump()
                if event.key == pygame.K_r and game_over: # 게임오버 시 재시작
                    return True # 게임 재시작 신호

        if not game_over:
            # --- 게임 로직 업데이트 ---
            # all_sprites 그룹을 통해 모든 스프라이트(Player, WorldObject)를 한번에 업데이트
            all_sprites.update(game_speed)

            # 오브젝트 생성
            object_spawn_timer += 1
            if object_spawn_timer > 60 / (game_speed + 0.1):
                object_spawn_timer = 0
                # 장애물(구멍) 생성
                new_obstacle = WorldObject('obstacle')
                world_objects.add(new_obstacle)
                all_sprites.add(new_obstacle)

                # 50% 확률로 해당 장애물에서 물고기가 튀어나옴
                if random.random() < 0.5:
                    new_fish = WorldObject('fish')
                    new_fish.world_x = new_obstacle.world_x # 장애물과 같은 위치
                    new_fish.world_z = new_obstacle.world_z
                    world_objects.add(new_fish)
                    all_sprites.add(new_fish)

            # 충돌 감지
            for obj in world_objects:
                if 0.8 < obj.world_z < 1.8: # 플레이어와 충돌 가능한 깊이 범위
                    if player.rect.colliderect(obj.rect):
                        if obj.obj_type == 'obstacle':
                            if not player.is_jumping: # 점프 중이 아닐 때만 충돌
                                game_over = True
                        elif obj.obj_type == 'fish':
                            score += 10
                            obj.kill()
            
            # 게임 속도 점차 증가
            # game_speed += 0.0001 # 속도 증가량을 더욱 줄여 난이도 대폭 하향

        # --- 화면 그리기 ---
        # 배경
        screen.fill(SKY_BLUE)
        pygame.draw.rect(screen, WHITE, (0, HORIZON_Y, SCREEN_WIDTH, SCREEN_HEIGHT - HORIZON_Y))

        # 트랙 라인
        pygame.draw.line(screen, BLACK, (SCREEN_WIDTH // 2, HORIZON_Y), (0, SCREEN_HEIGHT), 5)
        pygame.draw.line(screen, BLACK, (SCREEN_WIDTH // 2, HORIZON_Y), (SCREEN_WIDTH, SCREEN_HEIGHT), 5)

        # 오브젝트 그리기 (z가 큰 순서대로 그려서 원근감 표현)
        sorted_objects = sorted(world_objects.sprites(), key=lambda s: s.world_z, reverse=True)
        for sprite in sorted_objects:
            screen.blit(sprite.image, sprite.rect)
        
        # 플레이어 그리기
        screen.blit(player.image, player.rect)

        # UI 표시
        score_text = font.render(f"Score: {score}", True, BLACK)
        screen.blit(score_text, (10, 10))

        if game_over:
            game_over_text = font.render("GAME OVER", True, (255, 0, 0))
            restart_text = font.render("Press 'R' to Restart", True, BLACK)
            screen.blit(game_over_text, game_over_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 30)))
            screen.blit(restart_text, restart_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + 20)))

        pygame.display.flip()
        clock.tick(FPS)

    return False # 루프가 정상적으로 끝나면 종료 신호 반환

def main():
    """
    Pygame을 초기화하고, 게임 루프를 관리하며, 종료를 처리합니다.
    """
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Antarctic Adventure")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 50)

    # game_loop가 True를 반환하는 동안 (재시작) 계속 루프를 돕니다.
    while game_loop(screen, clock, font):
        pass

    pygame.quit()

if __name__ == '__main__':
    main()
