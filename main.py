from asyncio import run, get_event_loop
from lib.wlan import connect_to_wlan, register_ip
from lib.clock import sync_time
from lib.utils import try_till_success
from lib.webserver import app
from lib.schedule import run as run_schedule

@micropython.native
async def main():
    try_till_success(connect_to_wlan, max_try=10, should_reset=False)
    sync_time()
    loop = get_event_loop()
    loop.create_task(app.start_server(port=80))
    try_till_success(register_ip, err_msg="Couldn't register", max_try=5)
    loop.create_task(run_schedule())
    loop.run_forever()

if __name__ == "__main__":
    run(main())