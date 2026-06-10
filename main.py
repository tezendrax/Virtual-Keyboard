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

# Populate standard keys (Centered layout)
# Total keyboard width is around 940px (10 buttons of 85px width + 10px gaps)
start_x = 170
gap = 10

for j, key in enumerate(keys_row1):
    buttonList.append(Button([start_x + j * 95, 150], key))

for j, key in enumerate(keys_row2):
    buttonList.append(Button([start_x + j * 95, 255], key))

for j, key in enumerate(keys_row3):
    buttonList.append(Button([start_x + j * 95, 360], key))

# Populate special keys (Centered layout for Row 4)
# Caps(120), Space(340), Backspace(130), Enter(120), Clear(120) with 10px gaps = 870px total width
# Centering start_x for Row 4 = (1280 - 870) / 2 = 205
buttonList.append(Button([205, 465], "Caps", [120, 85]))
buttonList.append(Button([335, 465], "Space", [340, 85]))
buttonList.append(Button([685, 465], "Backspace", [130, 85]))
buttonList.append(Button([825, 465], "Enter", [120, 85]))
buttonList.append(Button([955, 465], "Clear", [120, 85]))

def drawAll(img, buttonList, active_button=None, clicked_button=None, isCaps=True):
    """
    Renders the virtual keyboard on a transparent overlay layer and blends it with the camera frame.
    """
    overlay = img.copy()
    
    # Draw dark main keyboard background panel
    cv2.rectangle(overlay, (150, 130), (1130, 570), (25, 20, 30), cv2.FILLED)
    cv2.rectangle(overlay, (150, 130), (1130, 570), (130, 60, 150), 2) # Elegant purple border
    
    for button in buttonList:
        x, y = button.pos
        w, h = button.size
        
        # Decide styling based on button state (Normal, Hover, Clicked)
        if clicked_button == button:
            bg_color = (40, 220, 80)      # Bright green for active click
            border_color = (80, 255, 120)
            text_color = (0, 0, 0)
        elif active_button == button:
            bg_color = (180, 50, 180)     # Neon purple for hover
            border_color = (255, 120, 255)
            text_color = (255, 255, 255)
        else:
            bg_color = (55, 45, 60)       # Deep violet-grey for default state
            border_color = (95, 80, 100)
            text_color = (235, 235, 235)
            
        # Draw key backgrounds and borders
        cv2.rectangle(overlay, (x, y), (x + w, y + h), bg_color, cv2.FILLED)
        cv2.rectangle(overlay, (x, y), (x + w, y + h), border_color, 2)
        
        # Adjust capitalization of key text
        display_text = button.text
        if len(display_text) == 1 and display_text.isalpha():
            display_text = display_text.upper() if isCaps else display_text.lower()
            
        # Draw centered text inside keys
        font = cv2.FONT_HERSHEY_DUPLEX
        font_scale = 0.9 if len(display_text) > 1 else 1.3
        thickness = 2
        text_size = cv2.getTextSize(display_text, font, font_scale, thickness)[0]
        text_w, text_h = text_size[0], text_size[1]
        
        text_x = x + (w - text_w) // 2
        text_y = y + (h + text_h) // 2
        
        cv2.putText(overlay, display_text, (text_x, text_y), font, font_scale, text_color, thickness, cv2.LINE_AA)
        
    # Apply alpha blending for modern glassmorphism transparency effect
    alpha = 0.78
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    return img

