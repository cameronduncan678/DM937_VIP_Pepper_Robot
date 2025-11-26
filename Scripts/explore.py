#! /usr/bin/env python
# -*- encoding: UTF-8 -*-

"""Example: Use explore method."""

import qi
import argparse
import sys
#import naoqi 
import time
import numpy
from PIL import Image

def main(session):
    """
    This example uses the explore method.
    """
    # Get the services ALNavigation and ALMotion.
    # ALNavigation handles autonomous movement, exploration, localization, and mapping.
    navigation_service = session.service("ALNavigation") 

    #ALMotion handles joint control, walking, posture, and basic movements.
    motion_service = session.service("ALMotion")

    # Wake up robot
    # Activates the robot’s motors and sets it to a default standing posture, so it’s ready to move.
    motion_service.wakeUp()

    # Explore the enviornment, in a radius of 15 m.
    # Instructs the robot to autonomously explore the environment within the given radius.
    # During exploration, the robot builds an internal map and scans its surroundings.
    radius = 15.0
    navigation_service.explore(radius)

    # Saves the internal map created during exploration to disk, returning the file path.
    path = navigation_service.saveExploration()
    print("Exploration saved at path: \"" + path + "\"")

    # Start localization to navigate in map
    # Activates the robot’s localization system so it knows its position in the previously explored map.
    navigation_service.startLocalization()

    # currently, come back to initial position
    # Commands the robot to move to a specific position and orientation in the map.
    navigation_service.navigateToInMap([0., 0., 0.])

    # Stops the robot’s localization system to save processing resources once navigation is complete.
    navigation_service.stopLocalization()

    # Retrieve and display the map built by the robot
    result_map = navigation_service.getMetricalMap()
    map_width = result_map[1]
    map_height = result_map[2]
    img = numpy.array(result_map[4]).reshape(map_width, map_height)
    
    # converts to grayscale
    img = (100 - img) * 2.55 # from 0..100 to 255..0
    img = numpy.array(img, numpy.uint8)
    # opens image in default image viewer
    Image.frombuffer('L',  (map_width, map_height), img, 'raw', 'L', 0, 1).show()

if __name__ == "__main__":
    #Command-line arguments let you specify the robot’s IP address and port.
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="10.1.32.138",
                        help="Robot IP address. On robot or Local Naoqi: use '10.1.32.138'.")
    parser.add_argument("--port", type=int, default=9559,
                        help="Naoqi port number")

    args = parser.parse_args()

    # Create and start the Naoqi session
    # Creates a connection session to the robot.
    session = qi.Session()
    try:
        # Connects to the robot via TCP.
        session.connect("tcp://" + args.ip + ":" + str(args.port))
    except RuntimeError:
        #If the connection fails, the script exits with an error message.
        print("Can't connect to Naoqi at ip \"" + args.ip + "\" on port " + str(args.port) + ".\n"
              "Please check your script arguments. Run with -h option for help.")
        sys.exit(1)
    #calls main session to start the exploration
    main(session)