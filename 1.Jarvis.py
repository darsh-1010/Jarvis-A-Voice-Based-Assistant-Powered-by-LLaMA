import speech_recognition as sr 
import pyttsx3
import time
import random
import datetime
import webbrowser
import subprocess
import cv2  # OpenCV for camera functionality
import pyautogui  # For taking screenshots
from Greetings import greeting # from user defiend code to greet user 
from Search import *
import requests
from bs4 import BeautifulSoup
import threading
import os # For multiple functionality realted to the OS such as opening an application
import pywhatkit
from langchain_ollama.llms import OllamaLLM #To acces ai models that act as chatgpt
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.llms import Ollama
import speedtest  # Importing speedtest library

recognizer = sr.Recognizer()
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Speed of speech
engine.setProperty('volume', 1.0)  # Volume level (0.0 to 1.0)

ollama_llm = Ollama(model="gemma2:2b")
tts_lock = threading.Lock()
conversation_history = []

# OpenCV camera variables
camera = None
camera_opened = False  # To track if the camera is open

def generate_and_speak(text):
    if text:
        # Append the user's query to the conversation history
        conversation_history.append(f"User: {text}")

        # Prepare the full context with conversation history
        context = "\n".join(conversation_history)

        # Use LangChain to create a prompt with conversation history
        response = ollama_llm.invoke(
            chain.invoke({
                "context": context,
                "question": text
            })
        )

        
        # Append the assistant's response to the conversation history
        conversation_history.append(f"Assistant: {response}")

        try:
            # Use the lock to ensure thread-safe access to the TTS engine
            with tts_lock:
                engine.say(response)
                engine.runAndWait()
            return "Speaking: " + response
        except Exception as e:
            return f"Error in text-to-speech: {e}"
    return "No text to process."

# Define the prompt template for LangChain
template = """
Answer the following question in summarized form

Here's the conversation history: {context}

Question: {question}

Answer:
"""

# Initialize the LLaMA 3 model using LangChain's Ollama integration
model = OllamaLLM(model='gemma2:2b')
prompts = ChatPromptTemplate.from_template(template)
chain = prompts | model


# variables
listener = sr.Recognizer() 
strTime = datetime.datetime.now().strftime("%H:%M")

# Functions for Functionalities

def wake_word():
    listener = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening")
        voice = listener.listen(source)
        try:
            command = listener.recognize_google(voice)
            command = command.lower()
            if 'jarvis' in command:
                greeting()
                while 1:
                    if not Listen():
                        break
            else:
                wake_word()
        except:
            wake_word()

def sleep():
     listener = sr.Recognizer()
     with sr.Microphone() as source:
         print("Listening")
         voice = listener.listen(source)
         try:
            command = listener.recognize_google(voice)
            command = command.lower()
            if 'jarvis' in command:
                Speak("Hi, How Can I Help You Today?")
                Listen()
            else:
                sleep()
         except:
            sleep()

def Speak(text):
    rate = 100
    engine = pyttsx3.init() 
    voices = engine.getProperty('voices') 
    engine.setProperty('voice', voices[0].id)
    engine.setProperty('rate', rate + 50)
    engine.say(text)
    engine.runAndWait()

# Function to open camera
def open_camera():
    global camera, camera_opened
    camera = cv2.VideoCapture(0)
    camera_opened = True
    Speak("Camera is now open.")
    while camera_opened:
        ret, frame = camera.read()
        if ret:
            cv2.imshow("Camera", frame)
            key = cv2.waitKey(1) & 0xFF
            # Close the camera if 'q' is pressed or 'Esc' key is pressed
            if key == ord('q') or key == 27:
                close_camera()
                break
        ListenForCameraCommands()
# Function to open Spotify to search for a song
def play_song(song_name):
    search_url = f"https://open.spotify.com/search/{song_name}"
    Speak(f"Opening Spotify to search for {song_name}")
    webbrowser.open(search_url)
    conversation_history.append(f"Assistant: Opened Spotify to search for {song_name}")

def close_camera():
    global camera, camera_opened
    if camera:
        camera.release()
        cv2.destroyAllWindows()
        camera_opened = False
        Speak("Camera is now closed.")

# Function to click photo with 5-second timer
def click_photo():
    global camera
    camera = cv2.VideoCapture(0)
    Speak("Opening camera to take a photo in 5 seconds.")
    countdown(5)  # 5-second countdown
    ret, frame = camera.read()
    if ret:
        cv2.imwrite("photo.jpg", frame)
        Speak("Photo has been clicked and saved.")
    camera.release()
    cv2.destroyAllWindows()

# Countdown function for audio feedback
def countdown(seconds):
    for i in range(seconds, 0, -1):
        Speak(f"{i}")
        time.sleep(1)

#Function for Sleep
def sleep():
     listener = sr.Recognizer()
     with sr.Microphone() as source:
         print("Listening")
         voice = listener.listen(source)
         try:
            command = listener.recognize_google(voice)
            command = command.lower()
            if 'jarvis' in command:
                Speak("Hello sir, How Can I Help You Today")
                Listen()
            else:
                sleep()
         except:
            sleep()

# Function to take screenshot with a 3-second countdown
def take_screenshot():
    Speak("Taking a screenshot in 3 seconds.")
    countdown(3)  # 3-second countdown before taking a screenshot
    screenshot = pyautogui.screenshot()
    screenshot.save("screenshot.png")
    Speak("Screenshot has been taken and saved.")

