import qi
import argparse
import sys

def say_product_confirm(session):
    tts = session.service("ALTextToSpeech")  

    tts.setLanguage("English") #setting language

    tts.say("Is this the product you are looking for?")