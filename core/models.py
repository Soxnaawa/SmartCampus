"""Modèles abstraits partagés par toutes les apps métier."""
import uuid

from django.db import models


class ModeleBase(models.Model):
    """Base commune : clé primaire UUID + date de création.

    Toutes les tables du projet utilisent un UUID comme clé primaire (exigence
    du cahier des charges §3) afin de ne pas exposer de compteurs séquentiels.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="Identifiant",
    )
    cree_le = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Créé le",
    )

    class Meta:
        abstract = True
        ordering = ["-cree_le"]
