import RPi.GPIO as GPIO
import os
from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
import time
from datetime import datetime, timedelta

reset = True
factory = PiGPIOFactory()
channel = 17
servoChannel = 12
GPIO.setmode(GPIO.BCM) #This preps the GPIO pin mode to BCM (Broadcom) so that I'm able to refer to pins by their number instead of names
GPIO.setup(channel, GPIO.IN) #This sets up pin 17 as an input pin from the piezo-vibration sensor
servo = Servo(servoChannel, pin_factory=factory) #this sets up the servo channel from a specially made library to work with servos (prevents software related jitters)

#SETUP VARS
tap_profile = []
setup_time_elapsed = 0
setup_complete = False
#CALLBACK VARS (needs to be global)
num_knocks = 0
currTime = 0
pattern_idx = 0
still_matching = False
pattern_matched = False

#This callback is what is called automatically by the pi
def callback(channel):
	global num_knocks, tap_profile, pattern_idx, still_matching, currTime, pattern_matched, tap_profile, setup_time_elapsed, setup_complete
	if GPIO.input(channel): #Is true when a knock is detected
		print(datetime.now().strftime("%S.%f"), "Knock")
		if not setup_complete: #This appends knocks with the timestamp of the knock to the tap_profile before it gets sent to processing via getDeltaSeconds()
			tap_profile.append(datetime.now())
			num_knocks = 0
		else:
			if num_knocks == 0: #for the first knock, register the current time
				print("\n\nStart")
				currTime = datetime.now()
			elif pattern_idx < len(tap_profile): #pattern_idx progresses as we keeping knocking in a way that matches the pattern registered
				newTime = datetime.now()
				if withinMargin((datetime.now() - currTime).total_seconds(), float(tap_profile[pattern_idx])): #checks to see if the time of the knock is milliseconds close to the actual knock time.
					currTime = newTime #Ensures that the current time is relative to the latest knock
					still_matching = True #if it's within margin then we're still matching otherwise it will stop and say incorrect mid match
				else:
					print("incorrect mid match")
					#restart
					num_knocks = 0
					pattern_idx = 0
					still_matching = False
				pattern_idx += 1
				
			if pattern_idx == len(tap_profile): #if we matched all knocks in the tap profile
				if still_matching: #if still matching was never changed to false from the else clause on line 44 then the mattern is matched
					pattern_matched = True
					print("Pattern Matched")
					print("Unlocking...")
					unlock() #unlocks the lock
					#reset vars for demo purposes so I can re-register another knock pattern for presentation
					tap_profile = []
					setup_time_elapsed = 0
					setup_complete = False
					currTime = 0.0
					pattern_idx = 0
					still_matching = False
					pattern_matched = False
					time.sleep(2) #time before relocking
				else: #if last knock was mismatched then it runs incorrect whole match
					print("incorrect whole match")
					#reset vars for demo purposes so I can re-register another knock pattern for presentation
					tap_profile = []
					setup_time_elapsed = 0
					setup_complete = False
					currTime = 0.0
					pattern_idx = 0
					still_matching = False
					pattern_matched = False
					time.sleep(2) #time before relocking
			num_knocks += 1 #Every time a knock is detected we increment this, it's used to keep track of the first knock hence why It's different from pattern_idx

GPIO.add_event_detect(channel, GPIO.BOTH, bouncetime=200) #reads IO from sensor pin with a bouncetime of 200ms, which allows me to control IO sensitivity programatically.
GPIO.add_event_callback(channel, callback) #this just makes it so that when input is received from sensor pin, it calls the callback function above.

def unlock(): #turns the servo from 0-90 degrees
    servo.max()
    time.sleep(1)
    servo.value = None;

def lock(): #turns the servo from 90-0 degrees
    servo.min()

#this function is self explanatory, it takes a time t, and another time otherTime, and sees if they are within a custom or default margin of each other
def withinMargin(t,otherTime,margin=0.15):
	pos_range = otherTime + margin
	neg_range = abs(otherTime - margin)
	if  t <= pos_range and t >= neg_range:
		return True
	else:
		print("Outside margin", f"{neg_range} <= {t} <= {pos_range}")
		return False

def getDeltaSeconds(): #This measures the time of the previous knock
	global tap_profile
	refined_profile = []
	for i in range(len(tap_profile)):
		if i != 0: #Prevents this function from doing its job for the first knock because there were no previous knocks at that moment
			#Saves the unprocessed time stamps of each knock and puts them in relation to each other by taking the time difference between each knock.
			refined_profile.append((tap_profile[i]-tap_profile[i-1]).total_seconds())
	print("Profile Complete", refined_profile)
	tap_profile = refined_profile #sets the tap profile to now be a knock pattern saved as a function (or mapping) of time.
		

try:
    os.system('sudo pigpiod') #Necessary for GPIOFactory so I don't have to enter this in the terminal everytime I want to run the program.
	#GENERAL ALGORITHM IN THIS LOOP
    while True:
        if setup_time_elapsed == 0: #Runs at the start of the program to let the user know that it's setup time.
            print("Setup Time")
            lock() #Turns the servo into lock mode in case it was unlocked from a previous run.
        if setup_time_elapsed < 10: #Allows the user 10 seconds to calibrate/register their new knockj pattern.
            setup_time_elapsed += 1
            print(setup_time_elapsed)
        if not setup_complete and not setup_time_elapsed < 10: #This occurs after the setup time is complete is complete
            setup_complete = True
            print("Tap Profile Size:",len(tap_profile))
            getDeltaSeconds() #This gets the difference in time from the previous knock to the current knock
        time.sleep(1) #Makes the program sleep for 1 second, which is essential for the setup timer.
except KeyboardInterrupt:
	pass #this is just so when I stop the program manually I don't see a giant error.
