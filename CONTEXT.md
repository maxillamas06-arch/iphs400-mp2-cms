# Club de Aficionados Albiazul CMS

The site of an unofficial fan club of C.F. Monterrey (Rayados). Members write about the team; the leader checks everything before it goes public; other fans read it on a static public site.

## Language

### Names

**Club de Aficionados Albiazul**:
The fan club this site belongs to. Unofficial. In prose, "the fan club".
_Avoid_: The club (that is Rayados), peña, the Aficionados

**Rayados**:
C.F. Monterrey, the professional team the fan club supports. In prose, "Rayados" or "the team"; the full legal name "Club de Fútbol Monterrey" appears only in the disclaimer.
_Avoid_: The club, Monterrey (ambiguous with the city)

### People

**Leader**:
The one person who runs the fan club and its site. Checks every post before it goes public and manages who belongs. Holds the *admin* role.
_Avoid_: Owner, moderator, webmaster

**Member**:
A fan with an account who writes posts. Cannot publish and cannot manage people. Holds the *editor* role.
_Avoid_: Contributor, author (as a role), user (when the role matters)

**Nickname** (*Apodo*):
The name readers see on a person's posts. Chosen once by that person at their first login; after that only the leader can change it. Unique, so no one can pass as someone else. Their real identity is known only to the leader.
_Avoid_: Display name, username, handle, alias

**Account** (*Cuenta*):
A leader's or member's way into the admin console: an email, a password, a role, a nickname, and whether it is active. Never deleted. *Mi cuenta* is where a person sees their own.
_Avoid_: User (in prose), profile, login

**Temporary password** (*Contraseña temporal*):
A password the leader sets on an account and hands over in person, for a new member or one who forgot theirs. The member can replace it on *Mi cuenta*.
_Avoid_: Default password, reset link

**Deactivate** (*Desactivar*):
The leader closing an account without deleting it: its person can no longer sign in, and their posts stay under their nickname. **Reactivate** (*Reactivar*) opens it again.
_Avoid_: Delete, ban, block, suspend

**Reader**:
Any fan visiting the public site. Has no account and cannot write.
_Avoid_: Visitor, user, subscriber

### Content

**Post** (*Publicación*):
A fan's opinion about the team, written by a member (or the leader) and filed under exactly one topic. In Spanish, *publicación* is always the thing, never the act: for the act say *publicar*.
_Avoid_: Article, story, news item, entry; "la publicación de …" to mean publishing

**Slug** (*Enlace*):
The end of a post's or page's web address, made from its title (`crónica-del-clásico-regio`). It can be changed until the post or page is first published, then never, so links shared on X or Facebook keep working. A page's slug can never be a name the site already uses for itself (the home page, the topic pages).
_Avoid_: URL, permalink, path

**Preview** (*Vista previa*):
A post's Markdown shown exactly as readers will see it, sanitized, without saving anything.
_Avoid_: Draft view, render

**Topic**:
The one fixed subject a post is filed under: **Match** (*Partido*), **Lineup** (*Alineación*), **Coach** (*Técnico*), **Signings** (*Fichajes*), or **Fan club news** (*Noticias del club de aficionados*). Readers see the Spanish names. The list is fixed; members cannot add topics.
_Avoid_: Category, tag, section, kind

**Page** (*Página*):
Fixed fan-club information shown in the public menu: *Quiénes somos*, *Próximos partidos*, *Reglas de la casa*, *Cómo unirse*. The fan club's own voice, not an opinion; only the leader writes pages, and they are never submitted. A page is a draft until the leader publishes it; unpublishing takes it back out of the menu at the next site update. Members never see pages in the admin console.
_Avoid_: Section, static page, menu item

**Menu order** (*Orden en el menú*):
The number the leader gives each page. The public menu lists *Inicio*, then the published pages from the lowest number up.
_Avoid_: Position, weight, rank

**Fan club news**:
The topic for the fan club's own announcements (watch parties, meetups), usually written by the leader. Never official news about Rayados.
_Avoid_: Club news (ambiguous), official news, announcements

**Disclaimer**:
The fixed line on every public page saying the site is a fan site not affiliated with Club de Fútbol Monterrey, in Spanish with the English line beneath.
_Avoid_: Legal notice, footer (the footer is where it sits, not what it is)

### Post lifecycle

**Draft** (*Borrador*):
A post its member is still writing. Never public.
_Avoid_: Unpublished (too broad), saved

**Submitted** (*Enviada*):
A post its member has finished and handed to the leader for checking. Never public. The dashboard counts these as *Esperando revisión* (waiting for review). With pending edits, they make up the leader's review queue.
_Avoid_: Pending, in review, ready

**Published** (*Publicada*):
A post the leader has approved. The only status that can appear on the public site.
_Avoid_: Live, approved, public

**Withdraw**:
A member pulling their submitted post back to draft to keep working on it.
_Avoid_: Cancel, unsubmit

**Send back** (*Devolver*):
The leader saying no: a submitted post returns to draft, or a pending edit is thrown away.
_Avoid_: Reject, decline

**Unpublish** (*Despublicar*):
The leader returning a published post to draft, taking it off the public site at the next site update. The slug stays locked.
_Avoid_: Archive, hide, retract

**Pending edit** (*Cambios propuestos*):
A member's proposed change to a published post (title, topic, body; never the slug), waiting for the leader. The published version stays public meanwhile; a post has at most one pending edit. The dashboard counts these as *Cambios propuestos*.
_Avoid_: Revision (that means history), draft (the post is still published)

**Approve** (*Aprobar*):
The leader accepting a pending edit, which replaces the published version. Readers then see *Actualizado el …* on the post, as they do after the leader edits a published post directly.
_Avoid_: Merge, accept, publish (publish is for submitted posts)

**Site update** (*Actualizar el sitio*):
The leader regenerating the public site from everything published and putting it online. Readers see nothing new until a site update; publishing alone changes nothing they can see.
_Avoid_: Publish (that is the status change), deploy, build, export

**Export**:
The first half of a site update: writing the public site's files from everything published, wiping what was there (`cms publish`). The second half puts those files online (`cms deploy`).
_Avoid_: Publish (that is the status change), build, render

### House rules

**House rules**:
The published line between tiradera and personal attack, used by the leader when checking posts and shown to readers on the *Reglas de la casa* page.
_Avoid_: Terms of service, code of conduct, guidelines

**Tiradera**:
Trash talk aimed at a rival club or its fans (e.g. Tigres). Allowed — it is part of being a fan.
_Avoid_: Banter (too mild), insult

**Personal attack**:
Aggression aimed at a real person, or a threat against a person or place. Never published, however it is phrased; catching it is the reason every post is checked.
_Avoid_: Tiradera (it is not one), offensive content
