"""
Chiffrement des données personnelles au repos (AES-256-GCM).

Principe :
- une clé symétrique de 32 octets (256 bits) est lue depuis l'environnement
  (`CHAMP_CHIFFREMENT_CLE`, en base64 urlsafe) ;
- chaque valeur est chiffrée avec un nonce aléatoire de 12 octets ;
- le format stocké en base est : base64( version(1o) || nonce(12o) || cipher+tag ).

AES-GCM est authentifié : toute altération du texte chiffré est détectée au
déchiffrement (exception levée). On peut donc stocker le blob en clair dans une
colonne `text` sans craindre une falsification silencieuse.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger("smartcampus.securite")

# Préfixe de version : permet de faire évoluer le format/la rotation de clé.
_VERSION = b"\x01"
_TAILLE_NONCE = 12  # 96 bits, recommandé pour AES-GCM
_TAILLE_CLE = 32    # 256 bits


def _charger_cle() -> bytes:
    """Retourne la clé AES-256 (32 octets).

    Ordre de résolution :
    1. variable d'environnement `CHAMP_CHIFFREMENT_CLE` (base64 de 32 octets) ;
    2. à défaut, dérivation SHA-256 de `SECRET_KEY` — **uniquement acceptable en
       développement**, un avertissement est émis.
    """
    brute = getattr(settings, "CHAMP_CHIFFREMENT_CLE", "") or ""
    if brute:
        try:
            cle = base64.urlsafe_b64decode(brute)
        except (ValueError, TypeError) as exc:
            raise ImproperlyConfigured(
                "CHAMP_CHIFFREMENT_CLE n'est pas un base64 valide."
            ) from exc
        if len(cle) != _TAILLE_CLE:
            raise ImproperlyConfigured(
                "CHAMP_CHIFFREMENT_CLE doit décoder vers exactement 32 octets "
                f"(actuellement {len(cle)})."
            )
        return cle

    # Repli développement : clé dérivée de SECRET_KEY.
    logger.warning(
        "CHAMP_CHIFFREMENT_CLE absente : dérivation de la clé depuis SECRET_KEY "
        "(NE PAS utiliser en production)."
    )
    return hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()


def generer_cle_base64() -> str:
    """Génère une nouvelle clé AES-256 prête à coller dans `.env`."""
    return base64.urlsafe_b64encode(os.urandom(_TAILLE_CLE)).decode("ascii")


def chiffrer(texte_clair: str | None) -> str | None:
    """Chiffre une chaîne et renvoie le blob base64 à stocker en base.

    `None` est conservé tel quel (champ vide). Une chaîne vide est chiffrée
    normalement (le résultat reste déchiffrable vers "").
    """
    if texte_clair is None:
        return None
    aes = AESGCM(_charger_cle())
    nonce = os.urandom(_TAILLE_NONCE)
    chiffre = aes.encrypt(nonce, texte_clair.encode("utf-8"), None)
    blob = _VERSION + nonce + chiffre
    return base64.urlsafe_b64encode(blob).decode("ascii")


def dechiffrer(blob_base64: str | None) -> str | None:
    """Déchiffre un blob produit par `chiffrer`.

    Renvoie `None` si l'entrée est `None`. Lève `ValueError` si le contenu est
    corrompu, tronqué ou chiffré avec une autre clé (intégrité GCM invalide).
    """
    if blob_base64 is None:
        return None
    try:
        blob = base64.urlsafe_b64decode(blob_base64)
    except (ValueError, TypeError) as exc:
        raise ValueError("Donnée chiffrée illisible (base64 invalide).") from exc

    if len(blob) < 1 + _TAILLE_NONCE + 16:  # version + nonce + tag minimal
        raise ValueError("Donnée chiffrée tronquée.")

    version, reste = blob[:1], blob[1:]
    if version != _VERSION:
        raise ValueError(f"Version de chiffrement non supportée : {version!r}.")

    nonce, chiffre = reste[:_TAILLE_NONCE], reste[_TAILLE_NONCE:]
    aes = AESGCM(_charger_cle())
    try:
        clair = aes.decrypt(nonce, chiffre, None)
    except InvalidTag as exc:
        raise ValueError(
            "Échec de déchiffrement : donnée altérée ou clé incorrecte."
        ) from exc
    return clair.decode("utf-8")
