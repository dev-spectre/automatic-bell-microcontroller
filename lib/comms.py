# Modified from Easy_comms by Kevin McAleer. https://github.com/kevinmcaleer/easy_comms
from machine import UART
from time import time_ns
from log import log

class Comms():
    def __init__(self, uart_id=0, baud_rate=9600):
        self.uart_id = uart_id
        self.baud_rate = baud_rate
        self.uart = UART(uart_id, baud_rate)
        self.uart.init()
        
    def send(self, message):
        message += "\n"
        bytes_sent = self.uart.write(bytes(message, "utf-8"))
        log(f"Sent {bytes_sent} bytes of {message} (length {len(message)-1})")
        
    def read(self):
        start_time = time_ns()
        new_line = False
        message = ""
        while not new_line:
            if (self.uart.any() > 0):
                message += self.uart.read().decode("utf-8", "replace")
                if "\n" in message:
                    new_line = True
                    message = message.strip('\n')
                    log(f"received message: {message}\n(length: {len(message)})")
                    return message
            elif time_ns() > (start_time + 5 * 10**9):
                log(f"Message read timeout")
                return None
        else:
            return None