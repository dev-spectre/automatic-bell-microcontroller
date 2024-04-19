from machine import Pin
from utime import sleep

relay = Pin(22, Pin.OUT, value=1)
led = Pin("LED", Pin.OUT)

def switch_on():
    led.on()
    relay.value(0)
    
def switch_off():
    led.off()
    relay.value(1)

def timer(seconds):
    switch_on()
    sleep(seconds)
    switch_off()
    
def repeat_timer(count, timer_seconds, sleep_seconds):
    for _ in range(count):
        timer(timer_seconds)
        sleep(sleep_seconds)