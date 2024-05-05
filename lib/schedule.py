from switch import switch_on, switch_off, timer, repeat_timer
from config import JSON
from log import log
from time import mktime, localtime, time
from asyncio import sleep

schedule = JSON("/schedule.json")

@micropython.native
def all_schedule_exists(*schedule_list):
    schedules = schedule.get("schedules")
    if len(schedule_list) > len(schedules): return False
    for i in schedule_list:
        if i not in schedules: return False
    return True

@micropython.native
def remove_date_from_unixtime(unixtime):
    if 0 <= unixtime < 86400: return unixtime
    unixtime = localtime(unixtime)
    unixtime = mktime((1970, 1, 1, unixtime[3], unixtime[4], unixtime[5], 3, 1))
    return unixtime

@micropython.native
def get_active_schedule():
    active_schedule_names = schedule.get("active")
    schedules = schedule.get("schedules")
    weekly_schedules = schedule.get("weekly")
    monthly_schedules = schedule.get("monthly")
    once = schedule.get("once")
    active_schedule = {}
    year, month, mday, _, _, _, weekday, _ = localtime()
    for i in active_schedule_names:
        if i in weekly_schedules[weekday] or \
           i in (monthly_schedules.get(str(mday)) or []) or \
           once.get(i) == [year, month, mday]:
            active_schedule.update(schedules.get(i))
    active_schedule = list(active_schedule.items())
    return sorted(active_schedule, key=lambda x: x[0])

@micropython.native
def get_next_ring_index(running, progress, current_time):
    r = range(len(running))
    for i in r:
        unixtime = remove_date_from_unixtime(running[i][0])
        has_rang = progress >= unixtime
        if current_time <= unixtime or 0 < current_time - unixtime < int(schedule.get("max_wait")) and not has_rang:
            return i
    return -1

@micropython.native
def ring_bell(running, idx):
    params = running[idx][1].split("/", 3)
    log(running, params, idx)
    mode = params[0].lower()
    if mode == "on":
        switch_on()
    elif mode == "off":
        switch_off()
    elif mode == "timer":
        on_seconds = float(params[1])
        timer(on_seconds)
    elif mode == "repeat":
        repeat = int(params[1])
        on_seconds = float(params[2])
        off_seconds = float(params[3])
        repeat_timer(repeat, on_seconds, off_seconds)

@micropython.native
def save_progress(running, idx, current_time_with_date, next_ring):
    schedule.set("progress", next_ring)
    schedule.set("last_ring", remove_date_from_unixtime(time()))
    if running[idx] is running[-1]:
        log("completed schedule")
        schedule.set("is_complete", True)
        schedule.set("completed_on", current_time_with_date)

@micropython.native
def reset_progress(current_time_with_date):
    if schedule.get("is_complete") and current_time_with_date - schedule.get("completed_on") > int(schedule.get("max_wait")):
        log("reset schedule")
        schedule.set("is_complete", False)
        schedule.set("progress", -1)
        schedule.set("last_ring", schedule.get("gap") * -1)

@micropython.native
async def run():
    while True:
        try:
            await sleep(0.1)
            running = get_active_schedule()
            if running == []:
                await sleep(50)
                continue

            current_time_with_date = time()
            current_time = remove_date_from_unixtime(current_time_with_date)

            reset_progress(current_time_with_date)

            progress = schedule.get("progress")
            if progress >= 0: progress = remove_date_from_unixtime(progress)

            idx = get_next_ring_index(running, progress, current_time)
            next_ring = remove_date_from_unixtime(running[idx][0])
            has_rang = progress >= next_ring

            if (current_time == next_ring or (0 < current_time - next_ring < int(schedule.get("max_wait"))) and not has_rang) and schedule.get("last_ring") + schedule.get("gap") < current_time:
                ring_bell(running, idx)
                save_progress(running, idx, current_time_with_date, next_ring)
            elif current_time < next_ring:
                await sleep(next_ring - current_time)
            elif schedule.get("last_ring") + schedule.get("gap") >= current_time:
                await sleep(schedule.get("last_ring") + schedule.get("gap") - current_time)
            else:
                await sleep(50)
        except Exception as err:
            log(err, function_name = "schedule.run")