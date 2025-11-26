#! /usr/bin/env python
# -*- encoding: UTF-8 -*-

"""Example: Use explore method."""

import qi
import argparse
import sys
#import naoqi 
import time


def main(session):
    """
    This example uses the explore method.
    """
    #autonomous_life = session.service("ALAutonomousLifeProxy")
    #autonomous_life.setState("disabled")
    #motion = session.service("ALMotion")
    #motion.wakeUp()

    tts = session.service("ALTextToSpeech")
    tts.setParameter("speed",83)
    tts.setVolume(1.0)
    # for
    tts.say("Hello, my name is pepper")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="10.1.32.68",
                        help="Robot IP address. On robot or Local Naoqi: use '10.1.32.68'.")
    parser.add_argument("--port", type=int, default=9559,
                        help="Naoqi port number")

    args = parser.parse_args()

    # Create and start the Naoqi session
    session = qi.Session()
    try:
        session.connect("tcp://" + args.ip + ":" + str(args.port))
    except RuntimeError:
        print("Can't connect to Naoqi at ip \"" + args.ip + "\" on port " + str(args.port) + ".\n"
              "Please check your script arguments. Run with -h option for help.")
        sys.exit(1)
    main(session)
