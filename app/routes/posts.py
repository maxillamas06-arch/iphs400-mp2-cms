"""Posts: the content list and the post editor."""
from __future__ import annotations

import sqlite3
from collections.abc import Callable

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app import content, markdown, policy
from app.accounts import User
from app.content import PendingEdit, Post, PostFields, Status
from app.web import Forbidden, NotFound, flash, get_db, render, signed_in_user

router = APIRouter(prefix="/admin", dependencies=[Depends(signed_in_user)])


def post_fields(title: str = Form(""), topic: str = Form(""), body: str = Form(""),
                slug: str = Form("")) -> PostFields:
    return PostFields(title=title, topic=topic, body=body, slug=slug)


def existing_post(post_id: str, user: User = Depends(signed_in_user),
                  conn: sqlite3.Connection = Depends(get_db)) -> Post:
    # An id that is not a number is as unknown as one that is not in the database.
    post = content.get_post(conn, int(post_id)) if post_id.isdecimal() else None
    if post is None:
        raise NotFound(user)
    return post


NOT_YOURS = "Solo puedes cambiar o borrar tus propios borradores."


def changeable_post(post: Post = Depends(existing_post),
                    user: User = Depends(signed_in_user)) -> Post:
    if not policy.may_change_post(user, post):
        raise Forbidden(user, NOT_YOURS)
    return post


def previewable_post(post: Post = Depends(existing_post),
                  user: User = Depends(signed_in_user)) -> Post:
    if not policy.may_use_editor(user, post):
        raise Forbidden(user, NOT_YOURS)
    return post


def proposable_post(post: Post = Depends(existing_post),
                    user: User = Depends(signed_in_user)) -> Post:
    if not policy.may_propose_edit(user, post):
        raise Forbidden(user, "Solo el miembro que escribió una publicación ya publicada puede"
                              " proponerle cambios.")
    return post


def publishable_post(post: Post = Depends(existing_post),
                     user: User = Depends(signed_in_user)) -> Post:
    if not policy.may_publish(user, post):
        raise Forbidden(user, "El borrador de un miembro se publica cuando quien lo escribió"
                              " lo envía para revisión.")
    return post


def own_post(post: Post = Depends(existing_post),
             user: User = Depends(signed_in_user)) -> Post:
    if not policy.may_submit_or_withdraw(user, post):
        raise Forbidden(user, "Solo el miembro que escribió esta publicación puede enviarla o"
                              " retirarla.")
    return post


def render_post_form(request: Request, user: User, post: Post | None,
                     form: PostFields | Post | PendingEdit, status_code: int = 200, **context):
    return render(request, "admin/post_form.html", user, status_code=status_code,
                  post=post, form=form, topics=content.TOPICS, **context)


def render_post_page(request: Request, user: User, post: Post, status_code: int = 200,
                     **context):
    """The post as this person gets it: the editor when they may change it or
    propose an edit to it, else read only. A member proposing an edit picks up
    their pending edit where they left it."""
    if not policy.may_use_editor(user, post):
        return render(request, "admin/post_view.html", user, status_code=status_code,
                      post=post, body_html=markdown.to_html(post.body), **context)
    proposal = post.pending_edit if policy.may_propose_edit(user, post) else None
    return render_post_form(request, user, post, proposal or post, status_code=status_code,
                            **context)


def saved_message(message: str, fields: PostFields, saved: Post) -> str:
    """The save message, saying so when the typed slug was taken and got a number."""
    if fields.typed_slug and fields.typed_slug != saved.slug:
        return (f"{message} El enlace «{fields.typed_slug}» ya era de otra publicación:"
                f" quedó «{saved.slug}».")
    return message


