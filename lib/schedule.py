from switch import switch_on, switch_off, timer, repeat_timer
from config import JSON
from log import log
from time import mktime, localtime, time
from asyncio import sleep
from clock import is_synced as time_is_synced, get_date

schedule = JSON("/schedule.json")

@micropython.native
def convert_to_unix_time(time_string):
    hour, minute = map(int, time_string.split(":"))
    tm = (1970, 1, 1, hour, minute, 0, 0, 0)
    unix_time = mktime(tm)
    return unix_time

@micropython.native
def get_mode_string(mode):
    duration = mode["duration"]
    if mode["type"] == "single":
        return f"timer/{duration}"
    else:
        ring_count = mode.get("ringCount", 0)
        gap = mode.get("gap", 0)
        return f"repeat/{ring_count}/{duration}/{gap}"
    
@micropython.native
def expand_schedule(schedules):
    expanded_schedule = {}
    for sched in schedules:
        start_time = convert_to_unix_time(sched["start"])
        if sched["type"] == "session":
            end_time = convert_to_unix_time(sched.get("end", ""))
            include_end_time = sched.get("includeEndTime", True)
            interval_in_seconds = sched.get("interval", 0) * 60
            mode = get_mode_string(sched["mode"])
            i = start_time
            while i < end_time:
                expanded_schedule[int(i)] = mode
                i += interval_in_seconds
            if include_end_time:
                expanded_schedule[end_time] = mode
        else:
            mode = get_mode_string(sched["mode"])
            expanded_schedule[start_time] = mode
    return expanded_schedule

@micropython.native
def is_wild_schedule(schedule_name, strict=True):
    wild_schedule = schedule.get("schedules").get(schedule_name)
    if len(wild_schedule) == 0 or len(wild_schedule[0]) != 2: return False
    wild_schedules = schedule.get("wild_schedules")
    return wild_schedule[0][0] == "*" or not strict and schedule_name in wild_schedules

@micropython.native
def all_schedule_exists(*schedule_list):
    schedules = schedule.get("schedules")
    if len(schedule_list) > len(schedules): return False
    for i in schedule_list:
        if i not in schedules: return False
    return True

@micropython.native
def remove_non_existent_schedules():
    weekly_schedules = schedule.get("weekly")
    monthly_schedules = schedule.get("monthly")
    once = schedule.get("once")
    wild_schedules = schedule.get("wild_schedules")
    skip = schedule.get("skip")
    active = schedule.get("active")
    schedules = schedule.get("schedules")

    for i in range(len(weekly_schedules)):
        weekly_schedules[i] = [j for j in weekly_schedules[i] if j in schedules]

    for key in list(once.keys()):
        once[key] = [i for i in once[key] if i in schedules]
        if not once[key]: once.pop(key)

    for key in list(skip.keys()):
        skip[key] = [i for i in skip[key] if i in schedules]
        if not skip[key]: skip.pop(key)
  
    for key in list(monthly_schedules.keys()):
        monthly_schedules[key] = [i for i in monthly_schedules[key] if i in schedules]
        if not monthly_schedules[key]: monthly_schedules.pop(key)

    schedule.set("active", [i for i in active if i in schedules])
    schedule.set("wild_schedules", [i for i in wild_schedules if i in schedules])
    
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
    once = schedule.get("once").get(get_date()) or []
    skip = schedule.get("skip").get(get_date()) or {}
    active_schedule = {}
    _, _, mday, _, _, _, weekday, _ = localtime()
    for i in active_schedule_names:
        if i not in schedules or i in skip: continue
        if i in weekly_schedules[weekday] or \
           i in (monthly_schedules.get(str(mday)) or []) or \
           i in once:
            if not is_wild_schedule(i):
                expanded_schedule = expand_schedule(schedules.get(i))
                active_schedule.update(expanded_schedule)
    active_schedule = list(active_schedule.items())
    return sorted(active_schedule, key=lambda x: x[0])

