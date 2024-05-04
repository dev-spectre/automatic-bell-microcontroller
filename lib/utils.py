from log import log

@micropython.native
def try_till_success(function, err_msg="", max_try = -1, should_reset = False):
    from gc import collect
    
    collect()
    
    while max_try != 0:
        max_try -= 1
        try:
            return function()
        except TypeError as err:
            log(err)
            return
        except OSError as err:
            collect()
            log(err, err_msg)
        except Exception as err:
            log(err, err_msg)
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
