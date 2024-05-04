from microdot import Microdot, redirect
from schedule import schedule, all_schedule_exists
from config import JSON, config
from log import log

app = Microdot()
env = JSON("/.env.json")

@app.before_request
async def authenticate(request):
    if request.path in ["/", "/signin", "/res"]: return None
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
    
    sync_from_unixtime(unixtime + config.get("time_fetch_offset"))
    
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
    for key in schedules_to_delete:
        if key in active or key not in schedules: continue
        deleted[key] = schedules.pop(key)
    schedule.set("schedules", schedules)
    return {
        "success": True,
        "data": deleted,
        }, 200

@app.route("/schedule", methods=["POST", "PUT"])
async def create_schedule(request):
    schedules_to_add = request.json.get("schedules")
    
    if not schedules_to_add:
        return {
            "success": False,
            "msg": "No schedules given to add/update",
            }, 422
    
    schedules = schedule.get("schedules")
    added = {}
    for key in schedules_to_add:
        if request.method == "POST" and schedules.get(key):
            continue
        schedules[key] = schedules_to_add[key]
        added[key] = schedules_to_add[key]
    schedule.set("schedules", schedules)
    return {
        "success": True,
        "data": added,
        }, 201

@app.get("/active")
async def get_active_schedule(request):
    return {
        "success": True,
        "data": schedule.get("active")
        }, 200

@app.put("/active")
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
