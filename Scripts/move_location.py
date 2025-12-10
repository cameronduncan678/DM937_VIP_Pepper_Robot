#! /usr/bin/env python
# -*- encoding: UTF-8 -*-

import qi
import argparse
import sys
import time
import math
from naoqi import ALProxy

def move_location():
    PEPPER_IP = "10.1.32.138"
    PORT = 9559

    motion = ALProxy("ALMotion", PEPPER_IP, PORT)

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