def ListenForCameraCommands():
    listener = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for camera commands")
        voice = listener.listen(source)
        try:
            command = listener.recognize_google(voice)
            command = command.lower()

            if 'close camera' in command:
                close_camera()
        except:
            pass

# Function to test internet speed
def test_internet_speed():
    st = speedtest.Speedtest()
    Speak("Testing internet speed. Please wait.")
    download_speed = st.download() / (10**6)  # Convert to Mbps
    upload_speed = st.upload() / (10**6)  # Convert to Mbps
    result = f"The download speed is {download_speed:.2f} Mbps and the upload speed is {upload_speed:.2f} Mbps."
    Speak(result)
    conversation_history.append(f"Assistant: {result}")

def Listen():
    listener = sr.Recognizer()
    with sr.Microphone() as source:
        Speak("Listening")
        voice = listener.listen(source)
        try:
            command = listener.recognize_google(voice)
            command = command.lower()

            # Handle various commands, update conversation history accordingly
            if 'how are you' in command:
                Speak("I'm Fine Thank You")
                conversation_history.append("Assistant: I'm Fine Thank You")
            elif 'i am fine' in command:
                Speak("That's Great How Can I Help You Today?")
                conversation_history.append("Assistant: That's Great How Can I Help You Today?")
            elif 'thank you' in command:
                Speak("You are Welcome")
                conversation_history.append("Assistant: You are Welcome")
            elif 'time' in command:
                Speak(f"The Time Is {strTime}")
                conversation_history.append(f"Assistant: The Time Is {strTime}")
            # Open apps in the system
            elif 'open calculator' in command:
                Speak("Opening Calculator")
                subprocess.Popen(r'C:\Windows\System32\calc.exe')
                conversation_history.append("Assistant: Opened Calculator")
            elif 'open notepad' in command: 
                Speak("Opening Notepad")
                subprocess.Popen(r'C:\Windows\System32\notepad.exe')
                conversation_history.append("Assistant: Opened Notepad")
            elif 'open command prompt' in command:
                Speak("Opening CMD")
                subprocess.Popen(r'C:\Windows\System32\cmd.exe')
                conversation_history.append("Assistant: Opened CMD")
            elif 'open source file' in command:
                Speak("Opening Source File")
                subprocess.Popen(r'explorer.exe D:\Laptop\Phoneix')
                conversation_history.append("Assistant: Opened Source File")
            # Access Web Browser
            elif 'open google' in command:
                Speak("Opening Google")
                webbrowser.open_new('https://www.google.com/')
                conversation_history.append("Assistant: Opening Google")
            elif 'open chatgpt' in command:
                Speak("Opening Chat Gpt")
                webbrowser.open_new('https://chatgpt.com/')
                conversation_history.append("Assistant: Opening ChatGpt")
            elif 'open youtube' in command:
                Speak("Opening YouTube")
                webbrowser.open_new('https://www.youtube.com/')
                conversation_history.append("Assistant: Opening YouTube")
            elif 'open my mail' in command:
                Speak("Opening Your Mail")
                webbrowser.open_new('https://mail.google.com/mail/u/1/#inbox')
                conversation_history.append("Assistant: Opened your mail")
            # Camera functionality commands
            elif 'open camera' in command:
                open_camera()
                conversation_history.append("Assistant: Opened the camera")
            elif 'click photo' in command:
                click_photo()
                conversation_history.append("Assistant: Clicked a photo")
            elif 'close camera' in command:
                close_camera()
                conversation_history.append("Assistant: Closed the camera")
            # Screenshot functionality
            elif 'take screenshot' in command:
                take_screenshot()
                conversation_history.append("Assistant: Took a screenshot")
            #Access spotfiy
            elif 'play song ' in command:
                song_name = command.replace('play', '').strip().strip('"')
                play_song(song_name)
            # Internet Speed Test
            elif 'test internet speed' in command:
                test_internet_speed()
            #NEWS Functionality 
            elif "news" in command:
                    from NewsRead import latestnews
                    latestnews()
            #Volume up-Down Functionality
            elif "volume up" in command:
                    from vol import volumeup
                    Speak("Turning volume up,sir")
                    volumeup()
            elif "volume down" in command:
                    from vol import volumedown
                    Speak("Turning volume down, sir")
                    volumedown()
            #Music to lighten the mood
            elif "tired" in command:
                    Speak("Playing your favourite songs, sir")
                    a = (1,2,3) # You can choose any number of songs (I have only choosen 3)
                    b = random.choice(a)
                    if b==1:
                        webbrowser.open("https://www.youtube.com/watch?v=v-icNVDbVLk")
                    if b==2:
                        webbrowser.open("https://www.youtube.com/watch?v=pxCWiYFkvTg")
                    if b==3:
                        webbrowser.open("https://www.youtube.com/watch?v=DCkRJ8BDRQU")
            #Shut Down System
            elif "shutdown the system" in command:
                    Speak("Shutting Down the System")
                    os.system("shutdown /s /t 1")
            # Sleep Functionality 
            elif 'sleep' in command:
                Speak("Going To Sleep")
                sleep()
            # Terminate the Program
            elif 'terminate' in command:
                Speak("Shutting Down")
                conversation_history.append("Assistant: Shutting Down")
                return 0
            else:
                return generate_and_speak(command)
        except Exception as e:
            Speak(f"Sorry, I couldn't understand the command due to {e}")
            conversation_history.append(f"Assistant: Sorry, I couldn't understand the command due to {e}")
    return 1

# Main Function
wake_word()
