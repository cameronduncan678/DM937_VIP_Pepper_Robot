from naoqi import ALProxy
import time

def point_arm():
    
    PEPPER_IP = "10.1.32.138"
    PORT = 9559
    
    motion = ALProxy("ALMotion", PEPPER_IP, PORT)

    motion.wakeUp()
    pitch_joint = "RShoulderPitch"

    count = 1

    while count <= 1000:
        motion.setAngles(pitch_joint, 0.5, 0.1)
        count += 1


