from config import config
from clock import get_time
from os import stat

def log(*msg):
    file_path = config.get("log") or "/log.txt"
    line = f"[{get_time()}]: "
    for i in msg:
        i = str(i)
        line += f" {i}"
    print(line)
    line += "\n"
    try:
        if stat(file_path)[6] > 5_24_288:
            line += "File size limit exceeded, overwirting log"
            raise Exception("File size limit exceeded")
        with open(file_path, "a") as f:
            f.write(line)
    except Exception as err:
        from gc import collect
        
        collect()
        with open(file_path, "w+") as f:
            logs = f.readlines()
            logs.append(line)
            quater_len = len(logs) // 4
            r = range(-quater_len, 0, -1)
            for i in r:
                f.write(logs[i])
        
        collect()