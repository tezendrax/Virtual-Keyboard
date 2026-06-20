import cv2
from cvzone.HandTrackingModule import HandDetector
import numpy as np
import time
from pynput.keyboard import Controller, Key

# Initialize webcam
cap = cv2.VideoCapture(0)
cap.set(3, 1280) # Width
cap.set(4, 720)  # Height

# Initialize hand detector with a confidence of 0.8 to prevent false tracking
detector = HandDetector(detectionCon=0.8, maxHands=1)

# Keyboard state variables
finalText = ""
isCaps = True
keyboard = Controller()

# WPM and Keystroke tracking variables for the HUD side panel
typing_start_time = None
total_keys_pressed = 0

# Debounce and click variables
last_click_time = 0
click_cooldown = 0.45  # Cooldown in seconds to prevent double typing
clicked_key = None
clicked_key_timer = 0  # Number of frames to keep the clicked style visible

class Button:
    def __init__(self, pos, text, size=[85, 85]):
        self.pos = pos
        self.text = text
        self.size = size

# Define keys rows
keys_row1 = ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"]
keys_row2 = ["A", "S", "D", "F", "G", "H", "J", "K", "L", ";"]
keys_row3 = ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/"]

buttonList = []

# Populate standard keys (Shifted right and uplifted layout with extra spacing)
# Total keyboard width is around 1062px (10 buttons of 90px width + 18px gaps)
start_x = 166
gap = 18

for j, key in enumerate(keys_row1):
    buttonList.append(Button([start_x + j * (90 + gap), 125], key, [90, 90]))

for j, key in enumerate(keys_row2):
    buttonList.append(Button([start_x + j * (90 + gap), 233], key, [90, 90]))

for j, key in enumerate(keys_row3):
    buttonList.append(Button([start_x + j * (90 + gap), 341], key, [90, 90]))

# Populate special keys (Shifted right and shifted downwards layout with 18px gaps)
# Caps(140), Space(400), Backspace(150), Enter(150), Clear(150) with 18px gaps = 1062px total width
# Centering start_x for Row 4 = 166
buttonList.append(Button([166, 449], "Caps", [140, 90]))
buttonList.append(Button([166 + 140 + gap, 449], "Space", [400, 90]))
buttonList.append(Button([166 + 140 + gap + 400 + gap, 449], "Backspace", [150, 90]))
buttonList.append(Button([166 + 140 + gap + 400 + gap + 150 + gap, 449], "Enter", [150, 90]))
buttonList.append(Button([166 + 140 + gap + 400 + gap + 150 + gap + 150 + gap, 449], "Clear", [150, 90]))