@micropython.native
def get_next_ring_index(running, progress, current_time):
    start_idx = 0
    midnight_reset_count = schedule.get("midnight_reset_count")
    if midnight_reset_count > 0:
        r = range(1, len(running))
        for i in r:
            prev_time = remove_date_from_unixtime(running[i-1][0])
            next_time = remove_date_from_unixtime(running[i][0])
            if prev_time > next_time:
                start_idx = i
                midnight_reset_count -= 1
                if midnight_reset_count <= 0: break
    r = range(start_idx, len(running))
    for i in r:
        unixtime = remove_date_from_unixtime(running[i][0])
        has_rang = progress >= unixtime
        if current_time <= unixtime or 0 < current_time - unixtime < int(schedule.get("max_wait")) and not has_rang:
            return i
    return -1

@micropython.native
def ring_bell(params):
    params = params.split("/", 3)
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
        schedule.set("midnight_reset_count", 0)
        active_schedules = schedule.get("active")
        once = schedule.get("once")
        i = 0
        wild_schedules = schedule.get("wild_schedules")
        weekly_schedules = schedule.get("weekly")
        monthly_schedules = schedule.get("monthly")
        weekly_and_monthly = [x for i in weekly_schedules for x in i]
        monthly = [x for i in monthly_schedules for x in monthly_schedules[i]]
        weekly_and_monthly.extend(monthly)
        date = get_date()
        while i < len(active_schedules):
            if active_schedules[i] in wild_schedules:
                schedules = schedule.get("schedules")
                wild_schedule = schedules.get(active_schedules[i])
                if wild_schedule[0][0] == "*": continue
                r = range(len(wild_schedule)-1, 0, -1)
                for j in r:
                    gap = f"+{wild_schedule[j][0] - wild_schedule[j-1][0]}"
                    wild_schedule[j][0] = gap
                wild_schedule[0][0] = "*"
                schedule.set("schedules", schedules)
            if active_schedules[i] in (once.get(date) or []):
                once[date].remove(active_schedules[i])
                if once[date] == []: once.pop(date)
                schedule.set("once", once)
            if active_schedules[i] not in weekly_and_monthly:
                active_schedules.pop(i)
            else:
                i += 1
        schedule.set("active", active_schedules)
        remove_non_existent_schedules()

@micropython.native
def reset_progress(current_time_with_date):
    if schedule.get("progress") > remove_date_from_unixtime(current_time_with_date):
        midnight_reset_count = schedule.get("midnight_reset_count")
        schedule.set("midnight_reset_count", midnight_reset_count + 1)
        schedule.set("progress", 0)
        schedule.set("last_ring", schedule.get("gap") * -1)
    if schedule.get("is_complete") and current_time_with_date - schedule.get("completed_on") > int(schedule.get("max_wait")):
        log("reset schedule")
        schedule.set("is_complete", False)
        schedule.set("last_ring", schedule.get("gap") * -1)
        schedule.set("progress", -1)
        skip = schedule.get("skip")
        date = get_date()
        if date in skip: skip.pop(date)
        schedule.set("skip", skip)

@micropython.native
async def run():
    while True:
        try:
            if not time_is_synced: await sleep(10)
            await sleep(0.1)
            running = get_active_schedule()

            current_time_with_date = time()
            current_time = remove_date_from_unixtime(current_time_with_date)

            reset_progress(current_time_with_date)
            
            if running == []:
                await sleep(1)
                continue
            
            progress = schedule.get("progress")
            if progress >= 0: progress = remove_date_from_unixtime(progress)

            idx = get_next_ring_index(running, progress, current_time)
            next_ring = remove_date_from_unixtime(running[idx][0])
            has_rang = progress >= next_ring

            if (current_time == next_ring or (0 < current_time - next_ring < int(schedule.get("max_wait"))) and not has_rang) and schedule.get("last_ring") + schedule.get("gap") < current_time:
                params = running[idx][1]
                log(running, params, idx)
                ring_bell(params)
                save_progress(running, idx, current_time_with_date, next_ring)
            elif current_time < next_ring:
                await sleep(next_ring - current_time)
            elif schedule.get("last_ring") + schedule.get("gap") >= current_time:
                await sleep(schedule.get("last_ring") + schedule.get("gap") - current_time)
            else:
                await sleep(10)
        except Exception as err:
            await sleep(1)
            log(err, function_name = "schedule.run")