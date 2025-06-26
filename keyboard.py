import pygame
import pygame.mixer
import sys
import os
import ctypes
from pygame.locals import *

# Initialize pygame
pygame.init()
pygame.mixer.init()

# Constants
WIDTH, HEIGHT = 850, 380
BG_COLOR = (20, 20, 20)
KEY_COLOR = (40, 40, 40)
KEY_PRESSED_COLOR = (80, 80, 80)
GLOW_COLOR = (150, 150, 255)
TEXT_COLOR = (220, 220, 220)
ROUND_RADIUS = 15
KEY_TEXT_COLOR = (240, 240, 240)
TEXT_DISPLAY_HEIGHT = 40
TEXT_AREA_COLOR = (30, 30, 30)
GLOW_SIZE = 2
TITLE_BAR_HEIGHT = 0
BUTTON_SIZE = 20
KEY_SPACING = 10
WPM_UPDATE_INTERVAL = 1000
WPM_FONT_SIZE = 16
WPM_COLOR = (180, 180, 255)
WPM_COUNTER_WIDTH = 100
WPM_COUNTER_HEIGHT = 50  # Same as key_size

# Create the window without title bar
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)
clock = pygame.time.Clock()

# Make window transparent for cursor
try:
    hwnd = pygame.display.get_wm_info()["window"]
    ctypes.windll.user32.SetWindowLongA(hwnd, -20, 0x00080000)
except:
    pass

# Load custom click sound
try:
    click_sound = pygame.mixer.Sound("click.wav")
except Exception as e:
    print(f"Error loading sound: {e}. Using fallback sound.")
    click_sound = pygame.mixer.Sound(buffer=bytearray(100))

# Load custom images
def load_image(name, scale=1.0):
    try:
        image = pygame.image.load(name)
        if scale != 1.0:
            new_size = (int(image.get_width() * scale), int(image.get_height() * scale))
            image = pygame.transform.scale(image, new_size)
        return image
    except:
        print(f"Couldn't load image: {name}. Using colored rectangle instead.")
        return None

bg_image = load_image("background.jpg", scale=WIDTH/1920)
keycap_image = load_image("keycap.png", scale=0.2)
keycap_pressed_image = load_image("keycap_pressed.png", scale=0.2)

# Keyboard layout
key_layout = [
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'BACK'],
    ['Z', 'X', 'C', 'V', 'B', 'N', 'M', 'ENTER']
]

# Special keys row
special_keys_layout = ['SPACE']

