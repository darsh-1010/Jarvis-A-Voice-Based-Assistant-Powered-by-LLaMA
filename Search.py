import wikipedia as wi
import speech_recognition as sr 
import pyttsx3
import webbrowser
import pywhatkit

listener = sr.Recognizer() 

def Speak(text):
    rate= 100
    engine = pyttsx3.init() 
    voices = engine.getProperty('voices') 
    engine.setProperty('voice', voices[0].id)
    engine.setProperty('rate', rate+50)
    engine.say(text)
    engine.runAndWait()

def searchGoogle(command):
    if "google" in command:
        command=command.replace("jarvis","")
        command=command.replace("search google","")
        command=command.replace("google","")
        Speak("This What I found On Google")
        try:
           webbrowser.open("https://www.google.com/search?client=firefox-b-d&q="+command)
           ''' pywhatkit.search(command)
            result = wi.summary(command,1)
            Speak(result)'''
        except:
            Speak("Could Not Speak")

def searchYoutube(command):
    if "youtube" in command:
        command=command.replace("jarvis","")
        command=command.replace("search youtube","")
        command=command.replace("youtube","")
        Speak("This What I found On youtube")
        web="https://www.youtube.com/results?search_query="+command
        webbrowser.open(web)
        pywhatkit.playonyt(command)
        Speak("Done Sir")