def drawAll(img, buttonList, active_button=None, clicked_button=None, isCaps=True):
    """
    Renders the virtual keyboard on a transparent overlay layer and blends it with the camera frame.
    Separates background panel transparency and key transparency for a premium glassmorphism look.
    """
    # Draw distinct keys with transparency directly on camera feed background
    overlay_keys = img.copy()
    for button in buttonList:
        if clicked_button == button or active_button == button:
            continue # We will draw the hovered/clicked keys later on top with high opacity/solid style
            
        x, y = button.pos
        w, h = button.size
        
        bg_color = (75, 15, 3)         # Much darker navy blue for default state (BGR)
        border_color = (105, 25, 5)    # Matching dark navy border outline
        text_color = (255, 255, 255)   # Crisp white text
        inner_glow = (255, 190, 80)  # Bright neon cyan/blue glow
            
        # Draw key backgrounds and borders
        cv2.rectangle(overlay_keys, (x, y), (x + w, y + h), bg_color, cv2.FILLED)
        cv2.rectangle(overlay_keys, (x, y), (x + w, y + h), border_color, 2) # Outer border
        cv2.rectangle(overlay_keys, (x + 2, y + 2), (x + w - 2, y + h - 2), inner_glow, 1)
        
        # Adjust capitalization of key text
        display_text = button.text
        if len(display_text) == 1 and display_text.isalpha():
            display_text = display_text.upper() if isCaps else display_text.lower()
            
        # Draw centered text inside keys
        font = cv2.FONT_HERSHEY_DUPLEX
        
        # Optimize font size for special keys and standard keys
        if display_text == "Caps":
            font_scale = 1.15
        elif display_text == "Space":
            font_scale = 1.1
        elif display_text == "Backspace":
            font_scale = 0.7  # Prevent overflow for longer word
        elif display_text in ["Enter", "Clear"]:
            font_scale = 0.95
        else:
            font_scale = 0.9 if len(display_text) > 1 else 1.3
            
        thickness = 2
        text_size = cv2.getTextSize(display_text, font, font_scale, thickness)[0]
        text_w, text_h = text_size[0], text_size[1]
        
        text_x = x + (w - text_w) // 2
        text_y = y + (h + text_h) // 2
        
        cv2.putText(overlay_keys, display_text, (text_x, text_y), font, font_scale, text_color, thickness, cv2.LINE_AA)
        
    alpha_keys = 0.52 # Slightly more solid frosted keys
    cv2.addWeighted(overlay_keys, alpha_keys, img, 1 - alpha_keys, 0, img)
    
    # Render the hovered key on top with a much higher opacity (0.85) to decrease its transparency
    if active_button and active_button != clicked_button:
        x, y = active_button.pos
        w, h = active_button.size
        
        bg_color = (60, 0, 60)        # Deeper rich dark purple for hover
        border_color = (100, 10, 100) # Dark purple border
        inner_glow = (240, 100, 240) # Bright neon purple glow
        text_color = (255, 255, 255)  # Crisp white text
        
        overlay_hover = img.copy()
        cv2.rectangle(overlay_hover, (x, y), (x + w, y + h), bg_color, cv2.FILLED)
        cv2.rectangle(overlay_hover, (x, y), (x + w, y + h), border_color, 2)
        cv2.rectangle(overlay_hover, (x + 2, y + 2), (x + w - 2, y + h - 2), inner_glow, 1)
        
        display_text = active_button.text
        if len(display_text) == 1 and display_text.isalpha():
            display_text = display_text.upper() if isCaps else display_text.lower()
            
        font = cv2.FONT_HERSHEY_DUPLEX
        if display_text == "Caps":
            font_scale = 1.15
        elif display_text == "Space":
            font_scale = 1.1
        elif display_text == "Backspace":
            font_scale = 0.7
        elif display_text in ["Enter", "Clear"]:
            font_scale = 0.95
        else:
            font_scale = 0.9 if len(display_text) > 1 else 1.3
            
        thickness = 2
        text_size = cv2.getTextSize(display_text, font, font_scale, thickness)[0]
        text_w, text_h = text_size[0], text_size[1]
        text_x = x + (w - text_w) // 2
        text_y = y + (h + text_h) // 2
        cv2.putText(overlay_hover, display_text, (text_x, text_y), font, font_scale, text_color, thickness, cv2.LINE_AA)
        
        alpha_hover = 0.85 # Highly solid hover appearance (decreased transparency)
        cv2.addWeighted(overlay_hover, alpha_hover, img, 1 - alpha_hover, 0, img)
    
    # Render the clicked key on top with a much higher opacity (0.88) to decrease its transparency
    if clicked_button:
        x, y = clicked_button.pos
        w, h = clicked_button.size
        
        bg_color = (15, 110, 30)      # Vivid dark green background
        border_color = (35, 170, 50)  # Solid green border
        inner_glow = (80, 240, 120)   # Glowing neon green inner outline
        text_color = (255, 255, 255)  # Crisp white text
        
        overlay_click = img.copy()
        cv2.rectangle(overlay_click, (x, y), (x + w, y + h), bg_color, cv2.FILLED)
        cv2.rectangle(overlay_click, (x, y), (x + w, y + h), border_color, 2)
        cv2.rectangle(overlay_click, (x + 2, y + 2), (x + w - 2, y + h - 2), inner_glow, 1)
        
        # Center key text capitalization
        display_text = clicked_button.text
        if len(display_text) == 1 and display_text.isalpha():
            display_text = display_text.upper() if isCaps else display_text.lower()
            
        font = cv2.FONT_HERSHEY_DUPLEX
        if display_text == "Caps":
            font_scale = 1.15
        elif display_text == "Space":
            font_scale = 1.1
        elif display_text == "Backspace":
            font_scale = 0.7
        elif display_text in ["Enter", "Clear"]:
            font_scale = 0.95
        else:
            font_scale = 0.9 if len(display_text) > 1 else 1.3
            
        thickness = 2
        text_size = cv2.getTextSize(display_text, font, font_scale, thickness)[0]
        text_w, text_h = text_size[0], text_size[1]
        text_x = x + (w - text_w) // 2
        text_y = y + (h + text_h) // 2
        cv2.putText(overlay_click, display_text, (text_x, text_y), font, font_scale, text_color, thickness, cv2.LINE_AA)
        
        alpha_click = 0.88 # Very solid click appearance
        cv2.addWeighted(overlay_click, alpha_click, img, 1 - alpha_click, 0, img)
        
    return img

