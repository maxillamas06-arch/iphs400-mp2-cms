"""Pages (leader only): the page editor. Every route here is named in
`policy.LEADER_ONLY_ROUTES`."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app import content, markdown
from app.accounts import User
from app.content import Page, PageFields
from app.web import NotFound, flash, get_db, render, saved_message, signed_in_user

router = APIRouter(prefix="/admin/pages", dependencies=[Depends(signed_in_user)])


def page_fields(title: str = Form(""), body: str = Form(""), menu_order: str = Form(""),
                slug: str = Form("")) -> PageFields:
    return PageFields(title=title, body=body, menu_order=menu_order, slug=slug)


def existing_page(page_id: str, user: User = Depends(signed_in_user),
                  conn: sqlite3.Connection = Depends(get_db)) -> Page:
    # An id that is not a number is as unknown as one that is not in the database.
    page = content.get_page(conn, int(page_id)) if page_id.isdecimal() else None
    if page is None:
        raise NotFound(user, "esa página")
    return page


def render_page_form(request: Request, user: User, page: Page | None,
                     form: PageFields | Page, status_code: int = 200, **context):
    return render(request, "admin/page_form.html", user, status_code=status_code,
                  page=page, form=form, **context)


@router.get("/new", name="new_page")
def new_page(request: Request, user: User = Depends(signed_in_user)):
    return render_page_form(request, user, None, PageFields(title="", body="", menu_order=""))


@router.post("/new", name="create_page")
def create_page(request: Request, fields: PageFields = Depends(page_fields),
                user: User = Depends(signed_in_user),
                conn: sqlite3.Connection = Depends(get_db)):
    try:
        page = content.create_page(conn, user, fields)
    except content.ContentError as refused:
        return render_page_form(request, user, None, fields, status_code=400,
                                error=str(refused))
    flash(request, saved_message("Borrador de página guardado.", fields, page, "otra página"))
    return RedirectResponse(request.app.url_path_for("page", page_id=page.id), status_code=303)


@router.post("/new/preview", name="preview_new_page")
def preview_new_page(request: Request, fields: PageFields = Depends(page_fields),
                     user: User = Depends(signed_in_user)):
    return render_page_form(request, user, None, fields,
                            preview_html=markdown.to_html(fields.body))


@router.get("/{page_id}", name="page")
def page_editor(request: Request, page: Page = Depends(existing_page),
                user: User = Depends(signed_in_user)):
    return render_page_form(request, user, page, page)


@router.post("/{page_id}", name="save_page")
def save_page(request: Request, page: Page = Depends(existing_page),
              fields: PageFields = Depends(page_fields), user: User = Depends(signed_in_user),
              conn: sqlite3.Connection = Depends(get_db)):
    try:
        saved = content.save_page(conn, page, fields)
    except content.ContentError as refused:
        return render_page_form(request, user, page, fields, status_code=400,
                                error=str(refused))
    flash(request, saved_message("Cambios guardados.", fields, saved, "otra página"))
    return RedirectResponse(request.app.url_path_for("page", page_id=page.id), status_code=303)


@router.post("/{page_id}/preview", name="preview_page")
def preview_page(request: Request, page: Page = Depends(existing_page),
                 fields: PageFields = Depends(page_fields), user: User = Depends(signed_in_user)):
    return render_page_form(request, user, page, fields,
                            preview_html=markdown.to_html(fields.body))


def take_action(request: Request, user: User, page: Page, transition: content.Transition,
                conn: sqlite3.Connection, done: str):
    """A lifecycle button: done with a message, or refused with the reason why."""
    try:
        content.move_page(conn, page, transition)
    except content.ContentError as refused:
        return render_page_form(request, user, page, page, status_code=400, error=str(refused))
    flash(request, done)
    return RedirectResponse(request.app.url_path_for("page", page_id=page.id), status_code=303)


@router.post("/{page_id}/publish", name="publish_page")
def publish_page(request: Request, page: Page = Depends(existing_page),
                 user: User = Depends(signed_in_user),
                 conn: sqlite3.Connection = Depends(get_db)):
    return take_action(request, user, page, content.PUBLISH_PAGE, conn,
                       "Página publicada. Aparecerá en el menú del sitio público después de la"
                       " próxima actualización del sitio.")


@router.post("/{page_id}/unpublish", name="unpublish_page")
def unpublish_page(request: Request, page: Page = Depends(existing_page),
                   user: User = Depends(signed_in_user),
                   conn: sqlite3.Connection = Depends(get_db)):
    return take_action(request, user, page, content.UNPUBLISH_PAGE, conn,
                       "La página volvió a ser borrador. Desaparecerá del sitio público con la"
                       " próxima actualización del sitio.")


@router.get("/{page_id}/delete", name="confirm_delete_page")
def confirm_delete_page(request: Request, page: Page = Depends(existing_page),
                        user: User = Depends(signed_in_user)):
    return render(request, "admin/page_delete.html", user, page=page)


@router.post("/{page_id}/delete", name="delete_page")
def delete_page(request: Request, page: Page = Depends(existing_page),
                conn: sqlite3.Connection = Depends(get_db)):
    content.delete_page(conn, page)
    flash(request, "Página borrada.")
    return RedirectResponse(f"{request.app.url_path_for('content')}?type=page", status_code=303)
