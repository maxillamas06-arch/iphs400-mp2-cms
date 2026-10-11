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
    "new_user",        # GET  /admin/users/new: the empty account form
    "create_user",     # POST /admin/users/new
    "user",            # GET  /admin/users/{id}: one account and its forms
    "change_role",     # POST /admin/users/{id}/role
    "set_nickname",    # POST /admin/users/{id}/nickname
    "set_temporary_password",  # POST /admin/users/{id}/password
    "deactivate_user",  # POST /admin/users/{id}/deactivate
    "reactivate_user",  # POST /admin/users/{id}/reactivate
    "publish_post",    # POST /admin/posts/{id}/publish
    "unpublish_post",  # POST /admin/posts/{id}/unpublish
    "send_back_post",  # POST /admin/posts/{id}/send-back
    "pending_edit",    # GET  /admin/posts/{id}/pending-edit: published vs proposed
    "approve_edit",    # POST /admin/posts/{id}/pending-edit/approve
    "send_back_edit",  # POST /admin/posts/{id}/pending-edit/send-back
    # Pages are the fan club's own voice: only the leader sees or writes them.
    "new_page",        # GET  /admin/pages/new: the empty page editor
    "create_page",     # POST /admin/pages/new
    "preview_new_page",  # POST /admin/pages/new/preview
    "page",            # GET  /admin/pages/{id}: the page editor
    "save_page",       # POST /admin/pages/{id}
    "preview_page",    # POST /admin/pages/{id}/preview
    "publish_page",    # POST /admin/pages/{id}/publish
    "unpublish_page",  # POST /admin/pages/{id}/unpublish
    "confirm_delete_page",  # GET  /admin/pages/{id}/delete: are you sure?
    "delete_page",     # POST /admin/pages/{id}/delete
})


# The only admin routes someone without a nickname may use: until they choose
# one, the admin gate sends every other admin route to the nickname screen.
NICKNAME_ROUTES = frozenset({
    "nickname",         # GET  /admin/nickname: the first-login nickname screen
    "choose_nickname",  # POST /admin/nickname
})


def must_choose_nickname(user: User, route_name: str | None) -> bool:
    return user.nickname is None and route_name not in NICKNAME_ROUTES


def may_use_route(user: User, route_name: str | None) -> bool:
    return user.is_leader or route_name not in LEADER_ONLY_ROUTES


def may_manage_accounts(user: User) -> bool:
    """Create accounts, change roles and nicknames, set temporary passwords,
    deactivate and reactivate: the leader only."""
    return user.is_leader


def may_manage_pages(user: User) -> bool:
    """See, write, publish and delete pages: the leader only. Pages are the fan
    club's own voice, never submitted (ADR-003)."""
    return user.is_leader


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