def drawTextBox(img, text, isCaps):
    """
    Renders a stylized text display field showing current typing progress and cursors.
    Also displays the Caps Lock status badge outside the text box on the right.
    """
    # Stage 1: Draw highly translucent textbox background panel (166 to 1194)
    overlay_bg = img.copy()
    cv2.rectangle(overlay_bg, (166, 15), (1194, 95), (35, 25, 40), cv2.FILLED)
    alpha_bg = 0.10 # Translucent textbox background fill
    cv2.addWeighted(overlay_bg, alpha_bg, img, 1 - alpha_bg, 0, img)
    
    # Stage 2: Draw crisp text, double stylish border, and Caps Lock badge
    overlay_fg = img.copy()
    cv2.rectangle(overlay_fg, (166, 15), (1194, 95), (150, 70, 180), 2) # Sharp outer border
    cv2.rectangle(overlay_fg, (170, 19), (1190, 91), (220, 120, 245), 1) # Glowing inner accent border
    
    # Subtle asymmetrical neon pink corner accent lines
    accent_color = (255, 150, 255)
    # Top-Left accent
    cv2.line(overlay_fg, (166, 15), (178, 15), accent_color, 2, cv2.LINE_AA)
    cv2.line(overlay_fg, (166, 15), (166, 27), accent_color, 2, cv2.LINE_AA)
    # Bottom-Right accent
    cv2.line(overlay_fg, (1194, 95), (1182, 95), accent_color, 2, cv2.LINE_AA)
    cv2.line(overlay_fg, (1194, 95), (1194, 83), accent_color, 2, cv2.LINE_AA)
    
    # Blinking terminal cursor
    cursor = "|" if int(time.time() * 2.5) % 2 == 0 else ""
    display_text = text + cursor
    
    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale = 1.1
    thickness = 3 # Bold font thickness
    
    # Prevent text overflow
    while len(display_text) > 0:
        size = cv2.getTextSize(display_text, font, font_scale, thickness)[0]
        if size[0] < (1194 - 166 - 40): # Full width margin within textbox
            break
        display_text = display_text[1:]
        
    # Render typing text in bold black
    text_y = 15 + (80 + 20) // 2
    cv2.putText(overlay_fg, display_text, (196, text_y), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)
    
    # Render Caps Lock overlay badge outside the text box on the right
    badge_x = 1198
    badge_y = 30
    badge_w = 72
    badge_h = 50
    badge_bg = (100, 30, 120) if isCaps else (50, 50, 50)
    badge_border = (200, 80, 220) if isCaps else (100, 100, 100)
    
    cv2.rectangle(overlay_fg, (badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h), badge_bg, cv2.FILLED)
    cv2.rectangle(overlay_fg, (badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h), badge_border, 1)
    
    badge_text = "CAPS ON" if isCaps else "caps off"
    badge_font_scale = 0.43
    badge_text_size = cv2.getTextSize(badge_text, font, badge_font_scale, 1)[0]
    badge_text_x = badge_x + (badge_w - badge_text_size[0]) // 2
    badge_text_y = badge_y + (badge_h + badge_text_size[1]) // 2
    cv2.putText(overlay_fg, badge_text, (badge_text_x, badge_text_y), font, badge_font_scale, (255, 255, 255), 1, cv2.LINE_AA)
    
    alpha_fg = 0.85 # High opacity for text and borders
    cv2.addWeighted(overlay_fg, alpha_fg, img, 1 - alpha_fg, 0, img)
    return img

