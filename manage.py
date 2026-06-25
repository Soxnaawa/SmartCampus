#!/usr/bin/env python
"""Utilitaire en ligne de commande de Django pour le projet Smart Campus."""
import os
import sys


def main():
    # Le paquet de configuration du projet s'appelle `core` (voir §4 du cahier
    # des charges : core héberge settings, urls racine, utils chiffrement...).
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django ne semble pas installé. Activez votre environnement "
            "virtuel et lancez `pip install -r requirements.txt`."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
