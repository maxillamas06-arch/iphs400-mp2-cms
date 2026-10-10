"""Policy: the one place that says what a person may do.

Every leader-only admin route is named here, and only here. The admin gate
(`app.web.signed_in_user`) refuses a member on any of them, and the
access-control test reads this set, so protecting a new leader-only route means
adding its name below.
"""
from __future__ import annotations

from app.accounts import User

LEADER_ONLY_ROUTES = frozenset({
    "users",  # GET /admin/users: the list of accounts
})


def may_use_route(user: User, route_name: str | None) -> bool:
    return user.is_leader or route_name not in LEADER_ONLY_ROUTES
