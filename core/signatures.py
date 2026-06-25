"""
Vérification des signatures de carte (RSA + certificat X.509).

Chaque carte étudiante possède une paire de clés ; le backend stocke le
certificat X.509 (PEM) contenant la clé publique (`Etudiant.certificat_pub`).
Lors d'un scan, le terminal transmet une signature RSA du `nonce` ; on la
vérifie ici avec la clé publique extraite du certificat.

Le format de signature attendu : RSA PKCS#1 v1.5 + SHA-256 sur les octets du
nonce interprété comme une chaîne hexadécimale (le nonce est échangé en hex).
La signature elle-même est transmise encodée en base64.

Ce module fournit aussi de quoi générer des paires de clés / certificats de
test (utilisé par la commande `seed_data`), afin que la chaîne complète soit
vérifiable de bout en bout.
"""
from __future__ import annotations

import base64
import datetime as dt

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID


# ---------------------------------------------------------------------------
# Vérification (côté backend, à chaque scan)
# ---------------------------------------------------------------------------
def _octets_nonce(nonce_hex: str) -> bytes:
    """Convertit le nonce (chaîne hex) en octets signés/vérifiés.

    On signe les octets binaires du nonce et non sa représentation texte, ce
    qui est le comportement standard côté carte.
    """
    try:
        return bytes.fromhex(nonce_hex)
    except ValueError as exc:
        raise ValueError("Nonce non hexadécimal.") from exc


def cle_publique_depuis_certificat(certificat_pem: str):
    """Extrait la clé publique RSA d'un certificat X.509 au format PEM."""
    cert = x509.load_pem_x509_certificate(certificat_pem.encode("utf-8"))
    return cert.public_key()


def verifier_signature_nonce(
    certificat_pem: str, nonce_hex: str, signature_b64: str
) -> bool:
    """Vérifie la signature RSA d'un nonce avec la clé publique du certificat.

    Renvoie True si la signature est valide, False sinon (jamais d'exception
    pour une signature simplement invalide : on logge et on refuse en amont).
    """
    try:
        cle_pub = cle_publique_depuis_certificat(certificat_pem)
        signature = base64.b64decode(signature_b64)
        cle_pub.verify(
            signature,
            _octets_nonce(nonce_hex),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception:
        # Toute erreur (signature invalide, certificat illisible, mauvais
        # padding...) = vérification échouée. Le détail n'est pas propagé pour
        # éviter de divulguer la cause exacte à l'appelant.
        return False


# ---------------------------------------------------------------------------
# Génération de matériel cryptographique de TEST (cartes simulées)
# ---------------------------------------------------------------------------
def generer_paire_et_certificat(uid_carte: str):
    """Génère, pour une carte simulée, une clé privée RSA et un certificat
    X.509 auto-signé contenant la clé publique.

    Retourne un tuple ``(cle_privee_pem, certificat_pem)`` (deux str).
    Utilisé uniquement par `seed_data` / les tests : en production réelle, la
    carte génère sa clé et l'AC signe le certificat.
    """
    cle_privee = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    sujet = emetteur = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "SN"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Smart Campus"),
            x509.NameAttribute(NameOID.COMMON_NAME, uid_carte),
        ]
    )

    maintenant = dt.datetime.now(dt.timezone.utc)
    certificat = (
        x509.CertificateBuilder()
        .subject_name(sujet)
        .issuer_name(emetteur)
        .public_key(cle_privee.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(maintenant - dt.timedelta(days=1))
        .not_valid_after(maintenant + dt.timedelta(days=3650))
        .sign(cle_privee, hashes.SHA256())
    )

    cle_privee_pem = cle_privee.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    certificat_pem = certificat.public_bytes(serialization.Encoding.PEM).decode(
        "utf-8"
    )
    return cle_privee_pem, certificat_pem


def signer_nonce(cle_privee_pem: str, nonce_hex: str) -> str:
    """Signe un nonce avec une clé privée PEM et renvoie la signature base64.

    Symétrique de `verifier_signature_nonce` : utilisé par les tests et par le
    simulateur de scan pour produire des messages valides.
    """
    cle_privee = serialization.load_pem_private_key(
        cle_privee_pem.encode("utf-8"), password=None
    )
    signature = cle_privee.sign(
        _octets_nonce(nonce_hex),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")
