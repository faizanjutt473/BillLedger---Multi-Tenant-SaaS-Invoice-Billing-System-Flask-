from functools import wraps
from flask import abort
from flask_login import login_required, current_user


def roles_required(*roles):
    """Login zaroori, aur role allowed list mein ho warna 403."""
    def deco(f):
        @wraps(f)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return deco