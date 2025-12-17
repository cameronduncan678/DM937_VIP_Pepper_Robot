import qi
import argparse
import sys

def say_hi(session):
    tts = session.service("ALTextToSpeech")  

    tts.setLanguage("English") #setting language

    tts.say("Hi")