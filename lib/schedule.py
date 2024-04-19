from switch import switch_on, switch_off, timer, repeat_timer
from config import JSON
from log import log
from time import time
from asyncio import sleep

schedule = JSON("/schedule.json")

@micropython.native
def get_next_ring_index(running, progress, current_time):
    r = range(len(running))
    for i in r:
        unixtime = running[i][0]
        if current_time <= unixtime or 0 < current_time - unixtime < int(schedule.get("max_wait")) and not progress >= unixtime:
            return i
    return -1

@micropython.native
def run():
    while True:
        try:
            await sleep(0.1)
            active = schedule.get("active")
            running = schedule.get("schedules").get(active)
            running = sorted(running, key=lambda x: x[0])
            current_time = time()
            progress = schedule.get("progress")
            idx = get_next_ring_index(running, progress, current_time)
            next_ring = running[idx][0]
            has_rang = progress >= next_ring
            if current_time == next_ring or (0 < current_time - next_ring < int(schedule.get("max_wait"))) and not has_rang:
                params = running[idx][1].split("/", 3)
                log(running, current_time, params)
                mode = params[0].lower()
                if mode == "on":
                    switch_on()
                    schedule.set("progress", next_ring)
                elif mode == "off":
                    switch_off()
                    schedule.set("progress", next_ring)
                elif mode == "timer":
                    on_seconds = float(params[1])
                    timer(on_seconds)
                    schedule.set("progress", next_ring)
                elif mode == "repeat":
                    repeat = int(params[1])
                    on_seconds = float(params[2])
                    off_seconds = float(params[3])
                    repeat_timer(repeat, on_seconds, off_seconds)
                    schedule.set("progress", next_ring)
            elif current_time < next_ring:
                await sleep(next_ring - current_time)
            else:
                await sleep(50)
        except Exception as err:
            log(str(err))
            