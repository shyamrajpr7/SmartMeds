"""Database-backed storage for prescription attachments.

Serverless filesystems are ephemeral, so uploaded prescription files are kept
in the database and served through an authenticated view.
"""

import mimetypes

from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.urls import reverse
from django.utils.deconstruct import deconstructible

from .models import StoredMedia


@deconstructible
class DatabaseStorage(Storage):
    """Store files in the database so they survive redeploys."""

    def _save(self, name, content):
        content.seek(0)
        data = content.read()
        content_type = getattr(content, "content_type", None)
        if not content_type:
            content_type = (
                mimetypes.guess_type(name)[0] or "application/octet-stream"
            )
        StoredMedia.objects.create(
            name=name,
            content_type=content_type,
            size=len(data),
            data=data,
        )
        return name

    def _open(self, name, mode="rb"):
        media = StoredMedia.objects.get(name=name)
        return ContentFile(media.data, name=name)

    def exists(self, name):
        return StoredMedia.objects.filter(name=name).exists()

    def delete(self, name):
        StoredMedia.objects.filter(name=name).delete()

    def size(self, name):
        return StoredMedia.objects.get(name=name).size

    def url(self, name):
        return reverse("prescriptions:media", kwargs={"name": name})
