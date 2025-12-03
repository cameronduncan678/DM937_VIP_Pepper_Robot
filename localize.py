#! /usr/bin/env python
# -*- encoding: UTF-8 -*-

"""Example: Use localization methods"""

import qi
import argparse
import sys

# Connection to the robot.
# Path to previously saved exploration file
def main(session, exploration_file):
    """
    This example uses localization methods.
    """
    # Get the services ALNavigation and ALMotion.
    # Service for autonomous navigation, localization, and mapping.
    navigation_service = session.service("ALNavigation")

    # Service for controlling robot posture and movements.
    motion_service = session.service("ALMotion")

    # Wake up robot
    # Powers on motors and sets the robot into a standing posture, ready for navigation.
    motion_service.wakeUp()

    # Load a previously saved exploration
    navigation_service.loadExploration("2025-11-05T140157.816Z.explo")

    # Relocalize the robot and start the localization process.
    guess = [0., 0.] # assuming the robot is not far from the place where
                     # he started the loaded exploration.

    # Gives the robot an initial guess of its position on the loaded map.
    navigation_service.relocalizeInMap(guess) 

    # Starts continuous localization so the robot now tracks its position on the map in real time.
    navigation_service.startLocalization()

    # Navigate to another place in the map
    # from helper import search_product_by_name
    # coords = search_product_by_name("Bread")
    # navigation_service.navigateToInMap(coords)

    navigation_service.navigateToInMap([-2., 0., 0.])

    # Check where the robot arrived
    # Returns the robot’s estimated position and extracts the x-coordinate
    print ("I reached: " + str(navigation_service.getRobotPositionInMap()[0]))

    # Stops the localization process to save resources after navigation is complete.
    navigation_service.stopLocalization()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="10.1.32.138",
                        help="Robot IP address. On robot or Local Naoqi: use '10.1.32.138'.")
    parser.add_argument("--port", type=int, default=9559,
                        help="Naoqi port number")
    parser.add_argument("--explo", type=str, help="Path to .explo file.")

    args = parser.parse_args()

    # Creates a NAOqi session and tries to connect to the robot via TCP.
    # If connection fails, exits the script with an error message.
    session = qi.Session()
    try:
        session.connect("tcp://" + args.ip + ":" + str(args.port))
    except RuntimeError:
        print ("Can't connect to Naoqi at ip \"" + args.ip + "\" on port " + str(args.port) +".\n"
               "Please check your script arguments. Run with -h option for help.")
        sys.exit(1)

    # Calls the main function with the active session and the path to the exploration file.
    main(session, args.explo)