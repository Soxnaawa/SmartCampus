#!/usr/bin/env python3
"""
SmartCampus — Tests de Sécurité (M3)
=====================================
Suite de tests automatisés validant les mécanismes de sécurité.
Compatible pytest et exécution directe.

Couverture :
  - AES-256-GCM : chiffrement, déchiffrement, falsification
  - PKI         : génération de certificats, vérification de signature
  - Anti-replay : nonce unique, fenêtre temporelle, HMAC
  - Audit       : détection de patterns vulnérables

Auteur: P4 — Cybersécurité
"""

import sys
import os
import time
import json
import tempfile
import hmac as hmac_lib
import hashlib
import secrets
from pathlib import Path

# Ajouter les modules P4 au path
sys.path.insert(0, str(Path(__file__).parent.parent / "crypto"))
sys.path.insert(0, str(Path(__file__).parent.parent / "attacks" / "replay"))
sys.path.insert(0, str(Path(__file__).parent.parent / "audit"))

from aes_gcm import (
    derive_key, encrypt, decrypt, encrypt_card_data, decrypt_card_data,
    sign_challenge, verify_challenge, KEY_SIZE
)
from replay_demo import (
    NonceRegistry, generate_legitimate_scan, process_scan,
    TransactionResult, verify_hmac, TERMINAL_SECRET
)
from cryptography.exceptions import InvalidTag


# ─── Helpers ──────────────────────────────────────────────────────────────────

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name):
        self.passed += 1
        print(f"  ✅ PASS : {name}")

    def fail(self, name, reason):
        self.failed += 1
        self.errors.append(f"{name}: {reason}")
        print(f"  ❌ FAIL : {name} — {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*55}")
        print(f"  Tests : {self.passed}/{total} passés")
        if self.errors:
            print("  Échecs :")
            for e in self.errors:
                print(f"    - {e}")
        print(f"{'='*55}")
        return self.failed == 0


R = TestResult()


# ─── Tests AES-256-GCM ────────────────────────────────────────────────────────

def test_aes_key_derivation():
    key, salt = derive_key("TestPassphrase!")
    assert len(key) == KEY_SIZE
    # Redériver avec même passphrase + salt → même clé
    key2, _ = derive_key("TestPassphrase!", salt)
    assert key == key2
    # Passphrase différente → clé différente
    key3, _ = derive_key("AutrePassphrase!", salt)
    assert key != key3
    R.ok("AES: dérivation de clé PBKDF2 cohérente")


def test_aes_encrypt_decrypt_roundtrip():
    key, _ = derive_key("SmartCampus2025!")
    plaintext = b"Donnees sensibles etudiant SC-2025-00147"
    ciphertext = encrypt(plaintext, key)
    assert ciphertext != plaintext
    recovered = decrypt(ciphertext, key)
    assert recovered == plaintext
    R.ok("AES-GCM: chiffrement/déchiffrement roundtrip")


def test_aes_nonce_uniqueness():
    """Deux chiffrements du même plaintext → nonces différents."""
    key, _ = derive_key("NonceTest!")
    msg = b"meme message"
    c1 = encrypt(msg, key)
    c2 = encrypt(msg, key)
    assert c1[:12] != c2[:12], "Nonces identiques — vulnérabilité !"
    assert c1 != c2
    R.ok("AES-GCM: nonces uniques par chiffrement")


def test_aes_tamper_detection():
    """Modification d'un byte du ciphertext → InvalidTag."""
    key, _ = derive_key("TamperTest!")
    blob = bytearray(encrypt(b"donnees carte", key))
    blob[15] ^= 0xFF   # corrompre un byte du ciphertext
    try:
        decrypt(bytes(blob), key)
        R.fail("AES-GCM: détection de falsification", "InvalidTag non levée")
    except InvalidTag:
        R.ok("AES-GCM: falsification détectée (InvalidTag)")


