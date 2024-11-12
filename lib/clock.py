from machine import RTC, Pin
from urequests import get
from math import floor
from config import config
from utime import localtime, gmtime, mktime
from ds1302 import DS1302

# DAY_IN_SECONDS = 86400
# DAY_OFFSET = 4
# DAYS_IN_WEEK = 7

rtc = DS1302(Pin(28), Pin(26), Pin(20))
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
    
    pico_rtc = RTC()
    pico_rtc.datetime((year, month, day, weekday, hour, minute, second, 0))
    global is_synced
    is_synced = True

def get_time_from_worldtimeapi():
    from log import log
    
    res = get(url="http://worldtimeapi.org/api/timezone/Asia/Kolkata")
    data = res.json()
    try:
        return data.get("unixtime"), data.get("day_of_week")
    except Exception as err:
        log(err)
        res.close()

def set_rtc(date_time = None):
    if not date_time: date_time = localtime()
    rtc.date_time([date_time[0], date_time[1], date_time[2], (date_time[-2] + 1) % 8, date_time[3], date_time[4], date_time[5]])
    rtc.start()
    
def sync_with_rtc():
    pico_rtc = RTC()
    pico_rtc.datetime(rtc.date_time() + [0])

    
def sync_time():
    from utils import try_till_success
    
    global is_synced
    sync_with_rtc()
    result = try_till_success(get_time_from_worldtimeapi, max_try=10, should_reset=False)
    if not result:
        is_synced = True
        return
    if result[0] - mktime(gmtime()) < 10:
        is_synced = True
        return
    if not is_synced:
        sync_from_unixtime(result[0], result[1])
        set_rtc()