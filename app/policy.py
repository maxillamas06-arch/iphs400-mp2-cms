"""Policy: the one place that says what a person may do.

Every leader-only admin route is named here, and only here. The admin gate
(`app.web.signed_in_user`) refuses a member on any of them, and the
access-control test reads this set, so protecting a new leader-only route means
adding its name below.
"""
from __future__ import annotations

from app.accounts import User
from app.content import Post, Status

LEADER_ONLY_ROUTES = frozenset({
    "users",           # GET /admin/users: the list of accounts
    "publish_post",    # POST /admin/posts/{id}/publish
    "unpublish_post",  # POST /admin/posts/{id}/unpublish
})


def may_use_route(user: User, route_name: str | None) -> bool:
    return user.is_leader or route_name not in LEADER_ONLY_ROUTES


def may_change_post(user: User, post: Post) -> bool:
    """Save, preview or delete this post: the leader, any post; a member, only
    their own drafts (ADR-003)."""
    return user.is_leader or (post.author_id == user.id and post.status == Status.DRAFT)


def may_publish(user: User, post: Post) -> bool:
    """Publish this post: the leader only, and a member's post only once its
    member has submitted it. The leader's own drafts go straight out (ADR-003)."""
    return user.is_leader and (post.author_id == user.id or post.status != Status.DRAFT)