# Key positions and sizes with spacing
key_positions = {}
key_size = 60
start_x = ((WIDTH - (len(key_layout[0]) * (key_size + KEY_SPACING))) // 2) - 50 

# Create key positions for each alphanumeric row with spacing
for i, row in enumerate(key_layout):
    row_start_x = start_x
    if i == 1:  # Second row
        row_start_x += (key_size + KEY_SPACING) // 2
    elif i == 2:  # Third row
        row_start_x += (key_size + KEY_SPACING)
    
    for j, key in enumerate(row):
        width = key_size
        if key == 'BACK':
            width = key_size * 1.5
        elif key == 'ENTER':
            width = key_size * 1.5
        
        key_positions[key] = {
            'rect': pygame.Rect(
                row_start_x + j * (key_size + KEY_SPACING) + 20,
                TITLE_BAR_HEIGHT + 50 + i * (key_size + KEY_SPACING),
                width,
                key_size
            ),
            'pressed': False,
            'color': KEY_COLOR,
            'image': None,
            'pressed_image': None
        }

# Adjust ENTER key position to make room for WPM counter
key_positions['ENTER'] = {
    'rect': pygame.Rect(
        WIDTH - ( key_size + 70) - WPM_COUNTER_WIDTH - KEY_SPACING * 2,
        TITLE_BAR_HEIGHT + 50 + 2 * (key_size + KEY_SPACING),
        key_size * 1.5,
        key_size
    ),
    'pressed': False,
    'color': KEY_COLOR,
    'image': None,
    'pressed_image': None
}

# Spacebar (centered below the main keys with spacing)
space_start_x = (WIDTH - (key_size * 6 + KEY_SPACING * 5)) // 2
key_positions['SPACE'] = {
    'rect': pygame.Rect(
        space_start_x + 10,
        TITLE_BAR_HEIGHT + 50 + 3 * (key_size + KEY_SPACING),
        key_size * 6 + KEY_SPACING * 5,
        key_size
    ),
    'pressed': False,
    'color': KEY_COLOR,
    'image': None,
    'pressed_image': None
}

# WPM counter position
wpm_counter_rect = pygame.Rect(
    WIDTH - WPM_COUNTER_WIDTH - 40,
    TITLE_BAR_HEIGHT + 55 + 2 * (key_size + KEY_SPACING),
    WPM_COUNTER_WIDTH,
    WPM_COUNTER_HEIGHT
)

# Load fonts
try:
    title_font = pygame.font.SysFont('Consolas', 24, bold=True)
    font = pygame.font.SysFont('Consolas', 24, bold=True)
    key_font = pygame.font.SysFont('Consolas', 18, bold=True)
    special_key_font = pygame.font.SysFont('Consolas', 16, bold=True)
    button_font = pygame.font.SysFont('Consolas', 16, bold=True)
    wpm_font = pygame.font.SysFont('Consolas', WPM_FONT_SIZE, bold=True)
except:
    title_font = pygame.font.SysFont('Arial', 24, bold=True)
    font = pygame.font.SysFont('Arial', 24, bold=True)
    key_font = pygame.font.SysFont('Arial', 18, bold=True)
    special_key_font = pygame.font.SysFont('Arial', 16, bold=True)
    button_font = pygame.font.SysFont('Arial', 16, bold=True)
    wpm_font = pygame.font.SysFont('Arial', WPM_FONT_SIZE, bold=True)

# Text display variables
typed_text = ""
text_surface = pygame.Surface((WIDTH * 3, TEXT_DISPLAY_HEIGHT))
text_surface.fill(TEXT_AREA_COLOR)
text_x_offset = WIDTH * 3    
cursor_position = 0
cursor_visible = False
cursor_timer = 0

# WPM calculation variables
last_keypress_time = pygame.time.get_ticks()
keypress_count = 0
current_wpm = 0
last_wpm_update = 0

def calculate_wpm(keypresses, time_elapsed):
    """Calculate words per minute based on keypresses"""
    if time_elapsed == 0:
        return 0
    minutes = time_elapsed / 60000  # Convert ms to minutes
    words = keypresses / 6  # Approximate words (5 chars + 1 space)
    return int(words / minutes)

# Window control buttons
close_button_rect = pygame.Rect(WIDTH - BUTTON_SIZE - 10, 10, BUTTON_SIZE, BUTTON_SIZE)
minimize_button_rect = pygame.Rect(WIDTH - 2 * BUTTON_SIZE - 20, 10, BUTTON_SIZE, BUTTON_SIZE)

# Dragging variables
dragging = False
drag_start_pos = (0, 0)
window_pos = [100, 100]  # Initial window position

def draw_rounded_rect_with_glow(surface, rect, color, glow_color, radius=15, glow_size=5):
    """Draw a rounded rectangle with glowing border"""
    # Draw glow
    glow_rect = rect.inflate(glow_size * 2, glow_size * 2)
    pygame.draw.rect(surface, glow_color, glow_rect, border_radius=radius + glow_size)
    
    # Draw main key
    pygame.draw.rect(surface, color, rect, border_radius=radius)

# Key mapping
key_mapping = {
    K_q: 'Q', K_w: 'W', K_e: 'E', K_r: 'R', K_t: 'T', K_y: 'Y', 
    K_u: 'U', K_i: 'I', K_o: 'O', K_p: 'P',
    K_a: 'A', K_s: 'S', K_d: 'D', K_f: 'F', K_g: 'G', K_h: 'H',
    K_j: 'J', K_k: 'K', K_l: 'L',
    K_z: 'Z', K_x: 'X', K_c: 'C', K_v: 'V', K_b: 'B', K_n: 'N',
    K_m: 'M',
    K_SPACE: 'SPACE', K_BACKSPACE: 'BACK', K_RETURN: 'ENTER',
    K_LSHIFT: 'SHIFT', K_RSHIFT: 'SHIFT',
    K_LEFT: 'LEFT', K_RIGHT: 'RIGHT',
    K_ESCAPE: 'QUIT'
}

# Main loop
running = True
while running:
    # Draw background
    if bg_image:
        scaled_bg = pygame.transform.scale(bg_image, (WIDTH, HEIGHT))
        screen.blit(scaled_bg, (0, 0))
    else:
        screen.fill(BG_COLOR)
    
    # Draw title bar area
    pygame.draw.rect(screen, (30, 30, 30), (0, 0, WIDTH, TITLE_BAR_HEIGHT))
    
    # Draw title
    title_text = title_font.render("YOUR VIRTUAL KEYBOARD", True, (255, 255, 255))
    screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, 10))
    
    # Draw window control buttons
    pygame.draw.rect(screen, (200, 50, 50), close_button_rect, border_radius=10)
    pygame.draw.rect(screen, (200, 200, 50), minimize_button_rect, border_radius=10)
    
    close_text = button_font.render("X", True, (255, 255, 255))
    minimize_text = button_font.render("-", True, (255, 255, 255))
    
    screen.blit(close_text, (close_button_rect.centerx - close_text.get_width() // 2, 
                            close_button_rect.centery - close_text.get_height() // 2))
    screen.blit(minimize_text, (minimize_button_rect.centerx - minimize_text.get_width() // 2, 
                               minimize_button_rect.centery - minimize_text.get_height() // 2))
    
    # Update WPM calculation
    current_time = pygame.time.get_ticks()
    if current_time - last_wpm_update > WPM_UPDATE_INTERVAL:
        time_elapsed = current_time - last_wpm_update
        current_wpm = calculate_wpm(keypress_count, time_elapsed)
        last_wpm_update = current_time
        keypress_count = 0
    
    # Handle events
    for event in pygame.event.get():
        if event.type == QUIT:
            running = False
        
        elif event.type == KEYDOWN:
            if event.key in key_mapping:
                key = key_mapping[event.key]
                
                if key == 'QUIT':
                    running = False
                elif key not in ['LEFT', 'RIGHT', 'SHIFT']:
                    click_sound.play()
                    keypress_count += 1
                
                if key == 'BACK':
                    if cursor_position > 0:
                        typed_text = typed_text[:cursor_position-1] + typed_text[cursor_position:]
                        cursor_position = max(0, cursor_position - 1)
                elif key == 'SPACE':
                    typed_text = typed_text[:cursor_position] + ' ' + typed_text[cursor_position:]
                    cursor_position += 1
                elif key == 'SHIFT':
                    typed_text = ""
                    cursor_position = 0
                    text_x_offset = 0
                elif key == 'ENTER':
                    typed_text = typed_text[:cursor_position] + '\n' + typed_text[cursor_position:]
                    cursor_position += 1
                elif key == 'LEFT':
                    cursor_position = max(0, cursor_position - 1)
                elif key == 'RIGHT':
                    cursor_position = min(len(typed_text), cursor_position + 1)
                elif key in key_positions:
                    typed_text = typed_text[:cursor_position] + key.lower() + typed_text[cursor_position:]
                    cursor_position += 1
                
                if key in key_positions:
                    key_positions[key]['pressed'] = True
                    key_positions[key]['color'] = KEY_PRESSED_COLOR
        
        elif event.type == KEYUP:
            if event.key in key_mapping:
                key = key_mapping[event.key]
                if key in key_positions:
                    key_positions[key]['pressed'] = False
                    key_positions[key]['color'] = KEY_COLOR
        
        # Handle mouse wheel for text scrolling
        elif event.type == pygame.MOUSEWHEEL:
            text_x_offset += event.y * 20
            text_x_offset = max(min(text_x_offset, 0), -(font.size(typed_text)[0] - WIDTH + 40))
        
        # Handle window dragging and buttons
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            if close_button_rect.collidepoint(mouse_pos):
                running = False
            elif minimize_button_rect.collidepoint(mouse_pos):
                pygame.display.iconify()
            elif mouse_pos[1] <= TITLE_BAR_HEIGHT:  # Title bar area
                dragging = True
                drag_start_pos = mouse_pos
        
        elif event.type == pygame.MOUSEBUTTONUP:
            dragging = False
        
        elif event.type == pygame.MOUSEMOTION:
            if dragging:
                mouse_pos = pygame.mouse.get_pos()
                rel_x = mouse_pos[0] - drag_start_pos[0]
                rel_y = mouse_pos[1] - drag_start_pos[1]
                window_pos[0] += rel_x
                window_pos[1] += rel_y
                os.environ['SDL_VIDEO_WINDOW_POS'] = f"{window_pos[0]},{window_pos[1]}"
                drag_start_pos = mouse_pos
    
    # Update cursor blink
    #cursor_timer += 1
    #if cursor_timer >= 30:
        cursor_visible = not cursor_visible
        #cursor_timer = 0
    
    # Draw keys with glow effect and spacing
    for key, data in key_positions.items():
        rect = data['rect']
        color = KEY_PRESSED_COLOR if data['pressed'] else KEY_COLOR
        
        # Adjust rect for spacing
        spaced_rect = rect.inflate(-KEY_SPACING, -KEY_SPACING)
        draw_rounded_rect_with_glow(screen, spaced_rect, color, GLOW_COLOR, ROUND_RADIUS, GLOW_SIZE)
        
        if key in ['SPACE', 'BACK', 'ENTER']:
            label = {'SPACE': 'Space', 'BACK': 'Back', 'ENTER': 'Enter'}.get(key, key)
            text_surf = special_key_font.render(label, True, KEY_TEXT_COLOR)
        else:
            label = key
            text_surf = key_font.render(label, True, KEY_TEXT_COLOR)
        
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)
    
    # Draw WPM counter to the right of ENTER key
    pygame.draw.rect(screen, (50, 50, 70), wpm_counter_rect, border_radius=ROUND_RADIUS)
    wpm_text = wpm_font.render(f"{current_wpm} WPM", True, WPM_COLOR)
    wpm_text_rect = wpm_text.get_rect(center=wpm_counter_rect.center)
    screen.blit(wpm_text, wpm_text_rect)
    
    # Update text display surface
    text_surface.fill(TEXT_AREA_COLOR)
    text_width = font.size(typed_text)[0]
    
    # Calculate cursor position in pixels
    text_before_cursor = typed_text[:cursor_position]
    cursor_x = font.size(text_before_cursor)[0] + 20
    
    # Auto-scroll to follow cursor (starting from left)
    visible_start = text_x_offset
    visible_end = visible_start + WIDTH - 40
    
    # Always show cursor, scrolling when it reaches right 3/4 of window
    if cursor_x > (WIDTH * 3 // 4):
        text_x_offset = -(cursor_x - (WIDTH * 3 // 4))
    elif cursor_x < 20:  # Keep cursor visible at left edge
        text_x_offset = -cursor_x + 20
    
    text_x_offset = max(min(text_x_offset, 0), -(text_width - (WIDTH - 40)))
    
    # Draw text on the wider surface
    text_surf = font.render(typed_text, True, TEXT_COLOR)
    text_surface.blit(text_surf, (20 + text_x_offset, 15))
    
    # Draw cursor if visible (transparent effect)
    if cursor_visible:
        cursor_surface = pygame.Surface((2, TEXT_DISPLAY_HEIGHT - 20), pygame.SRCALPHA)
        cursor_surface.fill((*TEXT_COLOR, 150))  # Semi-transparent
        text_surface.blit(cursor_surface, (cursor_x + text_x_offset, 20))
    
    # Draw text display area
    screen.blit(text_surface.subsurface((0, 0, WIDTH, TEXT_DISPLAY_HEIGHT)), 
               (0, HEIGHT - TEXT_DISPLAY_HEIGHT))
    
    # Draw scroll indicator if needed
    # if text_width > WIDTH - 40:
    #     scroll_ratio = -text_x_offset / (text_width - (WIDTH - 40))
    #     scrollbar_width = 100
    #     scrollbar_x = (WIDTH - scrollbar_width) * scroll_ratio
        
    #     pygame.draw.rect(screen, (80, 80, 80), (0, HEIGHT - 5, WIDTH, 5))
    #     pygame.draw.rect(screen, (150, 150, 150), (scrollbar_x, HEIGHT - 5, scrollbar_width, 5))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()