def test_aes_aad_binding():
    """AAD différent → déchiffrement impossible."""
    key, _ = derive_key("AADTest!")
    blob = encrypt(b"payload", key, aad=b"card-uid-001")
    try:
        decrypt(blob, key, aad=b"card-uid-EVIL")
        R.fail("AES-GCM: liaison AAD", "AAD différent accepté")
    except InvalidTag:
        R.ok("AES-GCM: AAD lie le ciphertext à son contexte")


def test_card_data_encrypt_decrypt():
    key, _ = derive_key("CardDataTest!")
    card = {
        "uid":       "SC-2025-00147",
        "prenom":    "Ousmane",
        "nom":       "Diop",
        "matricule": "ESP-2025-001",
        "filiere":   "DIC2/M1-SSI",
        "solde":     15000,
        "statut":    "actif",
        "emis_le":   "2025-09-01",
        "expire_le": "2026-08-31",
    }
    enc_json = encrypt_card_data(card, key)
    dec = decrypt_card_data(enc_json, key)
    assert dec["prenom"] == "Ousmane"
    assert dec["nom"]    == "Diop"
    assert dec["uid"]    == "SC-2025-00147"  # uid non chiffré
    # Champs chiffrés dans JSON ne doivent pas contenir le plaintext
    raw = json.loads(enc_json)
    assert "Ousmane" not in raw["prenom"]
    R.ok("AES-GCM: chiffrement sélectif des données carte")


# ─── Tests Anti-Replay ────────────────────────────────────────────────────────

def test_nonce_first_use_accepted():
    reg   = NonceRegistry(ttl_seconds=60)
    nonce = secrets.token_hex(32)
    assert reg.consume(nonce) is True
    R.ok("Nonce: première utilisation acceptée")


def test_nonce_replay_rejected():
    reg   = NonceRegistry(ttl_seconds=60)
    nonce = secrets.token_hex(32)
    reg.consume(nonce)
    assert reg.consume(nonce) is False
    R.ok("Nonce: replay détecté et rejeté")


def test_legitimate_scan_accepted():
    reg  = NonceRegistry()
    scan = generate_legitimate_scan("SC-2025-00101", 60000, "RESTO-A1")
    status, _ = process_scan(scan.to_json(), reg)
    assert status == TransactionResult.OK
    R.ok("Anti-replay: scan légitime accepté")


def test_replay_scan_rejected():
    reg  = NonceRegistry()
    scan = generate_legitimate_scan("SC-2025-00101", 60000, "RESTO-A1")
    process_scan(scan.to_json(), reg)   # premier passage
    status, msg = process_scan(scan.to_json(), reg)   # replay
    assert status == TransactionResult.REPLAY
    R.ok("Anti-replay: replay rejeté")


def test_expired_timestamp_rejected():
    reg  = NonceRegistry()
    scan = generate_legitimate_scan("SC-2025-00102", 20000, "PHOTO-B2")
    data = json.loads(scan.to_json())
    data["timestamp"] -= 60_000   # 60s dans le passé
    msg  = f"{data['uid']}|{data['timestamp']}|{data['nonce']}".encode()
    data["signature"] = hmac_lib.new(TERMINAL_SECRET, msg, hashlib.sha256).hexdigest()
    status, _ = process_scan(json.dumps(data), reg)
    assert status == TransactionResult.EXPIRED
    R.ok("Anti-replay: timestamp expiré rejeté")


def test_forged_hmac_rejected():
    reg  = NonceRegistry()
    scan = generate_legitimate_scan("SC-2025-00103", 50000, "RESTO-A1")
    data = json.loads(scan.to_json())
    data["signature"] = "00" * 32   # signature aléatoire
    status, _ = process_scan(json.dumps(data), reg)
    assert status == TransactionResult.HMAC
    R.ok("Anti-replay: HMAC forgé rejeté")


# ─── Tests PKI (signatures RSA) ───────────────────────────────────────────────

