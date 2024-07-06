from asyncio import sleep
from microdot import Microdot, redirect
from microdot.cors import CORS
from schedule import schedule, all_schedule_exists, ring_bell, is_wild_schedule
from config import JSON, config
from log import log

app = Microdot()
env = JSON("/.env.json")
cors = CORS(app, allowed_origins="*", allow_credentials=True)

@app.before_request
async def authenticate(request):
    if request.path in ["/", "/signup", "/signin", "/res"]: return None
    jwt = request.headers.get("Authorization")
    userkey = env.get("userkey") 
    if jwt != userkey:
        return {
            "success": False,
            "msg": "Invalid JWT"
            }

@app.get("/")
async def index(request):
    from wlan import get_ip
    
    protocol = config.get("frontend_protocol")
    if not protocol:
        protocol = "http"
        
    return redirect(f"{protocol}://{config.get('frontend_domain')}/?ip={get_ip()}")

@app.get("/res")
async def response(request):
    return { "success": True }

@app.put("/time")
async def set_time(request):
    from clock import sync_from_unixtime, get_time
    
    time = request.json
    unixtime = time.get("unixtime")
    
    if not unixtime:
        return { "success": False }
    
    sync_from_unixtime(unixtime)
    
    return {
        "success": True,
        "data": { "datetime": get_time() },
        }

@app.get("/config")
async def get_config(request):
    key = request.json.get("key")
    
    if not key:
        return {
            "success": True,
            "data": config.load(),
            }, 200
    
    value = config.get(key)
    if not value:
        return {
            "success": False,
            "msg": "Key doesn't exist"
            }
    
    return {
        "success": True,
        "data": { "value": value },
        }

@app.route("/config", methods=["POST", "PUT"])
async def set_config(request):
    prop = request.json
    
    if not prop.get("key") or not prop.get("value"):
        return {
            "success": False,
            "msg": "Missing parameters",
            }, 422
    
    if prop.get("key") in ["log", "wlan_credentials"]:
        return {
            "success": False,
            "msg": "Permission denied",
            }, 403
    
    if request.method == "POST" and config.get(prop.get("key")):
        return {
            "success": False,
            "msg": "Key exists",
            }, 403
    
    if prop.get("key") == "removable_keys":
        return {
            "success": False,
            "msg": "Couldn't set config property removable_keys",
            }, 403

    value = config.set(prop.get("key"), prop.get("value"))
    if request.method == "POST" and prop.get("key") != "removable_keys" and not prop.get("isNonRemovable"):
        removable_keys = config.get("removable_keys")
        removable_keys.append(prop.get("key"))
        config.set("removable_keys", removable_keys)
        
    if not value:
        return {
            "success": False,
            "msg": "Couldn't set config",
            }, 500
    
    return {
        "success": True,
        "data": {
            "key": prop.get("key"),
            "value": prop.get("value"),
            },
        }, 201

@app.delete("/config")
async def remove_config(request):
    key = request.json.get("key")
    
    if not key:
        return {
            "success": False,
            "msg": "Key not found"
            }, 422
    
    if key not in config.get("removable_keys"):
        return {
            "success": False,
            "msg": "Permission denied",
            }, 403
    
    removable_keys = config.get("removable_keys")
    removable_keys.remove(key)
    config.set("removable_keys", removable_keys)
    
    return {
        "success": True,
        "data": {
            "key": key,
            "value": config.remove(key),
            },
        }

@app.get("/schedule")
async def get_schedule(request):
    key = request.json.get("key")
    
    if not key:
        return {
            "success": True,
            "data": schedule.load(),
            }, 200
    
    value = schedule.get("schedules").get(key)
    if not value:
        return {
            "success": False,
            "msg": "Key doesn't exist"
            }
    
    return {
        "success": True,
        "data": { key: value },
        }, 200