def drawTextBox(img, text, isCaps):
    """
    Renders a stylized text display field showing current typing progress and cursors.
    """
    overlay = img.copy()
    
    # Glassmorphism panel for the textbox
    cv2.rectangle(overlay, (150, 30), (1130, 110), (35, 25, 40), cv2.FILLED)
    cv2.rectangle(overlay, (150, 30), (1130, 110), (150, 70, 180), 2)
    
    # Blinking terminal cursor
    cursor = "|" if int(time.time() * 2.5) % 2 == 0 else ""
    display_text = text + cursor
    
    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale = 1.1
    thickness = 2
    
    # Prevent text overflow (truncate from left to keep latest typing visible)
    while len(display_text) > 0:
        size = cv2.getTextSize(display_text, font, font_scale, thickness)[0]
        if size[0] < (1130 - 150 - 40): # 40px margin
            break
        display_text = display_text[1:]
        
    # Render typing text
    text_y = 30 + (80 + 20) // 2
    cv2.putText(overlay, display_text, (175, text_y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
    
    # Render Caps Lock overlay badge
    badge_x = 1150
    badge_y = 45
    badge_w = 110
    badge_h = 50
    badge_bg = (100, 30, 120) if isCaps else (50, 50, 50)
    badge_border = (200, 80, 220) if isCaps else (100, 100, 100)
    
    cv2.rectangle(overlay, (badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h), badge_bg, cv2.FILLED)
    cv2.rectangle(overlay, (badge_x, badge_y), (badge_x + badge_w, badge_y + badge_h), badge_border, 1)
    
    badge_text = "CAPS ON" if isCaps else "caps off"
    badge_font_scale = 0.5
    badge_text_size = cv2.getTextSize(badge_text, font, badge_font_scale, 1)[0]
    badge_text_x = badge_x + (badge_w - badge_text_size[0]) // 2
    badge_text_y = badge_y + (badge_h + badge_text_size[1]) // 2
    cv2.putText(overlay, badge_text, (badge_text_x, badge_text_y), font, badge_font_scale, (255, 255, 255), 1, cv2.LINE_AA)
    
    alpha = 0.8
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
    
    # Detect hand
    # Note: Modern cvzone HandDetector findHands returns (hands, img)
    result = detector.findHands(img, draw=True)
    
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
    if active_button and lmList:
        # lmList[8] (index tip) and lmList[12] (middle tip)
        idx_x, idx_y = lmList[8][0], lmList[8][1]
        mid_x, mid_y = lmList[12][0], lmList[12][1]
        
        # Calculate Euclidean distance
        distance = np.hypot(idx_x - mid_x, idx_y - mid_y)
        
        # Draw interaction indicator lines
        color = (100, 255, 100) if distance < 35 else (0, 165, 255) # Green when close to clicking, Orange when far
        cv2.line(img, (idx_x, idx_y), (mid_x, mid_y), color, 3)
        cv2.circle(img, (idx_x, idx_y), 7, color, cv2.FILLED)
        cv2.circle(img, (mid_x, mid_y), 7, color, cv2.FILLED)
        
        # Trigger typing logic on click gesture (< 35px)
        current_time = time.time()
        if distance < 35:
            if current_time - last_click_time > click_cooldown:
                clicked_key = active_button
                clicked_key_timer = 6 # Render green click state for 6 frames
                last_click_time = current_time
                
                # Execute keyboard inputs and feed to active OS app
                key_text = active_button.text
                if key_text == "Space":
                    keyboard.type(" ")
                    finalText += " "
                elif key_text == "Backspace":
                    keyboard.press(Key.backspace)
                    keyboard.release(Key.backspace)
                    if len(finalText) > 0:
                        finalText = finalText[:-1]
                elif key_text == "Caps":
                    isCaps = not isCaps
                elif key_text == "Clear":
                    finalText = ""
                elif key_text == "Enter":
                    keyboard.press(Key.enter)
                    keyboard.release(Key.enter)
                    finalText += "\n"
                else:
                    # Append letter key (upper or lowercase)
                    char = key_text.upper() if isCaps else key_text.lower()
                    keyboard.type(char)
                    finalText += char

    # Manage clicked highlight timer
    if clicked_key_timer > 0:
        clicked_key_timer -= 1
    else:
        clicked_key = None
        
    # Render layout and textbox overlay
    img = drawAll(img, buttonList, active_button, clicked_key, isCaps)
    img = drawTextBox(img, finalText, isCaps)
    
    cv2.imshow("Premium Virtual Keyboard", img)
    
    # Press 'q' on hardware keyboard to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("Session ended.")
