import qi
import argparse
import sys
import msvcrt
import time

class PepperController:
    def __init__(self, session):
        self.motion_service = session.service("ALMotion")
        self.posture_service = session.service("ALRobotPosture")
        self.is_running = True
        self.collision_protection_enabled = False

    def set_velocity(self, linear_velocity, angular_velocity):
        self.motion_service.move(linear_velocity, 0, angular_velocity)

    def stop(self):
        self.motion_service.stopMove()

    def exit_program(self):
        self.is_running = False
        self.stop()
        sys.exit(0)

    def enable_external_collision_protection(self):
        # Enable the disactivation of "Move" external collision protection
        self.motion_service.setOrthogonalSecurityDistance(0.005)
        self.motion_service.setTangentialSecurityDistance(0.005)
        self.motion_service.setExternalCollisionProtectionEnabled("Move", True)
        self.collision_protection_enabled = True
        print("External collision protection enabled.")

    def disable_external_collision_protection(self):
        # Disable the "Move" external collision protection
        self.motion_service.setExternalCollisionProtectionEnabled("Move", False)
        self.collision_protection_enabled = False
        print("External collision protection disabled.")

    def toggle_collision_protection(self):
        # Toggle external collision protection based on the current state
        if self.collision_protection_enabled:
            self.disable_external_collision_protection()
        else:
            self.enable_external_collision_protection()

    def keyboard_control(self):
        print("Press 'W' to move forward, 'A' to turn left, 'D' to turn right, 'S' to stop robot, 'X' backward, 'C' to toggle collision protection, and 'Q' to quit.")
        while self.is_running:
            key = self.get_key()
            if key.lower() == 'w':
                self.set_velocity(0.4, 0)
            elif key.lower() == 'a':
                self.set_velocity(0, 0.4)
            elif key.lower() == 'd':
                self.set_velocity(0, -0.4)
            elif key.lower() == 'q':
                self.exit_program()
            elif key.lower() == 's':
                self.set_velocity(0, 0)
            elif key.lower() == 'x':
                self.set_velocity(-0.4, 0)
            elif key.lower() == 'c':
                self.toggle_collision_protection()

    def get_key(self):
        while True:
            if msvcrt.kbhit():
                return msvcrt.getch().decode("utf-8")

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

    pepper_controller = PepperController(session)

    try:
        pepper_controller.posture_service.goToPosture("StandInit", 0.5)  # Set the robot to a standing posture
        pepper_controller.enable_external_collision_protection()

        # Your other robot control logic goes here...
        pepper_controller.keyboard_control()
    except KeyboardInterrupt:
        pepper_controller.exit_program()
    finally:
        # Ensure external collision protection is disabled when the program exits
        if pepper_controller.collision_protection_enabled:
            pepper_controller.disable_external_collision_protection()
        session.close()
