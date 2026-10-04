import functools
from typing import Any, Callable, Optional

from .recorder import BlackBoxRecorder


def trace_node(
    recorder: BlackBoxRecorder,
    name: Optional[str] = None,
    event_type: str = "execution",
):
    """
    Decorator that automatically records a function execution
    as a Black Box trace node.
    """

    def decorator(func: Callable):

        @functools.wraps(func)
        def wrapper(*args, **kwargs):

            node_name = name or func.__name__

            with recorder.trace(
                name=node_name,
                event_type=event_type,
                inputs={
                    "args": args,
                    "kwargs": kwargs,
                },
            ) as step:

                result = func(*args, **kwargs)

                step.set_output(result)

                return result

        return wrapper

    return decorator

