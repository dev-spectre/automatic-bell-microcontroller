from machine import RTC
from urequests import get
from math import floor
from config import config
from utime import localtime, gmtime

# DAY_IN_SECONDS = 86400
# DAY_OFFSET = 4
# DAYS_IN_WEEK = 7

def get_time():
    year, month, day, hour, minute, second, _, _ = localtime()
    return f"{day}/{month}/{year} {hour}:{minute}:{second}"

def sync_from_unixtime(unixtime, weekday=None):
    tz_unixtime = unixtime + config.get("timezone_offset") + config.get("time_fetch_offset")
    
    if not weekday:
        weekday = (floor(tz_unixtime / 86400) + 4) % 7
    year, month, day, hour, minute, second, _, _ = gmtime(tz_unixtime)
    
    rtc = RTC()
    rtc.datetime((year, month, day, weekday, hour, minute, second, 0))

def sync_with_worldtimeapi():
    from log import log
    
    data = (get(url="http://worldtimeapi.org/api/timezone/Asia/Kolkata")).json()
    try:
        sync_from_unixtime(data.get("unixtime"), data.get("day_of_week"))
        log(f"Time synced with world time api, current time: {get_time()}")
    except Exception as err:
        log(str(err))
