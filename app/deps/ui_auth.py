"""Beginner-friendly overview for this module.

WHAT: Handles the logic defined in "app/deps/ui_auth.py" for the Time Tracker app.
WHEN: Invoked when its functions or classes are imported and called.
WHY: Provides supporting behaviour so the service runs smoothly.
HOW: Read the inline comments and docstrings below for the step-by-step flow.

File: app/deps/ui_auth.py
"""


from __future__ import annotations
from fastapi import Request, HTTPException, status

SESSION_FLAG = "ui_authenticated"

def is_logged_in(request: Request) -> bool:
    try:
        return bool(request.session.get(SESSION_FLAG))
    except Exception:
        return False

async def require_ui_session(request: Request):
    """
    Gate for UI routes: requires a valid session created by the login flow.
    If not logged in, we raise 401 so the route handler can redirect,
    or you can handle redirects in a middleware (we keep it simple/explicit).
    """
    if not is_logged_in(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
    return True