from network import WLAN, STA_IF
from config import config
from log import log

wlan = WLAN(STA_IF)
wlan.config(pm=WLAN.PM_NONE)
wlan.active(True)

def get_mac():
    from ubinascii import hexlify
    return hexlify(wlan.config("mac"), ":").decode().replace(":", "").lower()

def get_ip():
    return wlan.ifconfig()[0]

def is_connected():
    return wlan.isconnected()

def connect(ssid, password):
    from machine import Pin
    from time import sleep
    from network import STAT_GOT_IP, STAT_NO_AP_FOUND, STAT_WRONG_PASSWORD, STAT_CONNECT_FAIL
    from error import NoAccessPointFound, WrongPassword, ConnectionFailed
    
    pico_led = Pin("LED", Pin.OUT)
    
    if (password == ""):
        password = None
        
    if wlan.active():
        wlan.active(True)
        
    wlan.connect(ssid, password)
    max_wait = config.get("max_attempts")
    no_ap_retry = 20
    while not wlan.isconnected() and max_wait != 0:
        pico_led.toggle()
        status = wlan.status()
        if status == STAT_GOT_IP:
            break
        elif status == STAT_NO_AP_FOUND:
            log("No access point found")
            no_ap_retry -= 1
            if no_ap_retry < 0:
                raise NoAccessPointFound()
        elif status == STAT_WRONG_PASSWORD or max_wait == 1:
            wlan.disconnect()
            log("Wrong Password")
            raise WrongPassword()
        elif status == STAT_CONNECT_FAIL:
            raise ConnectionFailed()

        print(f"SSID: {ssid}, Password: {password}, status:", status)
        max_wait -= 1
        sleep(0.2)
    log(f"Connection IP: {get_ip()}")
    pico_led.off()
    return get_ip()
    
def scan_and_connect():
    from error import NoAccessPointFound, WrongPassword, ConnectionFailed
    from config import JSON
    
    env = JSON("../.env.json")
    
    if wlan.active():
        wlan.active(True)
        
    available_wlans = wlan.scan()
    log("Available WiFi:", available_wlans)
    for wlan_info in available_wlans:
        if wlan_info[-2] == 0:
            continue
        try:
            ssid = wlan_info[0]
            password = env.get("key")
            ip = connect(ssid, password)
            log(f"Connection IP: {ip}")
            return ssid, password, ip
        except ConnectionFailed:
            log("Connection failed")
        except (NoAccessPointFound, WrongPassword):
            continue   

def connect_to_wlan():
    from error import NoAccessPointFound, WrongPassword, ConnectionFailed

    wlan_credentials = config.get("wlan_credentials")
    print(wlan_credentials)
    if wlan_credentials:
        for wlan_cred in wlan_credentials:
            if wlan.isconnected():
              ip = get_ip()
              log(f"Connection IP: {ip}")
              return config.set("ip", ip)

            try:
              ssid = wlan_cred.get("ssid")
              password = wlan_cred.get("password")
              ip = connect(ssid, password)
              log(f"Connection IP: {ip}")
              return config.set("ip", ip)
            except (NoAccessPointFound, WrongPassword):
                continue

    ssid, password, ip = scan_and_connect()
    config.set("wlan_credentials", [{ "ssid": ssid, "password": password}])
    log(f"Connection IP: {ip}")
    return config.set("ip", ip)

def register_ip():
    from config import JSON
    from ujson import dumps
    
    env = JSON("/.env.json")
    device_id = env.get("device_id")
    ip = get_ip()
    key = env.get("key")
    header = {"Content-Type": "application/json", "Authorization": env.get("jwt")}
    if not device_id:
        from urequests import post
        
        payload = dumps({
            "key": key,
            "ip": ip
            })
        res = post(f"{config.get('backend_api')}/device", headers=header, data=payload).json()
        if res.get("success"):
            env.set("ip", ip)
            device_id = env.set("device_id", res["data"].get("deviceId"))
            log("Device registered on database with id", device_id)
            return device_id
        log("Couldn't register device")
        raise Exception("Device not registered", str(res))
    if ip != env.get("ip"):
        from urequests import put
        
        payload = dumps({
            "deviceId": env.get("device_id"),
            "key": env.get("key"),
            "ip": ip
            })
        res = put(f"{config.get('backend_api')}/device", headers=header, data=payload).json()
        if res.get("success"):
            log("IP changed on database", ip)
            return env.set("ip", ip)
        log("Couldn't update IP on database")
        raise Exception("Couldn't update IP on database")
        
        
if __name__ == "__main__":
    from utils import try_till_success
    
    try_till_success(connect_to_wlan)
    register_ip()
    