@router.get("/content", name="content")
def content_list(request: Request, status: str = "", topic: str = "", pending: str = "",
                 user: User = Depends(signed_in_user),
                 conn: sqlite3.Connection = Depends(get_db)):
    # A filter value the list does not offer is no filter at all.
    chosen_status = Status(status) if status in content.STATUS_NAMES else None
    chosen_topic = topic if topic in content.TOPICS else None
    with_pending_edit = pending == "1"
    return render(request, "admin/content.html", user,
                  posts=content.list_posts(conn, chosen_status, chosen_topic, with_pending_edit),
                  status=chosen_status, topic=chosen_topic, pending=with_pending_edit,
                  statuses=content.STATUS_NAMES, topics=content.TOPICS)


@router.get("/posts/new", name="new_post")
def new_post(request: Request, user: User = Depends(signed_in_user)):
    return render_post_form(request, user, None, PostFields(title="", topic="", body=""))


@router.post("/posts/new", name="create_post")
def create_post(request: Request, fields: PostFields = Depends(post_fields),
                user: User = Depends(signed_in_user),
                conn: sqlite3.Connection = Depends(get_db)):
    try:
        post = content.create_post(conn, user, fields)
    except content.ContentError as refused:
        return render_post_form(request, user, None, fields, status_code=400,
                                error=str(refused))
    flash(request, saved_message("Borrador guardado.", fields, post))
    return RedirectResponse(request.app.url_path_for("post", post_id=post.id), status_code=303)


@router.post("/posts/new/preview", name="preview_new_post")
def preview_new_post(request: Request, fields: PostFields = Depends(post_fields),
                     user: User = Depends(signed_in_user)):
    return render_post_form(request, user, None, fields,
                            preview_html=markdown.to_html(fields.body))


@router.get("/posts/{post_id}", name="post")
def post_page(request: Request, post: Post = Depends(existing_post),
              user: User = Depends(signed_in_user)):
    return render_post_page(request, user, post)


@router.post("/posts/{post_id}", name="save_post")
def save_post(request: Request, post: Post = Depends(changeable_post),
              fields: PostFields = Depends(post_fields), user: User = Depends(signed_in_user),
              conn: sqlite3.Connection = Depends(get_db)):
    try:
        saved = content.save_post(conn, post, fields)
    except content.ContentError as refused:
        return render_post_form(request, user, post, fields, status_code=400,
                                error=str(refused))
    flash(request, saved_message("Cambios guardados.", fields, saved))
    return RedirectResponse(request.app.url_path_for("post", post_id=post.id), status_code=303)


@router.post("/posts/{post_id}/preview", name="preview_post")
def preview_post(request: Request, post: Post = Depends(previewable_post),
                 fields: PostFields = Depends(post_fields), user: User = Depends(signed_in_user)):
    return render_post_form(request, user, post, fields,
                            preview_html=markdown.to_html(fields.body))


@router.post("/posts/{post_id}/propose-edit", name="propose_edit")
def propose_edit(request: Request, post: Post = Depends(proposable_post),
                 fields: PostFields = Depends(post_fields), user: User = Depends(signed_in_user),
                 conn: sqlite3.Connection = Depends(get_db)):
    try:
        content.propose_edit(conn, post, fields)
    except content.ContentError as refused:
        return render_post_form(request, user, post, fields, status_code=400,
                                error=str(refused))
    flash(request, "Cambios propuestos. El líder los revisará; mientras tanto, los lectores siguen"
                   " viendo la versión publicada.")
    return RedirectResponse(request.app.url_path_for("post", post_id=post.id), status_code=303)


@router.get("/posts/{post_id}/pending-edit", name="pending_edit")
def pending_edit(request: Request, post: Post = Depends(existing_post),
                 user: User = Depends(signed_in_user)):
    """The published version and the pending edit side by side, each as readers
    would see it."""
    if post.pending_edit is None:
        raise NotFound(user)
    return render(request, "admin/pending_edit.html", user, post=post, edit=post.pending_edit,
                  published_html=markdown.to_html(post.body),
                  proposed_html=markdown.to_html(post.pending_edit.body))


