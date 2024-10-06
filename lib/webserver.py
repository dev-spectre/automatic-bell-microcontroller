from asyncio import sleep
from microdot import Microdot, redirect
from microdot.cors import CORS
from schedule import schedule, all_schedule_exists, ring_bell, is_wild_schedule
from config import JSON, config
from clock import get_date
from log import log

app = Microdot()
env = JSON("/.env.json")
cors = CORS(app, allowed_origins="*", allow_credentials=True)

@app.before_request
async def authenticate(request):
    if request.path in ["/", "/signup", "/signin", "/res", "/password/reset"]: return None
    jwt = request.headers.get("Authorization")
    userkey = env.get("userkey") 
    if jwt not in userkey:
        return {
            "success": False,
            "msg": "Invalid JWT"
            }

@app.get("/res")
async def response(request):
    return { "success": True }

@app.get("/verify")
async def verify(request):
    return { "success": True }

@app.get("/schedule")
async def get_schedule(request):
    args = request.args
    
    if not args:
        return {
            "success": True,
            "data": schedule.load(),
            }, 200
    
    keys = args.getlist("key")
    values = {}
    for key in keys:
        value = schedule.get(key)
        if value:
            values[key] = value
        
    if not values:
        return {
            "success": False,
            "msg": "Key doesn't exist"
            }
    
    return {
        "success": True,
        "data": values,
        }, 200

@app.get("/config")
async def get_config(request):
    args = request.args
    
    if not args:
        return {
            "success": True,
            "data": config.load(),
            }, 200
    
    keys = args.getlist("key")
    values = {}
    for key in keys:
        value = config.get(key)
        if value:
            values[key] = value
        
    if not value:
        return {
            "success": False,
            "msg": "Key doesn't exist"
            }
    
    return {
        "success": True,
        "data": values,
        }

@app.put("/schedule/active")
async def set_active_schedule(request):
    active = (request.json or {}).get("active")
    if not all_schedule_exists(*active):
        return {
            "success": False,
            "msg": "Schedule doesn't exists",
            }, 404

    unique_active = []
    active_dict = dict.fromkeys(active)
    r = range(len(active) - 1, -1, -1)
    for i in r:
        schedule_name = active[i]
        if active_dict[schedule_name] is None:
            active_dict[schedule_name] = True
            unique_active.append(schedule_name)

    unique_active = unique_active[::-1]

    schedule.set("active", unique_active)
    return {
        "success": True,
        "data": {
            "active": unique_active,
            },
        }, 201

@app.put("/schedule/skip")
async def set_active_schedule(request):
    skip_update = (request.json or {}).get("skip")
    if not skip_update:
        return {
            "success": False,
            "msg": "Missing parameters",
            }, 404

    skip = schedule.get("skip")
    skip.update(skip_update)
    schedule.set("skip", skip)
    
    return {
        "success": True,
        "data": {
            "skip": skip,
            },
        }, 201

@app.route("/schedule", methods=["POST", "PUT"])
async def set_schedule(request):
    schedules_update = (request.json or {}).get("schedules")
    weekly_schedules_update = (request.json or {}).get("weekly") or {}
    monthly_schedules_update = (request.json or {}).get("monthly") or {}
    once_update = (request.json or {}).get("once") or {}
    force_add = (request.json or {}).get("force")
    is_assign_only = (request.json or {}).get("isAssignOnly")
    remove_existing = (request.json or {}).get("removeExisting")
    
    if not force_add and not weekly_schedules_update and not monthly_schedules_update and not once_update:
        return {
            "success": False,
            "msg": "Missing parameters",
            }, 422
    
    if not is_assign_only and not schedules_update:
        return {
            "success": False,
            "msg": "No schedules given to add/update",
            }, 422

    added = {}
    if not is_assign_only:
        schedules = schedule.get("schedules")
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

    if remove_existing:
        once = schedule.get("once")
        weekly_schedules = schedule.get("weekly")
        monthly_schedules = schedule.get("monthly")
        schedules_to_remove = set()
        
        for i in weekly_schedules_update:
            schedules_to_remove.update(weekly_schedules_update[i])

        for i in monthly_schedules_update:
            schedules_to_remove.update(monthly_schedules_update[i])

        for i in once_update:
            schedules_to_remove.update(once_update[i])

        for day_schedules in weekly_schedules:
            for i in schedules_to_remove:
                if i in day_schedules:
                    day_schedules.remove(i)

        for i in list(monthly_schedules.keys()):
            for j in schedules_to_remove:
                if j in monthly_schedules[i]:
                    monthly_schedules[i].remove(j)
            if not monthly_schedules[i]: monthly_schedules.pop(i)

        for i in list(once.keys()):
            for j in schedules_to_remove:
                if j in once[i]:
                    once[i].remove(j)
            if not once[i]: once.pop(i)

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
        for i in once_update:
            if i not in once:
                once[i] = once_update[i] or []
                continue
            once[i].extend(once_update[i])
            once[i] = list(set(once[i]))
        schedule.set("once", once)

    return {
        "success": True,
        "data": added,
        }, 201

