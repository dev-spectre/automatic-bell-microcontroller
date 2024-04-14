from microdot import Microdot, redirect
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
    
    raise Exception
    return {
        "success": True,
        "data": { "datetime": get_time() },
        }

@app.get("/config")
async def get_config(request):
    key = request.json.get("key")
    
    if not key:
        return {
            "success": False,
            "msg": "Key not found"
            }, 422
    
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

@app.get("/configs")
async def get_configs(request):
    return {
        "success": True,
        "data": config.load()
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

if __name__ == "__main__":
    app.run(port=8787)