@app.delete("/schedule")
async def delete_schedule(request):
    schedules_to_delete = request.json.get("keys")

    if not schedules_to_delete:
        return {
            "success": False,
            "msg": "No schedules given to delete",
            }, 422

    schedules = schedule.get("schedules")
    deleted = {}
    active = schedule.get("active")
    weekly_schedules = schedule.get("weekly")
    monthly_schedules = schedule.get("monthly")
    once = schedule.get("once")
    wild_schedules = schedule.get("wild_schedules")

    for key in schedules_to_delete:
        if key in active or key not in schedules: continue
        if key in once: once.pop(key)
        if key in wild_schedules: wild_schedules.remove(key)
        
        for weekly_schedule in weekly_schedules:
            if key in weekly_schedule:
                weekly_schedule.remove(key)

        for monthly_schedule in monthly_schedules:
            if key in monthly_schedule:
                monthly_schedule.remove(key)

        deleted[key] = schedules.pop(key)
    schedule.set("schedules", schedules)
    schedule.set("once", once)
    schedule.set("monthly", monthly_schedules)
    schedule.set("weekly", weekly_schedules)
    return {
        "success": True,
        "data": deleted,
        }, 200

@app.route("/schedule", methods=["POST", "PUT"])
async def set_schedule(request):
    schedules_update = request.json.get("schedules")
    weekly_schedules_update = request.json.get("weekly")
    monthly_schedules_update = request.json.get("monthly")
    once_update = request.json.get("once")
    force_add = request.json.get("force")
    
    if not force_add and not weekly_schedules_update and not monthly_schedules_update and not once_update:
        return {
            "success": False,
            "msg": "Missing parameters",
            }, 422
    
    if not schedules_update:
        return {
            "success": False,
            "msg": "No schedules given to add/update",
            }, 422
    
    schedules = schedule.get("schedules")
    added = {}
    for key in schedules_update:
        if request.method == "POST" and schedules.get(key):
            continue
        schedules[key] = schedules_update[key]
        added[key] = schedules_update[key]

        wild_schedules = schedule.get("wild_schedules")
        if is_wild_schedule(key) and key not in wild_schedules: 
            wild_schedules.append(key)
            schedule.set("wild_schedules", wild_schedules)
            
    schedule.set("schedules", schedules)

    if weekly_schedules_update:
        weekly_schedules = schedule.get("weekly")
        for i, schedule_list in weekly_schedules_update.items():
            idx = int(i)
            if 0 <= idx <= 6:
                weekly_schedules[idx].extend(schedule_list)
                weekly_schedules[idx] = list(set(weekly_schedules[idx]))
        schedule.set("weekly", weekly_schedules)

    if monthly_schedules_update:
        monthly_schedules = schedule.get("monthly")
        for i, schedule_list in monthly_schedules_update.items():
            idx = int(i)
            if not (1 <= idx <= 31): continue
            if i in monthly_schedules:
                monthly_schedules[i].extend(schedule_list)
                monthly_schedules[i] = list(set(monthly_schedules[i]))
            else:
                monthly_schedules[i] = list(set(schedule_list))
        schedule.set("monthly", monthly_schedules)

    if once_update:
        once = schedule.get("once")
        once.update(once_update)
        schedule.set("once", once)

    return {
        "success": True,
        "data": added,
        }, 201

@app.get("/schedule/active")
async def get_active_schedule(request):
    return {
        "success": True,
        "data": schedule.get("active")
        }, 200

@app.put("/schedule/active")
async def set_active_schedule(request):
    active = request.json.get("active")
    if not all_schedule_exists(*active):
        return {
            "success": False,
            "msg": "Schedule doesn't exists",
            }, 404

    schedule.set("active", active)
    return {
        "success": True,
        "data": {
            "active": active,
            },
        }, 201

@app.put("/schedule/gap")
async def set_schedule_gap(request):
    gap = request.json.get("gap")
    if not gap:
        return {
            "success": False,
            "msg": "Missing parameters"
            }, 422
    
    if type(0) != type(gap) or not 0 <= gap <= 60:
        return {
            "success": False,
            "msg": "Invalid input",
            }
    
    schedule.set("gap", gap)
    return {
        "success": True,
        "msg": f"Schedule gap set to {gap} second(s)",
        "data": {
            "gap": gap,
            },
        }, 201

@app.put("/schedule/wait")
async def set_schedule_max_wait(request):
    max_wait = request.json.get("wait")
    if not max_wait:
        return {
            "success": False,
            "msg": "Missing parameters"
            }, 422
    
    if type(0) != type(max_wait) or not 20 <= max_wait <= 300:
        return {
            "success": False,
            "msg": "Invalid input",
            }
    
    schedule.set("max_wait", max_wait)
    return {
        "success": True,
        "msg": f"Schedule max_wait set to {max_wait} second(s)",
        "data": {
            "wait": max_wait,
            },
        }, 201