@app.delete("/schedule")
async def delete_schedule(request):
    schedules_to_delete = (request.json or {}).get("keys")
    force = (request.json or {}).get("force")

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
    skip = schedule.get("skip")
    wild_schedules = schedule.get("wild_schedules")

    for key in schedules_to_delete:
        if key in active and not force or key not in schedules: continue
        if key in wild_schedules: wild_schedules.remove(key)
        
        if key in active:
            active.remove(key)
            
        for date in list(once.keys()):
            if key in once[date]:
                once[date].remove(key)
            if not once[date]: once.pop(date)

        for date in list(skip.keys()):
            if key in skip[date]:
                skip[date].remove(key)
            if not skip[date]: skip.pop(date)
        
        for weekly_schedule in weekly_schedules:
            if key in weekly_schedule:
                weekly_schedule.remove(key)

        for date in list(monthly_schedules.keys()):
            if key in monthly_schedules[date]:
                monthly_schedules[date].remove(key)
            if not monthly_schedules[date]: monthly_schedules.pop(date)

        deleted[key] = schedules.pop(key)
    schedule.set("schedules", schedules)
    schedule.set("once", once)
    schedule.set("monthly", monthly_schedules)
    schedule.set("weekly", weekly_schedules)
    return {
        "success": True,
        "data": deleted,
        }, 200

@app.post("/signin")
async def signin(request):
    from urequests import delete
    from gc import collect

    collect()

    userkey_id = (request.json or {}).get("userKeyId")
    res = delete(f"{config.get('backend_api')}/user/key", headers={
        "Content-Type": "application/json",
        "Authorization": env.get("jwt")
        },
        json={
            "userKeyId": userkey_id
        }).json()
    if not res.get("success") or not res.get("data").get("userKey"): return { "success": False }
    userkey = res.get("data").get("userKey")

    userkeys = env.get("userkey")
    userkeys.append(f"Bearer {userkey}")
    if len(userkeys) > 10:
        userkeys = userkeys[-10: -1]
    env.set("userkey", userkeys)

    collect()
    
    return {
        "success": True,
        }

@app.route("/config", methods=["PUT"])
async def set_config(request):
    new_config = (request.json or {})
    
    if not new_config:
        return {
            "success": False,
            "msg": "Missing parameters",
            }, 422

    updated = {}
    for key in new_config:
        if config.get(key) is None: continue
        config.set(key, new_config.get(key))
        updated[key] = new_config.get(key)
    
    if not updated:
        return {
            "success": False,
            "msg": "Couldn't set config",
            }, 500
    
    return {
        "success": True,
        "data": updated,
        }, 201

@app.put("/password/reset")
async def reset_password(request):
    from urequests import put
    from json import dumps
 
    if (request.json or {}).get("key") != env.get("key"):
        return {
            "success": False,
            "msg": "Invalid key",
            }

    payload = dumps({
        "username": (request.json or {}).get("username"),
        "password": (request.json or {}).get("password"),
        "key": (request.json or {}).get("key"),
        })
    res = put(f"{config.get('backend_api')}/user/password/reset", headers={
        "Content-Type": "application/json",
        "Authorization": env.get("jwt"),
        }, data=payload
        ).json()
    
    return res

@app.post("/bell/ring")
async def manual_ring(request):
    mode = (request.json or {}).get("mode")
    if not mode:
        return {
            "success": False,
            "msg": "Couldn't ring bell"
            }
    ring_bell(mode)
    return {
        "success": True,
        }, 201

@app.post("/signup")
async def signup(request):
    from gc import  collect
    from urequests import post, put
    from json import dumps
    
    collect()
    
    key = (request.json or {}).get("key")
    username = (request.json or {}).get("username")
    password = (request.json or {}).get("password")
    
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
            "deviceId": (request.json or {}).get("id"),
            "userId": user_response.get("data").get("id"),
        })
    res = put(f"{config.get('backend_api')}/device/assign", headers={
        "Content-Type": "application/json",
        "Authorization": env.get("jwt"),
        }, data=payload
        ).json()
    
    collect()
    
    return {
        "success": True,
        "data": {
            "id": res.get("data").get("userId"),
            "ip": res.get("data").get("ip"),
            "deviceId": res.get("data").get("id"),
            }
        }

@app.put("/schedule/run")
async def run_schedule(request):
    from time import time
    schedule_name = (request.json or {}).get("schedule")
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
    date = get_date()
    once_schedule_list = once.get(date)
    if not once_schedule_list: [schedule_name]
    else: once_schedule_list.append(schedule_name)
    once[date] = once_schedule_list
    schedule.set("once", once)
    schedule.set("active", active_schedules)
    await sleep(0.5)
    return {
        "success": True,
        "msg": "Schedule added to active schedules"
        }, 201

@app.put("/time")
async def set_time(request):
    from clock import sync_from_unixtime, get_time
    
    time = (request.json or {})
    unixtime = time.get("unixtime")
    
    if not unixtime:
        return { "success": False }
    
    sync_from_unixtime(unixtime)
    
    return {
        "success": True,
        "data": { "datetime": get_time() },
        }

@app.get("/")
async def index(request):
    from wlan import get_ip
    
    protocol = config.get("frontend_protocol")
    if not protocol:
        protocol = "http"
        
    return redirect(f"{protocol}://{config.get('frontend_domain')}/?ip={get_ip()}")

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
    from gc import collect
    from machine import reset
    collect()
    log(exception)
    reset()
    return {
        "success": False,
        "msg": "OS Error",
        }, 501

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
