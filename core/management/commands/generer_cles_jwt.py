"""
Génère une paire de clés RSA pour signer les JWT en RS256.

Usage :
    python manage.py generer_cles_jwt --dossier certs/

Puis renseigner dans `.env` :
    JWT_ALGORITHM=RS256
    JWT_SIGNING_KEY_PATH=certs/jwt_private.pem
    JWT_VERIFYING_KEY_PATH=certs/jwt_public.pem
"""
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Génère une paire de clés RSA (PEM) pour les JWT RS256."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dossier",
            default="certs",
            help="Dossier de sortie des clés (défaut: certs/).",
        )

    def handle(self, *args, **options):
        dossier = Path(options["dossier"])
        dossier.mkdir(parents=True, exist_ok=True)

        cle = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        chemin_prive = dossier / "jwt_private.pem"
        chemin_public = dossier / "jwt_public.pem"

        chemin_prive.write_bytes(
            cle.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        chemin_public.write_bytes(
            cle.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Clés générées :\n  - {chemin_prive}\n  - {chemin_public}"
            )
        )
