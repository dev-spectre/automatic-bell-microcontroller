from lib.wlan import connect_to_wlan, register_ip
from lib.clock import sync_with_worldtimeapi, get_RTC
from lib.utils import try_till_success
from switch import repeat_timer
from lib.web_server import app

if __name__ == "__main__":    
    try_till_success(connect_to_wlan, max_try=10, should_reset=True)
    try_till_success(sync_with_worldtimeapi, err_msg = "Sync with world time api failed", max_try=10, should_reset=True)
    try_till_success(register_ip, err_msg="Couldn't register", max_try=5)
    repeat_timer(10, 5, 5)
    app.run(port=80)