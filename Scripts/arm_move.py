from naoqi import ALProxy
import time

PEPPER_IP = "10.1.32.138"
PORT = 9559

motion = ALProxy("ALMotion", PEPPER_IP, PORT)
tts = ALProxy("ALTextToSpeech", PEPPER_IP, PORT)
asr = ALProxy("ALSpeechRecognition", PEPPER_IP, PORT)
memory = ALProxy("ALMemory", PEPPER_IP, PORT)

motion.wakeUp()

def move_left_arm_with_fist(
    roll_up=1.0,
    roll_down=-1.0,
    pitch_inward=0.5,
    speed=0.1,
    pause=1.0
):
    roll_joint = "LShoulderRoll"
    pitch_joint = "LShoulderPitch"
    hand_joint = "LHand"

    # Fist

    motion.setAngles(hand_joint, 0.0, speed)
    time.sleep(pause)

    # Arm up
    motion.setAngles(roll_joint, roll_up, speed)
    time.sleep(pause)

    # Arm inward
    motion.setAngles(pitch_joint, pitch_inward, speed)
    time.sleep(pause)

    # Ask question
    tts.say("Is this the product you are looking for?")

    time.sleep(0.5)

 
    # Begin speech recognition
    asr.pause(True)
    asr.setLanguage("English")
    vocabulary = ["yes", "no"]
    asr.setVocabulary(vocabulary, False)
    asr.pause(False)
    asr.subscribe("ProductCheck")

    # Listen for 4 seconds
    time_limit = time.time() + 4
    user_answer = None

    while time.time() < time_limit:
        data = memory.getData("WordRecognized")
        if isinstance(data, list) and len(data) > 1:
            word = data[0]
            confidence = data[1]
            if confidence > 0.4:  # basic confidence filter
                user_answer = word
                break

        time.sleep(0.1)

    # Stop recognition
    asr.unsubscribe("ProductCheck")

    # Reaction
    if user_answer == "yes":
        tts.say("Great.")
    elif user_answer == "no":
        tts.say("What else are you looking for?")
    else:
        tts.say("I did not quite hear that.")

    # Arm down
    motion.setAngles(roll_joint, roll_down, speed)
    time.sleep(pause)

    # Return to neutral
    motion.setAngles([roll_joint, pitch_joint, hand_joint],
                     [0.0, 1.5, 1.0], speed)

    time.sleep(pause)

# Run
move_left_arm_with_fist()