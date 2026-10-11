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
    "send_back_post",  # POST /admin/posts/{id}/send-back
    "pending_edit",    # GET  /admin/posts/{id}/pending-edit: published vs proposed
    "approve_edit",    # POST /admin/posts/{id}/pending-edit/approve
    "send_back_edit",  # POST /admin/posts/{id}/pending-edit/send-back
})


def may_use_route(user: User, route_name: str | None) -> bool:
    return user.is_leader or route_name not in LEADER_ONLY_ROUTES


def may_change_post(user: User, post: Post) -> bool:
    """Save this post directly, or delete it: the leader, any post; a member, only
    their own drafts (ADR-003)."""
    return user.is_leader or (post.author_id == user.id and post.status == Status.DRAFT)


def may_propose_edit(user: User, post: Post) -> bool:
    """Propose an edit to this post: only the member who wrote it, once it is
    published. The leader edits published posts directly instead (ADR-003)."""
    return (not user.is_leader and post.author_id == user.id
            and post.status == Status.PUBLISHED)


def may_use_editor(user: User, post: Post) -> bool:
    """Open this post in the editor and preview it: whoever may save it directly
    or propose an edit to it."""
    return may_change_post(user, post) or may_propose_edit(user, post)


def may_submit_or_withdraw(user: User, post: Post) -> bool:
    """Submit this post, or withdraw it: only the member who wrote it. The leader
    publishes or sends back instead (ADR-003)."""
    return not user.is_leader and post.author_id == user.id


def may_publish(user: User, post: Post) -> bool:
    """Publish this post: the leader only, and a member's post only once its
    member has submitted it. The leader's own drafts go straight out (ADR-003)."""
    return user.is_leader and (post.author_id == user.id or post.status != Status.DRAFT)