def drawSidePanel(img, lmList, active_button, wpm, total_keys_pressed, isCaps):
    """
    Renders a simple, highly visual sidebar HUD in the left margin.
    Contains hand connection status, hovered key target, a live click press-meter, and typing stats.
    """
    overlay = img.copy()
    
    # Side panel bounds: X: 20 to 112, Y: 15 to 539 (aligned with keyboard bottom boundary)
    cv2.rectangle(overlay, (20, 15), (112, 539), (30, 20, 35), cv2.FILLED)
    cv2.rectangle(overlay, (20, 15), (112, 539), (150, 70, 180), 2) # Elegant purple border
    
    font = cv2.FONT_HERSHEY_DUPLEX
    
    # 1. Hand Connection Status
    status_text = "HAND"
    cv2.putText(overlay, status_text, (28, 45), font, 0.45, (150, 150, 150), 1, cv2.LINE_AA)
    
    if lmList:
        cv2.rectangle(overlay, (28, 55), (104, 80), (40, 180, 80), cv2.FILLED) # Green box
        cv2.putText(overlay, "ONLINE", (35, 73), font, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
    else:
        cv2.rectangle(overlay, (28, 55), (104, 80), (50, 50, 200), cv2.FILLED) # Red box
        cv2.putText(overlay, "OFFLINE", (31, 73), font, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
        
    # 2. Target Key currently hovered
    cv2.putText(overlay, "TARGET", (28, 115), font, 0.45, (150, 150, 150), 1, cv2.LINE_AA)
    target_char = active_button.text if active_button else "-"
    
    # Draw key box display
    cv2.rectangle(overlay, (36, 125), (96, 185), (60, 45, 55), cv2.FILLED)
    cv2.rectangle(overlay, (36, 125), (96, 185), (95, 80, 100), 1)
    
    t_size = cv2.getTextSize(target_char, font, 0.8, 2)[0]
    t_x = 36 + (60 - t_size[0]) // 2
    t_y = 125 + (60 + t_size[1]) // 2
    cv2.putText(overlay, target_char, (t_x, t_y), font, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    
    # 3. Press Click Meter
    cv2.putText(overlay, "PRESS", (28, 220), font, 0.45, (150, 150, 150), 1, cv2.LINE_AA)
    
    # Calculate index-middle pinch percentage
    pct = 0
    if lmList:
        idx_x, idx_y = lmList[8][0], lmList[8][1]
        mid_x, mid_y = lmList[12][0], lmList[12][1]
        distance = np.hypot(idx_x - mid_x, idx_y - mid_y)
        # Map distance [35, 100] to [100, 0]
        pct = int(max(0, min(100, (100 - distance) / (100 - 35) * 100)))
        
    # Draw progress bar container (vertical bar)
    bar_y_start = 230
    bar_y_end = 360
    bar_h = bar_y_end - bar_y_start # 130px
    cv2.rectangle(overlay, (46, bar_y_start), (86, bar_y_end), (50, 40, 50), cv2.FILLED)
    cv2.rectangle(overlay, (46, bar_y_start), (86, bar_y_end), (100, 80, 100), 1)
    
    # Fill progress bar based on percentage
    if pct > 0:
        fill_h = int(bar_h * (pct / 100.0))
        # Turn green if clicked (>=95%), white color (255, 255, 255) otherwise
        fill_color = (15, 110, 30) if pct >= 95 else (105, 25, 5)
        cv2.rectangle(overlay, (47, bar_y_end - fill_h), (85, bar_y_end - 1), fill_color, cv2.FILLED)
        
    # Render percentage text below bar
    pct_text = f"{pct}%"
    pct_size = cv2.getTextSize(pct_text, font, 0.4, 1)[0]
    cv2.putText(overlay, pct_text, (66 - pct_size[0] // 2, bar_y_end + 18), font, 0.4, (235, 235, 235), 1, cv2.LINE_AA)
    
    # 4. Typing Statistics (Spaced out for the longer side bar)
    cv2.putText(overlay, "STATS", (28, 420), font, 0.45, (150, 150, 150), 1, cv2.LINE_AA)
    
    wpm_text = f"WPM: {wpm}"
    keys_text = f"Keys: {total_keys_pressed}"
    caps_text = "CAPS: ON" if isCaps else "CAPS: OFF"
    
    cv2.putText(overlay, wpm_text, (28, 450), font, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(overlay, keys_text, (28, 480), font, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
    
    # Highlight Caps Lock in purple if active, grey otherwise
    caps_color = (220, 80, 200) if isCaps else (150, 150, 150)
    cv2.putText(overlay, caps_text, (28, 510), font, 0.4, caps_color, 1, cv2.LINE_AA)
    
    # Apply alpha blending for translucent look (match side panel transparency)
    alpha = 0.93
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    return img

print("Initializing camera feed... Hover index finger to target keys. Pinch index & middle finger tips to type.")

while True:
    success, img = cap.read()
    if not success:
        print("Error reading camera frame. Exiting...")
        break
        
    # Flip the image horizontally for a natural mirror view
    img = cv2.flip(img, 1)
    
    # Detect hand (with cvzone drawing disabled so we can render our custom premium lines)
    result = detector.findHands(img, draw=False)
    
    if isinstance(result, tuple):
        hands, img = result
    else:
        hands = result
        
    lmList = []
    if hands:
        # Get coordinates for the first hand detected
        lmList = hands[0]["lmList"]
        
    active_button = None
    
    # Check if index finger is hovering over any button
    if lmList:
        # lmList[8] is index finger tip. [x, y, z]
        idx_x, idx_y = lmList[8][0], lmList[8][1]
        
        for button in buttonList:
            x, y = button.pos
            w, h = button.size
            if x < idx_x < x + w and y < idx_y < y + h:
                active_button = button
                break
                
    # Detect and handle click event
    distance = None
    if active_button and lmList:
        # lmList[8] (index tip) and lmList[12] (middle tip)
        idx_x, idx_y = lmList[8][0], lmList[8][1]
        mid_x, mid_y = lmList[12][0], lmList[12][1]
        
        # Calculate Euclidean distance
        distance = np.hypot(idx_x - mid_x, idx_y - mid_y)
        
        # Trigger typing logic on click gesture (< 35px)
        current_time = time.time()
        if distance < 35:
            if current_time - last_click_time > click_cooldown:
                clicked_key = active_button
                clicked_key_timer = 6 # Render green click state for 6 frames
                last_click_time = current_time
                
                # Start WPM tracking timer on first keypress
                if typing_start_time is None:
                    typing_start_time = current_time
                
                # Execute keyboard inputs and feed to active OS app
                key_text = active_button.text
                if key_text == "Space":
                    keyboard.type(" ")
                    finalText += " "
                    total_keys_pressed += 1
                elif key_text == "Backspace":
                    keyboard.press(Key.backspace)
                    keyboard.release(Key.backspace)
                    if len(finalText) > 0:
                        finalText = finalText[:-1]
                    total_keys_pressed = max(0, total_keys_pressed - 1)
                elif key_text == "Caps":
                    isCaps = not isCaps
                elif key_text == "Clear":
                    finalText = ""
                    typing_start_time = None
                    total_keys_pressed = 0
                elif key_text == "Enter":
                    keyboard.press(Key.enter)
                    keyboard.release(Key.enter)
                    finalText += "\n"
                    total_keys_pressed += 1
                else:
                    # Append letter key (upper or lowercase)
                    char = key_text.upper() if isCaps else key_text.lower()
                    keyboard.type(char)
                    finalText += char
                    total_keys_pressed += 1

    # Manage clicked highlight timer
    if clicked_key_timer > 0:
        clicked_key_timer -= 1
    else:
        clicked_key = None
        
    # Calculate WPM (Words Per Minute)
    wpm = 0
    if typing_start_time is not None:
        elapsed = (time.time() - typing_start_time) / 60.0
        if elapsed > 0.005: # Calculate after 0.3 seconds to avoid infinity spike
            wpm = int((total_keys_pressed / 5.0) / elapsed)
        
    # Stage 1: Render keyboard layout (this draws the keys)
    img = drawAll(img, buttonList, active_button, clicked_key, isCaps)
    
    # Stage 2: Draw hand skeleton & interaction indicator on TOP of the keys (soft & translucent)
    if lmList:
        overlay_hand = img.copy()
        
        # 1. Translucent palm energy field polygon
        palm_pts = np.array([
            [lmList[0][0], lmList[0][1]],
            [lmList[1][0], lmList[1][1]],
            [lmList[2][0], lmList[2][1]],
            [lmList[5][0], lmList[5][1]],
            [lmList[9][0], lmList[9][1]],
            [lmList[13][0], lmList[13][1]],
            [lmList[17][0], lmList[17][1]]
        ], dtype=np.int32)
        
        # Fill polygon on a separate temporary overlay to keep palm area extremely subtle (low fill opacity)
        overlay_palm = overlay_hand.copy()
        cv2.fillPoly(overlay_palm, [palm_pts], (240, 130, 20))
        cv2.addWeighted(overlay_palm, 0.20, overlay_hand, 0.80, 0, overlay_hand)
        
        # Define connection pairs for standard MediaPipe hand landmark skeleton
        connections = [
            (0, 1), (1, 2), (2, 3), (3, 4),      # Thumb
            (0, 5), (5, 6), (6, 7), (7, 8),      # Index
            (9, 10), (10, 11), (11, 12),         # Middle
            (13, 14), (14, 15), (15, 16),        # Ring
            (0, 17), (17, 18), (18, 19), (19, 20),# Pinky
            (5, 9), (9, 13), (13, 17),           # Knuckle base connections
            (1, 5)                               # Connect thumb base to index base to structure the palm
        ]
        
        # 2. Draw connections with glowing neon light blue tubes (light blue outer glow with white inner core)
        for p1, p2 in connections:
            x1, y1 = lmList[p1][0], lmList[p1][1]
            x2, y2 = lmList[p2][0], lmList[p2][1]
            cv2.line(overlay_hand, (x1, y1), (x2, y2), (240, 130, 20), 2, cv2.LINE_AA) # Outer light blue glow
            cv2.line(overlay_hand, (x1, y1), (x2, y2), (255, 255, 255), 1, cv2.LINE_AA) # Sharp white core
            
        # 3. Draw joint nodes & fingertip target reticles (neon purple)
        # Filter to only draw 3 dots per finger (Thumb: 2, 3, 4; Index: 5, 6, 8; Middle: 9, 10, 12; Ring: 13, 14, 16; Pinky: 17, 18, 20)
        allowed_dots = {2, 3, 4, 5, 6, 8, 9, 10, 12, 13, 14, 16, 17, 18, 20}
        for i, lm in enumerate(lmList):
            if i not in allowed_dots:
                continue
            cx, cy = lm[0], lm[1]
            if i in [8, 12]: # Index tip (8) and Middle tip (12) used for target and click
                # Cyber target reticle
                cv2.circle(overlay_hand, (cx, cy), 9, (240, 100, 240), 1, cv2.LINE_AA) # Outer ring
                cv2.circle(overlay_hand, (cx, cy), 3, (240, 100, 240), cv2.FILLED)    # Center node
                # Reticle ticks
                cv2.line(overlay_hand, (cx - 13, cy), (cx - 7, cy), (240, 100, 240), 1, cv2.LINE_AA)
                cv2.line(overlay_hand, (cx + 7, cy), (cx + 13, cy), (240, 100, 240), 1, cv2.LINE_AA)
                cv2.line(overlay_hand, (cx, cy - 13), (cx, cy - 7), (240, 100, 240), 1, cv2.LINE_AA)
                cv2.line(overlay_hand, (cx, cy + 7), (cx, cy + 13), (240, 100, 240), 1, cv2.LINE_AA)
            else:
                # Standard joint node (neat neon purple with white core)
                cv2.circle(overlay_hand, (cx, cy), 5, (240, 100, 240), cv2.FILLED)
                cv2.circle(overlay_hand, (cx, cy), 2, (255, 255, 255), cv2.FILLED)
            
        # 4. Draw interaction indicator line
        if active_button and distance is not None:
            idx_x, idx_y = lmList[8][0], lmList[8][1]
            mid_x, mid_y = lmList[12][0], lmList[12][1]
            # Light blue (240, 130, 20) when close to clicking, Neon purple (240, 100, 240) when far
            color = (240, 130, 20) if distance < 35 else (240, 100, 240)
            cv2.line(overlay_hand, (idx_x, idx_y), (mid_x, mid_y), color, 2, cv2.LINE_AA)
            
        # Blend the hand overlay onto the image with a subtle, soft opacity
        alpha_hand = 0.60
        cv2.addWeighted(overlay_hand, alpha_hand, img, 1 - alpha_hand, 0, img)
        
    # Stage 4: Draw textbox and sidebar HUD
    img = drawTextBox(img, finalText, isCaps)
    img = drawSidePanel(img, lmList, active_button, wpm, total_keys_pressed, isCaps)
    
    cv2.imshow("Premium Virtual Keyboard", img)
    
    # Press 'q' on hardware keyboard to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
print("Session ended.")       ,