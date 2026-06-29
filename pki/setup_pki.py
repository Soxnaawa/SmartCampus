#!/usr/bin/env python3
"""
SmartCampus — PKI Setup (M3 Cybersécurité)
==========================================
Génère la hiérarchie PKI complète :
  Root CA → Intermediate CA → Cartes étudiantes

Usage:
    python3 setup_pki.py [--cards N]

Auteur: P4 — Cybersécurité
"""

import os
import json
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

# ─── Répertoires ──────────────────────────────────────────────────────────────
BASE  = Path(__file__).parent
CA    = BASE / "root-ca"
CARDS = BASE / "cards"
CERTS = BASE / "certs"
CRL   = BASE / "crl"

for d in [CA, CARDS, CERTS, CRL]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def gen_key(bits: int = 2048) -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=bits)

def save_key(key, path: Path, password: bytes | None = None):
    enc = (
        serialization.BestAvailableEncryption(password)
        if password else NoEncryption()
    )
    path.write_bytes(
        key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, enc)
    )

def save_cert(cert, path: Path):
    path.write_bytes(cert.public_bytes(Encoding.PEM))

def load_key(path: Path) -> rsa.RSAPrivateKey:
    return serialization.load_pem_private_key(path.read_bytes(), password=None)

def load_cert(path: Path) -> x509.Certificate:
    return x509.load_pem_x509_certificate(path.read_bytes())

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

# ─── 1. Root CA ───────────────────────────────────────────────────────────────

def create_root_ca() -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
    print("[PKI] Génération Root CA (4096 bits)...")
    key  = gen_key(4096)
    name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME,             "SN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME,   "Dakar"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME,        "ESP/UCAD SmartCampus"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "PKI Root Authority"),
        x509.NameAttribute(NameOID.COMMON_NAME,              "SmartCampus Root CA"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now_utc())
        .not_valid_after(now_utc() + timedelta(days=3650))   # 10 ans
        .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
        .add_extension(x509.KeyUsage(
            digital_signature=True, key_cert_sign=True, crl_sign=True,
            content_commitment=False, key_encipherment=False,
            data_encipherment=False, key_agreement=False,
            encipher_only=False, decipher_only=False
        ), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .sign(key, hashes.SHA256())
    )
    save_key(key=key, path=CA / "root-ca.key")   # type: ignore
    save_cert(cert, CA / "root-ca.crt")
    print(f"    ✓ Root CA : {CA / 'root-ca.crt'}")
    return key, cert

# ─── 2. Certificat carte étudiant ─────────────────────────────────────────────

def create_card_cert(
    uid: str,
    student_name: str,
    filiere: str,
    root_key: rsa.RSAPrivateKey,
    root_cert: x509.Certificate,
) -> dict:
    """Génère clé + certificat X.509 pour une carte étudiant."""
    key  = gen_key(2048)
    name = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME,             "SN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME,        "ESP/UCAD SmartCampus"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, filiere),
        x509.NameAttribute(NameOID.COMMON_NAME,              f"Card:{uid}"),
        x509.NameAttribute(NameOID.PSEUDONYM,                student_name),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(root_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now_utc())
        .not_valid_after(now_utc() + timedelta(days=365))    # 1 an
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(
            digital_signature=True, content_commitment=True,
            key_encipherment=False, data_encipherment=False,
            key_agreement=False, key_cert_sign=False, crl_sign=False,
            encipher_only=False, decipher_only=False
        ), critical=True)
        .add_extension(x509.ExtendedKeyUsage([
            ExtendedKeyUsageOID.CLIENT_AUTH,
        ]), critical=False)
        .add_extension(
            x509.SubjectAlternativeName([x509.RFC822Name(f"{uid}@smartcampus.esp.sn")]),
            critical=False
        )
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(root_key.public_key()), critical=False)
        .sign(root_key, hashes.SHA256())
    )

    # Sauvegarde PEM
    key_path  = CARDS / f"{uid}.key"
    cert_path = CARDS / f"{uid}.crt"
    save_key(key=key, path=key_path)
    save_cert(cert, cert_path)

    # Fingerprint SHA-256
    fp = cert.fingerprint(hashes.SHA256()).hex()

    return {
        "uid":         uid,
        "student":     student_name,
        "filiere":     filiere,
        "serial":      str(cert.serial_number),
        "fingerprint": fp,
        "not_after":   cert.not_valid_after_utc.isoformat(),
        "key_file":    str(key_path),
        "cert_file":   str(cert_path),
    }