def test_rsa_sign_verify():
    """Génère une paire RSA et valide signature sur un nonce."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PublicFormat, PrivateFormat, NoEncryption
    )
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    pub_pem  = key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)

    nonce = secrets.token_hex(32)
    sig   = sign_challenge(nonce, priv_pem)
    assert verify_challenge(nonce, sig, pub_pem) is True
    R.ok("PKI: signature RSA-PSS vérifiée")


def test_rsa_invalid_signature_rejected():
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PublicFormat, PrivateFormat, NoEncryption
    )
    key     = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub_pem = key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    nonce   = secrets.token_hex(32)
    assert verify_challenge(nonce, "AAAA" * 64, pub_pem) is False
    R.ok("PKI: signature invalide rejetée")


def test_rsa_wrong_key_rejected():
    """Signature avec clé A, vérification avec clé B → rejet."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PublicFormat, PrivateFormat, NoEncryption
    )
    key_a = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_b = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_a = key_a.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
    pub_b  = key_b.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    nonce  = secrets.token_hex(32)
    sig    = sign_challenge(nonce, priv_a)
    assert verify_challenge(nonce, sig, pub_b) is False
    R.ok("PKI: signature avec mauvaise clé rejetée")


# ─── Audit statique ───────────────────────────────────────────────────────────

def test_audit_detects_sql_injection():
    from security_audit import scan_file, RULES
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("cursor.execute('SELECT * FROM users WHERE id=%s' % user_id)\n")
        fname = f.name
    findings = scan_file(Path(fname), RULES)
    os.unlink(fname)
    sql_findings = [fi for fi in findings if fi.rule_id == "SEC-001"]
    assert len(sql_findings) > 0
    R.ok("Audit: SQL injection détectée (SEC-001)")


def test_audit_detects_hardcoded_secret():
    from security_audit import scan_file, RULES
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write('SECRET_KEY = "super_secret_password_123"\n')
        fname = f.name
    findings = scan_file(Path(fname), RULES)
    os.unlink(fname)
    sec_findings = [fi for fi in findings if fi.rule_id == "SEC-002"]
    assert len(sec_findings) > 0
    R.ok("Audit: secret hardcodé détecté (SEC-002)")


def test_audit_clean_code_passes():
    from security_audit import scan_file, RULES
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(
            "import os\n"
            "SECRET_KEY = os.environ.get('SECRET_KEY')\n"
            "cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))\n"
        )
        fname = f.name
    findings = scan_file(Path(fname), RULES)
    os.unlink(fname)
    critical = [fi for fi in findings if fi.severity == "CRITICAL"]
    assert len(critical) == 0
    R.ok("Audit: code propre sans findings CRITICAL")


# ─── Runner ───────────────────────────────────────────────────────────────────

def run_all():
    print("=" * 55)
    print("  SmartCampus — Security Test Suite")
    print("=" * 55)
    print()

    groups = [
        ("AES-256-GCM", [
            test_aes_key_derivation,
            test_aes_encrypt_decrypt_roundtrip,
            test_aes_nonce_uniqueness,
            test_aes_tamper_detection,
            test_aes_aad_binding,
            test_card_data_encrypt_decrypt,
        ]),
        ("Anti-Replay", [
            test_nonce_first_use_accepted,
            test_nonce_replay_rejected,
            test_legitimate_scan_accepted,
            test_replay_scan_rejected,
            test_expired_timestamp_rejected,
            test_forged_hmac_rejected,
        ]),
        ("PKI / RSA", [
            test_rsa_sign_verify,
            test_rsa_invalid_signature_rejected,
            test_rsa_wrong_key_rejected,
        ]),
        ("Audit statique", [
            test_audit_detects_sql_injection,
            test_audit_detects_hardcoded_secret,
            test_audit_clean_code_passes,
        ]),
    ]

    for group_name, tests in groups:
        print(f"\n▶ {group_name}")
        for t in tests:
            try:
                t()
            except AssertionError as e:
                R.fail(t.__name__, f"AssertionError: {e}")
            except Exception as e:
                R.fail(t.__name__, f"Exception: {type(e).__name__}: {e}")

    success = R.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    run_all()
