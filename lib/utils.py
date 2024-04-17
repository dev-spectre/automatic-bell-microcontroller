from log import log

def try_till_success(function, err_msg="", max_try = -1, should_reset = False):
    from gc import collect
    
    collect()
    
    while max_try != 0:
        max_try -= 1
        try:
            return function()
        except TypeError as err:
            return log(str(err))
        except OSError as err:
            collect()
            log(str(err), err_msg)
        except Exception as err:
            log(str(err), err_msg)
            continue
        else:
            return
    
    if should_reset:
        from machine import reset
        reset()

def bind(function, *args, **kwargs):
    def function_with_args():
        return function(*args, **kwargs)
    return function_with_args

if __name__ == "__main__":
    def a(b, c):
        return b + c
    
    print(try_till_success(bind(a, 1, 3)))