# ─── 3. Jeu d'étudiants fictifs ───────────────────────────────────────────────

STUDENTS = [
    ("SC-2025-00101", "Amadou Diallo",      "DIC2/M1-SSI"),
    ("SC-2025-00102", "Fatou Mbaye",         "DIC2/M1-SSI"),
    ("SC-2025-00103", "Ibrahima Sow",        "DIC2/M1-GL"),
    ("SC-2025-00104", "Mariama Diop",        "DIC2/M1-SSI"),
    ("SC-2025-00105", "Ousmane Ba",          "DIC2/M1-GL"),
    ("SC-2025-00106", "Aissatou Ndiaye",     "DIC2/M1-SSI"),
    ("SC-2025-00107", "Moussa Sarr",         "DIC2/M1-RI"),
    ("SC-2025-00108", "Rokhaya Fall",        "DIC2/M1-SSI"),
    ("SC-2025-00109", "Cheikh Gueye",        "DIC2/M1-GL"),
    ("SC-2025-00110", "Ndéye Diagne",        "DIC2/M1-SSI"),
    ("SC-2025-00111", "Pape Thiaw",          "DIC2/M1-RI"),
    ("SC-2025-00112", "Astou Niang",         "DIC2/M1-SSI"),
    ("SC-2025-00113", "Aliou Traoré",        "DIC2/M1-GL"),
    ("SC-2025-00114", "Khadija Coulibaly",   "DIC2/M1-SSI"),
    ("SC-2025-00115", "Mamadou Konaté",      "DIC2/M1-RI"),
    ("SC-2025-00116", "Bineta Diouf",        "DIC2/M1-SSI"),
    ("SC-2025-00117", "Seydou Camara",       "DIC2/M1-GL"),
    ("SC-2025-00118", "Aminata Sy",          "DIC2/M1-SSI"),
    ("SC-2025-00119", "Landing Badji",       "DIC2/M1-RI"),
    ("SC-2025-00120", "Sokhna Thiam",        "DIC2/M1-SSI"),
]

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SmartCampus PKI Setup")
    parser.add_argument("--cards", type=int, default=20, help="Nombre de cartes à générer")
    args = parser.parse_args()

    print("=" * 60)
    print("  SmartCampus — PKI Initialization")
    print("=" * 60)

    # Root CA
    root_key, root_cert = create_root_ca()

    # Cartes étudiantes
    print(f"\n[PKI] Génération de {min(args.cards, len(STUDENTS))} certificats cartes...")
    registry = []
    for uid, name, filiere in STUDENTS[:args.cards]:
        info = create_card_cert(uid, name, filiere, root_key, root_cert)
        registry.append(info)
        print(f"    ✓ {uid} — {name} ({filiere})")

    # Registre JSON
    reg_path = CERTS / "card_registry.json"
    reg_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False))
    print(f"\n[PKI] Registre sauvegardé : {reg_path}")

    # Bundle CA public
    bundle = CA / "smartcampus-ca-bundle.crt"
    bundle.write_bytes(root_cert.public_bytes(Encoding.PEM))
    print(f"[PKI] Bundle CA public    : {bundle}")

    print("\n[PKI] ✅ Infrastructure PKI opérationnelle.\n")

if __name__ == "__main__":
    main()
