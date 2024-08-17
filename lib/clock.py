from machine import RTC
from urequests import get
from math import floor
from config import config
from utime import localtime, gmtime

# DAY_IN_SECONDS = 86400
# DAY_OFFSET = 4
# DAYS_IN_WEEK = 7
is_synced = False

def get_time():
    year, month, day, hour, minute, second, _, _ = localtime()
    return f"{day}/{month}/{year} {hour}:{minute}:{second}"

def get_date():
    return get_time().split()[0]

def sync_from_unixtime(unixtime, weekday=None):
    tz_unixtime = unixtime + config.get("timezone_offset") + config.get("time_fetch_offset")
    
    if not weekday:
        weekday = (floor(tz_unixtime / 86400) + 4) % 7
    year, month, day, hour, minute, second, _, _ = gmtime(tz_unixtime)
    
    rtc = RTC()
    rtc.datetime((year, month, day, weekday, hour, minute, second, 0))
    global is_synced
    is_synced = True

def sync_with_worldtimeapi():
    from log import log
    
    res = get(url="http://worldtimeapi.org/api/timezone/Asia/Kolkata")
    data = res.json()
    try:
        sync_from_unixtime(data.get("unixtime"), data.get("day_of_week"))
        log(f"Time synced with world time api, current time: {get_time()}")
        res.close()
    except Exception as err:
        log(err)
        res.close()