"""Markdown rendering: Markdown text in, sanitized HTML out.

Used by Vista previa (and later by the review screens and the site export), so
the preview is always exactly what readers get.
"""
from __future__ import annotations

import nh3
from markdown_it import MarkdownIt

_markdown = MarkdownIt("commonmark")

# Text formatting, lists, blockquotes, code and links. Everything else goes,
# images included: posts carry no photos.
_TAGS = {"p", "br", "hr", "strong", "em", "del", "s", "h1", "h2", "h3", "h4", "h5", "h6",
         "ul", "ol", "li", "blockquote", "code", "pre", "a"}
_ATTRIBUTES = {"a": {"href", "title"}, "ol": {"start"}}
# Links keep only full addresses. Relative ones ("/admin", "//elsewhere") would
# point somewhere else on the public site, and published HTML has no root paths.
_URL_SCHEMES = {"http", "https", "mailto"}


def to_html(text: str) -> str:
    return nh3.clean(_markdown.render(text), tags=_TAGS, attributes=_ATTRIBUTES,
                     url_schemes=_URL_SCHEMES, url_relative="deny",
                     link_rel="noopener noreferrer")
