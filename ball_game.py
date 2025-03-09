import cv2
import mediapipe as mp
import random
import pygame
import serial
import os
print(os.getcwd())

mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

counter = 1

pygame.mixer.init()
touch_sound = pygame.mixer.Sound('good.mp3')  # Replace with the path to your sound file
background_sound = pygame.mixer.Sound('bgm.mp3')  # Background sound file

background_sound.play(-1)  # -1 makes it loop indefinitely

led_state = "OFF"  # Initial LED state


ser = serial.Serial(
    'COM6', 115200
)  # Replace '/dev/ttyACM0' with the actual serial port of your Wio Terminal

def play_touch_sound():
    touch_sound.play()


def draw_circle(image, center, radius, color, thickness=2):
    cv2.circle(image, center, radius, color, thickness)


def track_index_finger_tip(image, results, image_width, image_height):
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            index_finger_tip = hand_landmarks.landmark[
                mp_hands.HandLandmark.INDEX_FINGER_TIP]
            tip_x, tip_y = int(index_finger_tip.x * image_width), int(
                index_finger_tip.y * image_height)
            return tip_x, tip_y
    return None


def is_tip_inside_circle(tip_coordinates, circle_center, circle_radius):
    distance = ((tip_coordinates[0] - circle_center[0])**2 +
                (tip_coordinates[1] - circle_center[1])*2)*0.5
    return distance <= circle_radius


def generate_random_circle(image_width, image_height):
    if(number_of_touches == 0):
        circle_radius = 50
    elif(number_of_touches == 1): 
        #circle_radius = int(random.randint(20, 50) / counter)
        circle_radius = 35
    else: 
        circle_radius = 20  

    circle_center = (random.randint(circle_radius,
                                    image_width - circle_radius),
                     random.randint(circle_radius,
                                    image_height - circle_radius))
    circle_color = (255, 255,0)
    return circle_center, circle_radius, circle_color


# For webcam input:
cap = cv2.VideoCapture(0)
with mp_hands.Hands(min_detection_confidence=0.5,
                    min_tracking_confidence=0.5) as hands:
    number_of_touches = 0
    circle_center, circle_radius, circle_color = generate_random_circle(640, 480)
    ser.write(b'OFF\n')  # Send the "ON" command to the Wio Terminal

    # Initialize velocities for circle movement
    velocity_x = 5
    velocity_y = 3

    game_won = False  # Flag to check if the game is won

    while cap.isOpened():
        success, image = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            continue

        # Process the image with Mediapipe
        image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
        image.flags.writeable = False  # Mediapipe processes the image as read-only
        results = hands.process(image)

        # Make the image writeable again for OpenCV
        image.flags.writeable = True

        # If the game is won, display the winning message
        if game_won:
            font = cv2.FONT_HERSHEY_SIMPLEX
            text = "You Win!"
            text_size = cv2.getTextSize(text, font, 2, 3)[0]
            text_x = (image.shape[1] - text_size[0]) // 2
            text_y = (image.shape[0] + text_size[1]) // 2
            cv2.putText(image, text, (text_x, text_y), font, 2, (0, 255, 0), 3)
            cv2.imshow('MediaPipe Hands with Moving Circle', image)

            if cv2.waitKey(5) & 0xFF == 27:  # Press 'Esc' to exit
                ser.write(b'RESET\n')  # Send the "ON" command to the Wio Terminal
                break
            continue

        # Draw the moving circle
        draw_circle(image, center=circle_center, radius=circle_radius, color=circle_color, thickness=-1)

        # Track the position of the tip of the right index finger
        tip_coordinates = track_index_finger_tip(image, results, 640, 480)

        if tip_coordinates is not None:
            # Check if the tip is inside the circle
            inside_circle = is_tip_inside_circle(tip_coordinates, circle_center, circle_radius)
            if inside_circle:
                ser.write(b'ON\n')  # Send the "ON" command to the Wio Terminal
                led_state = "ON"  # Update LED state
                number_of_touches += 1
                counter += 0.6
                print(f"Circle touched! Total touches: {number_of_touches}")
                if(number_of_touches == 3):
                    background_sound.stop()
                    play_touch_sound()  # Play sound effect


                if number_of_touches == 3:
                    game_won = True  # Set the game-won flag
                    continue

                # Generate a new circle
                circle_center, circle_radius, circle_color = generate_random_circle(640, 480)

        # Update circle position for movement
        circle_center = (circle_center[0] + velocity_x, circle_center[1] + velocity_y)

        # Check and update direction when the circle hits the image borders
        if circle_center[0] - circle_radius <= 0 or circle_center[0] + circle_radius >= 640:
            velocity_x = -velocity_x
        if circle_center[1] - circle_radius <= 0 or circle_center[1] + circle_radius >= 480:
            velocity_y = -velocity_y

        # Convert image back to BGR for display
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # Draw landmarks if available
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        # Show the image
        cv2.imshow('MediaPipe Hands with Moving Circle', image)

        if cv2.waitKey(5) & 0xFF == 27:  # Press 'Esc' to exit
            ser.write(b'RESET\n')  # Send the "ON" command to the Wio Terminal
            break

cap.release()
cv2.destroyAllWindows()

pygame.mixer.quit()