#! /usr/bin/env python
# -*- encoding: UTF-8 -*-

import qi
import argparse
import sys
import time

def main(session, x, y, z):
    """
    This example uses the ALMotion service to make Pepper move forward with adjustable linear velocity.
    """
    # Get the ALMotion service.
    #autonomous_life = session.service("ALAutonomousLifeProxy")
    #autonomous_life.setState("disabled")
    motion = session.service("ALMotion")
    
    # Wake up robot
    #motion.wakeUp()

    # Set the linear velocity for Pepper to move forward
    linear_velocity = 0.5  # Adjust this value to control the speed

    # Set the angular velocity (for turning)
    angular_velocity = 0.0  # You can adjust this value if needed

    # Make Pepper move forward with the specified velocity
    motion.moveToward(linear_velocity, 0.0, angular_velocity)

    # Let Pepper move forward for a few seconds (adjust as needed)
    time.sleep(5)

    # Stop Pepper's movement
    motion.stopMove()

    # Put Pepper in a resting posture
    #motion.rest()


def move(x, y, z, ip="10.1.32.68", port=9559):
    """
    Connects to Pepper and calls main() to move.
    """
    session = qi.Session()
    try:
        session.connect(f"tcp://{ip}:{port}")
    except RuntimeError:
        print(f"Can't connect to Naoqi at IP \"{ip}\" on port {port}.")
        sys.exit(1)
    
    # Call main with session and coordinates
    main(session, x, y, z)


# Only runs when executed directly
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="10.1.32.68",
                        help="Robot IP address. On robot or Local Naoqi: use '10.1.32.68'")
    parser.add_argument("--port", type=int, default=9559,
                        help="Naoqi port number")
    
    x = 0.0
    y = 0.0
    z = 0.0 

    args = parser.parse_args()
    move(x, y, z, ip=args.ip, port=args.port)