@app.post("/bell/ring")
async def manual_ring(request):
    from asyncio import get_event_loop
    mode = request.json.get("mode")
    if not mode:
        return {
            "success": False,
            "msg": "Couldn't ring bell"
            }
    ring_bell(mode)
    return {
        "success": True,
        }, 201

@app.put("/schedule/run")
async def run_schedule(request):
    from time import localtime, time
    schedule_name = request.json.get("schedule")
    schedules = schedule.get("schedules")

    if not schedule_name:
        return {
            "success": False,
            "msg": "Missing parameters",
            }, 422

    if not schedules.get(schedule_name):
        return {
            "success": False,
            "msg": "Schedule doesn't exist",
            }, 404
    
    if is_wild_schedule(schedule_name):
        wild_schedule = schedules.get(schedule_name)

        prev_time = time()
        wild_schedule[0][0] = prev_time
        r = range(1, len(wild_schedule))
        for i in r:
            gap = int(wild_schedule[i][0][1:])
            prev_time += gap
            wild_schedule[i][0] = prev_time
        schedule.set("schedules", schedules)

    active_schedules = schedule.get("active")
    if active_schedules == [] or active_schedules[-1] != schedule_name: active_schedules.append(schedule_name)
    once = schedule.get("once")
    year, month, mday, _, _, _, _, _ = localtime()
    once[schedule_name] = [year, month, mday]
    schedule.set("once", once)
    schedule.set("active", active_schedules)
    await sleep(0.5)
    return {
        "success": True,
        "msg": "Schedule added to active schedules"
        }, 201

@app.post("/signup")
async def signup(request):
    from urequests import post, put
    from json import dumps, loads
    
    key = request.json.get("key")
    username = request.json.get("username")
    password = request.json.get("password")
    
    if key != env.get("key"):
        return {
            "success": False,
            "msg": "Invalid key",
            }
    
    payload = dumps({
        "username": username,
        "password": password,
        })

    user_response = post(f"{config.get('backend_api')}/user/signup", headers={
        "Content-Type": "application/json",
        "Authorization": env.get("jwt"),
        }, data=payload
        ).json()
    
    if not user_response.get("success"):
        return user_response
    
    payload = dumps({
            "deviceId": request.json.get("id"),
            "userId": user_response.get("data").get("id"),
        })
    res = put(f"{config.get('backend_api')}/device/assign", headers={
        "Content-Type": "application/json",
        "Authorization": env.get("jwt"),
        }, data=payload
        ).json()
    return {
        "success": True,
        "data": {
            "id": res.get("data").get("userId"),
            "ip": res.get("data").get("ip"),
            "deviceId": res.get("data").get("id"),
            }
        }

@app.post("/signin")
async def signin(request):
    from urequests import delete
    
    userkey_id = request.json.get("userKeyId")
    res = delete(f"{config.get('backend_api')}/user/key", headers={
        "Content-Type": "application/json",
        "Authorization": env.get("jwt")
        },
        json={
            "userKeyId": userkey_id
        }).json()
    if not res.get("success") or not res.get("data").get("userKey"): return { "success": False }
    userkey = res.get("data").get("userKey")
    env.set("userkey", f"Bearer {userkey}")
    return {
        "success": True,
        }

@app.errorhandler(413)
async def max_req_length(request):
    return {
        "success": False,
        "msg": "Max request length reached (16KB)",
        }, 413

@app.errorhandler(404)
@app.errorhandler(405)
async def not_found(request):
    return {
        "success": False,
        "msg": "Route not found",
        }, 404

@app.errorhandler(OSError)
def os_error(request, exception):
    log(exception)
    return {
        "success": False,
        "msg": "OS Error",
        }, 500

@app.errorhandler(RuntimeError)
def runtime_error(request, exception):
    log(exception)
    return {
        "success": False,
        "msg": "Runtime error",
        }, 500

@app.errorhandler(Exception)
def unkown_error(request, exception):
    log(exception)
    return {
        "success": False,
        "msg": "Unkown error",
        }, 500

if __name__ == "__main__":
    app.run(port=8787)