def take_action(request: Request, user: User, post: Post, step: Callable[[], object],
                done: str):
    """A lifecycle button: done with a message, or refused with the reason why."""
    try:
        step()
    except content.ContentError as refused:
        return render_post_page(request, user, post, status_code=400, error=str(refused))
    flash(request, done)
    return RedirectResponse(request.app.url_path_for("post", post_id=post.id), status_code=303)


@router.post("/posts/{post_id}/submit", name="submit_post")
def submit_post(request: Request, post: Post = Depends(own_post),
                user: User = Depends(signed_in_user),
                conn: sqlite3.Connection = Depends(get_db)):
    return take_action(request, user, post, lambda: content.move(conn, post, content.SUBMIT),
                       "Enviada al líder para revisión.")


@router.post("/posts/{post_id}/withdraw", name="withdraw_post")
def withdraw_post(request: Request, post: Post = Depends(own_post),
                  user: User = Depends(signed_in_user),
                  conn: sqlite3.Connection = Depends(get_db)):
    return take_action(request, user, post, lambda: content.move(conn, post, content.WITHDRAW),
                       "Retirada. Volvió a ser borrador y puedes seguir escribiéndola.")


@router.post("/posts/{post_id}/publish", name="publish_post")
def publish_post(request: Request, post: Post = Depends(publishable_post),
                 user: User = Depends(signed_in_user),
                 conn: sqlite3.Connection = Depends(get_db)):
    return take_action(request, user, post, lambda: content.move(conn, post, content.PUBLISH),
                       "Publicada. Los lectores la verán después de la próxima actualización"
                       " del sitio.")


@router.post("/posts/{post_id}/send-back", name="send_back_post")
def send_back_post(request: Request, post: Post = Depends(existing_post),
                   user: User = Depends(signed_in_user),
                   conn: sqlite3.Connection = Depends(get_db)):
    return take_action(request, user, post, lambda: content.move(conn, post, content.SEND_BACK),
                       "Devuelta. Volvió a ser borrador: quien la escribió puede corregirla"
                       " y enviarla otra vez.")


@router.post("/posts/{post_id}/unpublish", name="unpublish_post")
def unpublish_post(request: Request, post: Post = Depends(existing_post),
                   user: User = Depends(signed_in_user),
                   conn: sqlite3.Connection = Depends(get_db)):
    return take_action(request, user, post, lambda: content.move(conn, post, content.UNPUBLISH),
                       "Volvió a ser borrador. Desaparecerá del sitio público con la próxima"
                       " actualización del sitio.")


@router.post("/posts/{post_id}/pending-edit/approve", name="approve_edit")
def approve_edit(request: Request, post: Post = Depends(existing_post),
                 user: User = Depends(signed_in_user),
                 conn: sqlite3.Connection = Depends(get_db)):
    return take_action(request, user, post, lambda: content.approve_edit(conn, post),
                       "Cambios aprobados. Los lectores verán la nueva versión después de la"
                       " próxima actualización del sitio.")


@router.post("/posts/{post_id}/pending-edit/send-back", name="send_back_edit")
def send_back_edit(request: Request, post: Post = Depends(existing_post),
                   user: User = Depends(signed_in_user),
                   conn: sqlite3.Connection = Depends(get_db)):
    return take_action(request, user, post, lambda: content.send_back_edit(conn, post),
                       "Cambios devueltos. La versión publicada quedó como estaba.")


@router.get("/posts/{post_id}/delete", name="confirm_delete_post")
def confirm_delete_post(request: Request, post: Post = Depends(changeable_post),
                        user: User = Depends(signed_in_user)):
    return render(request, "admin/post_delete.html", user, post=post)


@router.post("/posts/{post_id}/delete", name="delete_post")
def delete_post(request: Request, post: Post = Depends(changeable_post),
                conn: sqlite3.Connection = Depends(get_db)):
    content.delete_post(conn, post)
    flash(request, "Publicación borrada.")
    return RedirectResponse(request.app.url_path_for("content"), status_code=303)
