#! /usr/bin/env python
# -*- encoding: UTF-8 -*-

import qi
import argparse
import sys
import time
import math

def main(session):
    motion = session.service("ALMotion")

    # Move forward in safe 2m increments
    total_distance = 3.0
    step = 1.0
    steps = int(total_distance / step)

    for _ in range(steps):
        motion.moveTo(step, 0.0, 0.0)

    # Remaining distance if not multiple of step
    remainder = total_distance % step
    if remainder > 0:
        motion.moveTo(remainder, 0.0, 0.0)

    # Turn left 90 degrees
    motion.moveTo(0.0, 0.0, math.radians(90))

    motion.stopMove()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="10.1.32.138",
                        help="Robot IP address.")
    parser.add_argument("--port", type=int, default=9559,
                        help="Naoqi port number")

    args = parser.parse_args()

    session = qi.Session()
    try:
        session.connect("tcp://" + args.ip + ":" + str(args.port))
    except RuntimeError:
        print("Can't connect to Naoqi at IP \"" + args.ip +
              "\" on port " + str(args.port))
        sys.exit(1)

    main(session)
