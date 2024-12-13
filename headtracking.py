import cv2
import mediapipe as mp
import math
import numpy as np
import tkinter as tk
from tkinter import ttk, Text, Label
from PIL import Image, ImageTk
import pyvjoy
import json

print(mp.__file__)

# Initialize MediaPipe Face Mesh with CPU processing
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# Initialize drawing specifications
mp_drawing = mp.solutions.drawing_utils
drawing_spec = mp_drawing.DrawingSpec(thickness=1, circle_radius=1)

# Function to list available video capture devices
def list_video_devices():
    index = 0
    arr = []
    while True:
        cap = cv2.VideoCapture(index)
        if not cap.read()[0]:
            break
        else:
            arr.append(f"Device {index}")
        cap.release()
        index += 1
    return arr

# Initialize webcam
cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

def calculate_angle(landmark1, landmark2):
    x1, y1, z1 = landmark1.x, landmark1.y, landmark1.z
    x2, y2, z2 = landmark2.x, landmark2.y, landmark2.z
    angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
    return angle

def smooth_angle(angle, prev_angles, smoothing_factor=0.9):
    if prev_angles:
        smoothed_angle = smoothing_factor * prev_angles[-1] + (1 - smoothing_factor) * angle
    else:
        smoothed_angle = angle
    prev_angles.append(smoothed_angle)
    if len(prev_angles) > 10:
        prev_angles.pop(0)
    return smoothed_angle

base_angle = 0
prev_angles = []

# Remove the save_settings method
class FaceTrackingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Head Tracking")
        self.root.geometry("1024x768")
        self.root.configure(bg="gray")

        self.video_label = ttk.Label(root, background="black")
        self.video_label.grid(row=0, column=2, rowspan=10, sticky="nsew", padx=10, pady=10)

        self.direction_label = ttk.Label(root, text="Direction: Centered", background="gray", font=("Helvetica", 16))
        self.direction_label.grid(row=0, column=0, padx=10, pady=10)

        self.angle_slider = ttk.Scale(root, from_=-45, to=45, orient="horizontal", length=300)
        self.angle_slider.grid(row=1, column=0, padx=10, pady=10)

        self.reset_button = ttk.Button(root, text="Reset Center", command=self.reset_center)
        self.reset_button.grid(row=2, column=0, padx=10, pady=10)

        # Remove the save button
        self.text_label = Label(root, text="Enter video device number:")
        self.text_label.grid(row=3, column=0, padx=10, pady=10)

        self.device_entry = ttk.Entry(root)
        self.device_entry.grid(row=4, column=0, padx=10, pady=10)

        self.apply_button = ttk.Button(root, text="Apply Device", command=self.change_device)
        self.apply_button.grid(row=5, column=0, padx=10, pady=10)

        self.width_entry = ttk.Entry(root)
        self.width_entry.grid(row=6, column=0, padx=10, pady=10)
        self.width_entry.insert(0, "1920")

        self.height_entry = ttk.Entry(root)
        self.height_entry.grid(row=6, column=1, padx=10, pady=10)
        self.height_entry.insert(0, "1080")

        self.resolution_button = ttk.Button(root, text="Apply Resolution", command=self.change_resolution)
        self.resolution_button.grid(row=7, column=0, columnspan=2, padx=10, pady=10)

        self.joystick = pyvjoy.VJoyDevice(1)  # Initialize joystick
        self.current_position = 0x4000  # Initialize current joystick position to center

        self.load_settings()
        self.update_frame()

    # Remove the save_settings method

    def change_device(self):
        global cap
        device_index = int(self.device_entry.get())
        cap.release()
        cap = cv2.VideoCapture(device_index)
        self.change_resolution()

    def change_resolution(self):
        global cap
        width = int(self.width_entry.get())
        height = int(self.height_entry.get())
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def reset_center(self):
        global base_angle
        ret, frame = cap.read()
        if ret:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_results = face_mesh.process(rgb_frame)
            if face_results.multi_face_landmarks:
                for face_landmarks in face_results.multi_face_landmarks:
                    nose_tip = face_landmarks.landmark[1]
                    face_center = face_landmarks.landmark[168]
                    base_angle = calculate_angle(nose_tip, face_center)

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                self.current_position = settings.get("current_position", 0x4000)
                device_index = settings.get("device_index", 0)
                self.device_entry.insert(0, str(device_index))
                self.width_entry.insert(0, str(settings.get("width", 1920)))
                self.height_entry.insert(0, str(settings.get("height", 1080)))
                self.change_device()
        except FileNotFoundError:
            pass

    def update_frame(self):
        ret, frame = cap.read()
        if ret:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_results = face_mesh.process(rgb_frame)

            if face_results.multi_face_landmarks:
                for face_landmarks in face_results.multi_face_landmarks:
                    mp_drawing.draw_landmarks(
                        frame, face_landmarks, mp_face_mesh.FACEMESH_TESSELATION,
                        mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=1),
                        mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=1, circle_radius=1)
                    )
                    nose_tip = face_landmarks.landmark[1]
                    face_center = face_landmarks.landmark[168]
                    angle = calculate_angle(nose_tip, face_center) - base_angle
                    smoothed_angle = smooth_angle(angle, prev_angles)

                    if abs(smoothed_angle) < 3:
                        direction = "Centered"
                        target_position = 0x4000  # Center joystick
                    elif smoothed_angle > 0:
                        direction = "Looking Left"
                        target_position = 0x8000  # Move joystick left
                    else:
                        direction = "Looking Right"
                        target_position = 0x0000  # Move joystick right

                    # Interpolate joystick position
                    self.current_position = int(self.current_position + 0.1 * (target_position - self.current_position))
                    self.joystick.set_axis(pyvjoy.HID_USAGE_X, self.current_position)

                    self.direction_label.config(text=f"Direction: {direction}")
                    self.angle_slider.set(smoothed_angle)

                    cv2.putText(frame, direction, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

            # Resize frame to fit the video_label while maintaining 16:9 aspect ratio
            label_width = self.video_label.winfo_width()
            label_height = int(label_width * 9 / 16)
            if label_width > 0 and label_height > 0:
                frame = cv2.resize(frame, (label_width, label_height))

            img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            imgtk = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

        self.root.after(10, self.update_frame)

if __name__ == "__main__":
    root = tk.Tk()
    app = FaceTrackingApp(root)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)
    root.grid_columnconfigure(2, weight=1)
    root.grid_rowconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)
    root.mainloop()
    cap.release()
    cv2.destroyAllWindows()