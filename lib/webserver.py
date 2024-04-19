from microdot import Microdot, redirect
from schedule import schedule
from config import config

app = Microdot()

@app.get("/")
async def index(request):
    from wlan import get_ip
    
    protocol = config.get("frontend_protocol")
    if not protocol:
        protocol = "http"
        
    return redirect(f"{protocol}://{config.get('frontend_domain')}/?ip={get_ip()}")

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
        if key == active or key not in schedules: continue
        deleted[key] = schedules.pop(key)
    schedule.set("schedules", schedules)
    return {
        "success": True,
        "data": deleted,
        }, 200

@app.route("/schedule", methods=["POST", "PUT"])
async def create_schedule(request):
    schedules_to_add = request.json.get("schedules")
    
    if not schedules_to_delete:
        return {
            "success": False,
            "msg": "No schedules given to add/update",
            }, 422
    
    schedules = schedule.get("schedules")
    added = {}
    for key in schedules_to_add:
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
async def update_active_schedule(request):
    active = request.json.get("active")
    schedules = schedule.get("schedules")
    if active not in schedules:
        return {
            "success": False,
            "msg": "Schedule doesn't exists",
            }, 404
    
    schedule.set("active", active)
    return {
        "success": True,
        "msg": f"{active} is now active schedule",
        "data": {
            "active": active,
            },
        }, 201

@app.errorhandler(413)
async def max_req_length(request):
    return {
        "success": False,
        "msg": "Max request length reached (16KB)",
        }, 413

@app.errorhandler(404)
async def not_found(request):
    return {
        "success": False,
        "msg": "Route not found",
        }, 404

@app.errorhandler(OSError)
def os_error(request, exception):
    return {
        "success": False,
        "msg": "OS Error",
        "err": exception,
        }, 500

@app.errorhandler(RuntimeError)
def runtime_error(request, exception):
    return {
        "success": False,
        "msg": "Runtime error",
        "err": exception,
        }, 500

@app.errorhandler(Exception)
def unkown_error(request, exception):
    return {
        "success": False,
        "msg": "Unkown error",
        "err": exception
        }, 500

if __name__ == "__main__":
    app.run(port=8787)
