from contextlib import contextmanager

USAGE_TRACKER = None

@contextmanager
def usage_tracker():
    global USAGE_TRACKER
    assert USAGE_TRACKER is None
    USAGE_TRACKER = []
    try:
        yield
    finally:
        USAGE_TRACKER = None

def get_total_usage():
    global USAGE_TRACKER

    prompt_tokens = 0
    completion_tokens = 0

    for usage in USAGE_TRACKER:
        prompt_tokens += usage['prompt_tokens']
        completion_tokens += usage['completion_tokens']

    return {
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens
    }

def append_to_usage_tracker(usage):
    global USAGE_TRACKER
    USAGE_TRACKER.append(usage)