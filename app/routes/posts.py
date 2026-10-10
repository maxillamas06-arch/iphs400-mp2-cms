"""Posts: the content list and the post editor."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app import content, markdown, policy
from app.accounts import User
from app.content import Post, PostFields
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


def changeable_post(post: Post = Depends(existing_post),
                    user: User = Depends(signed_in_user)) -> Post:
    if not policy.may_change_post(user, post):
        raise Forbidden(user, "Solo puedes cambiar o borrar tus propios borradores.")
    return post


def render_post_form(request: Request, user: User, post: Post | None,
                     form: PostFields | Post, status_code: int = 200, **context):
    return render(request, "admin/post_form.html", user, status_code=status_code,
                  post=post, form=form, topics=content.TOPICS, **context)


def saved_message(message: str, fields: PostFields, saved: Post) -> str:
    """The save message, saying so when the typed slug was taken and got a number."""
    if fields.typed_slug and fields.typed_slug != saved.slug:
        return (f"{message} El enlace «{fields.typed_slug}» ya era de otra publicación:"
                f" quedó «{saved.slug}».")
    return message


@router.get("/content", name="content")
def content_list(request: Request, user: User = Depends(signed_in_user),
                 conn: sqlite3.Connection = Depends(get_db)):
    return render(request, "admin/content.html", user, posts=content.list_posts(conn))


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
    if not policy.may_change_post(user, post):
        return render(request, "admin/post_view.html", user, post=post,
                      body_html=markdown.to_html(post.body))
    return render_post_form(request, user, post, post)


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
def preview_post(request: Request, post: Post = Depends(changeable_post),
                 fields: PostFields = Depends(post_fields), user: User = Depends(signed_in_user)):
    return render_post_form(request, user, post, fields,
                            preview_html=markdown.to_html(fields.body))


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
