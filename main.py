from asyncio import sleep, run, get_event_loop
from lib.wlan import connect_to_wlan, register_ip
from lib.clock import sync_with_worldtimeapi
from lib.utils import try_till_success
from lib.webserver import app
from lib.schedule import run as run_schedule

@micropython.native
async def main():
    try_till_success(connect_to_wlan, max_try=10, should_reset=True)
    try_till_success(sync_with_worldtimeapi, err_msg = "Sync with world time api failed", max_try=10, should_reset=True)
    try_till_success(register_ip, err_msg="Couldn't register", max_try=5)
    loop = get_event_loop()
    loop.create_task(app.start_server(port=80))
    loop.create_task(run_schedule())
    loop.run_forever()

if __name__ == "__main__":
    run(main())