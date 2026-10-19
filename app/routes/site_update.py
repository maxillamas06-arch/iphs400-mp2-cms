"""The site update (leader only): the Actualizar el sitio button. Every route here is
named in `policy.LEADER_ONLY_ROUTES`."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app import site_update
from app.web import flash, get_db, signed_in_user

router = APIRouter(prefix="/admin/site-update", dependencies=[Depends(signed_in_user)])


@router.post("", name="update_site")
def update_site(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    try:
        site_update.update(conn, request.app.state.site, request.app.state.upload)
    except site_update.ExportFailed:
        flash(request, "No se pudo generar el sitio ✗, así que no se subió nada. Los lectores"
                       " siguen viendo la versión anterior. Vuelve a presionar Actualizar el"
                       " sitio; si sigue fallando, pide ayuda con la carpeta del sitio.",
              failed=True)
    except site_update.UploadFailed:
        flash(request, "Sitio generado ✓ · No se pudo subir a GitHub ✗. Los lectores siguen"
                       " viendo la versión anterior. Revisa que la computadora tenga internet"
                       " y vuelve a presionar Actualizar el sitio.", failed=True)
    else:
        flash(request, "Sitio generado ✓ · Subido a GitHub ✓. Los lectores verán los cambios"
                       " en unos minutos.")
    return RedirectResponse(request.app.url_path_for("dashboard"), status_code=303)
