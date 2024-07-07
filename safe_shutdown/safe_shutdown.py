import Jetson.GPIO as GPIO
import time
import os


print("-----------------------------------------")
print("      Starting  SafeShutdown Process")
print("-----------------------------------------")

pin = 23

GPIO.setmode(GPIO.BOARD)
GPIO.setup(pin, GPIO.IN)

time.sleep(60)
try:
   while True:
      if GPIO.input(pin) == True:
         print("[!] safe shutdown button pressed...")
         os.system("sudo shutdown now")
         time.sleep(1)
except KeyboardInterrupt:
   GPIO.cleanup()
