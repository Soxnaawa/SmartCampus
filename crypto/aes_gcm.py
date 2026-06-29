#!/usr/bin/env python3
"""
SmartCampus — Module Cryptographie (M3)
========================================
Chiffrement AES-256-GCM des données carte et au repos.

Principes:
  - AES-256-GCM : chiffrement authentifié (confidentialité + intégrité)
  - Nonce 96 bits aléatoire par opération (jamais réutilisé)
  - PBKDF2-SHA256 pour dériver la clé depuis une passphrase
  - Format wire : nonce(12) | tag(16) | ciphertext

Auteur: P4 — Cybersécurité
"""

import os
import json
import base64
import hashlib
import secrets
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from cryptography.exceptions import InvalidTag

# ─── Constantes ───────────────────────────────────────────────────────────────
NONCE_SIZE  = 12     # 96 bits — standard GCM
KEY_SIZE    = 32     # 256 bits
KDF_ITERS   = 480_000  # OWASP 2024 recommandation PBKDF2-SHA256
KDF_SALT_SIZE = 32


# ─── Dérivation de clé ────────────────────────────────────────────────────────

def derive_key(passphrase: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """
    Dérive une clé AES-256 depuis une passphrase.
    Retourne (key, salt) — sauvegarder le salt pour pouvoir redériver.
    """
    if salt is None:
        salt = os.urandom(KDF_SALT_SIZE)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=KDF_ITERS,
    )
    key = kdf.derive(passphrase.encode("utf-8"))
    return key, salt


# ─── Chiffrement / Déchiffrement AES-256-GCM ──────────────────────────────────

def encrypt(plaintext: bytes, key: bytes, aad: bytes | None = None) -> bytes:
    """
    Chiffre `plaintext` avec AES-256-GCM.
    `aad` = Additional Authenticated Data (ex: UID carte) — intégré
    dans le tag sans être chiffré.
    Retourne : nonce(12) || ciphertext+tag
    """
    if len(key) != KEY_SIZE:
        raise ValueError(f"Clé AES invalide : attendu {KEY_SIZE} octets, reçu {len(key)}")
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, aad)
    return nonce + ciphertext


def decrypt(blob: bytes, key: bytes, aad: bytes | None = None) -> bytes:
    """
    Déchiffre un blob produit par `encrypt`.
    Lève cryptography.exceptions.InvalidTag si le MAC échoue.
    """
    if len(blob) < NONCE_SIZE + 16:
        raise ValueError("Blob trop court — données corrompues.")
    nonce      = blob[:NONCE_SIZE]
    ciphertext = blob[NONCE_SIZE:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, aad)


# ─── Chiffrement JSON carte ────────────────────────────────────────────────────

def encrypt_card_data(card: dict, key: bytes) -> str:
    """
    Chiffre les champs sensibles d'une carte étudiant.
    Le champ `uid` sert d'AAD (lié au ciphertext mais visible).
    Retourne un dict JSON sérialisé avec champs chiffrés en base64.
    """
    uid   = card["uid"].encode()
    sensitive_fields = ["prenom", "nom", "matricule", "filiere"]
    encrypted = {"uid": card["uid"], "solde": card.get("solde", 0),
                 "statut": card.get("statut", "actif"),
                 "emis_le": card.get("emis_le", ""),
                 "expire_le": card.get("expire_le", "")}
    for field in sensitive_fields:
        if field in card:
            blob = encrypt(card[field].encode("utf-8"), key, aad=uid)
            encrypted[field] = base64.b64encode(blob).decode("ascii")
    return json.dumps(encrypted, ensure_ascii=False, indent=2)


def decrypt_card_data(encrypted_json: str, key: bytes) -> dict:
    """Inverse de encrypt_card_data."""
    card = json.loads(encrypted_json)
    uid  = card["uid"].encode()
    sensitive_fields = ["prenom", "nom", "matricule", "filiere"]
    decrypted = dict(card)
    for field in sensitive_fields:
        if field in card:
            blob = base64.b64decode(card[field])
            decrypted[field] = decrypt(blob, key, aad=uid).decode("utf-8")
    return decrypted


# ─── Signature RSA (anti-replay) ──────────────────────────────────────────────

def sign_challenge(nonce_hex: str, private_key_pem: bytes) -> str:
    """
    Signe un challenge nonce avec la clé privée RSA de la carte.
    Retourne la signature en base64 (étape 2 du protocole §4.3).
    """
    private_key = load_pem_private_key(private_key_pem, password=None)
    signature   = private_key.sign(
        bytes.fromhex(nonce_hex),
        asym_padding.PSS(
            mgf=asym_padding.MGF1(hashes.SHA256()),
            salt_length=asym_padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")


def verify_challenge(nonce_hex: str, signature_b64: str, public_key_pem: bytes) -> bool:
    """
    Vérifie la signature du challenge.
    Retourne True si valide, False sinon (étape 3 du protocole §4.3).
    """
    try:
        public_key = load_pem_public_key(public_key_pem)
        public_key.verify(
            base64.b64decode(signature_b64),
            bytes.fromhex(nonce_hex),
            asym_padding.PSS(
                mgf=asym_padding.MGF1(hashes.SHA256()),
                salt_length=asym_padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


# ─── Demo ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  SmartCampus — Crypto Module Demo")
    print("=" * 55)

    # 1. Dérivation de clé
    passphrase = "SmartCampus@ESP2025!"
    key, salt  = derive_key(passphrase)
    print(f"\n[KEY]  Clé AES-256 dérivée (PBKDF2-SHA256 × {KDF_ITERS:,})")
    print(f"       Salt : {salt.hex()[:32]}...")

    # 2. Chiffrement carte
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
    encrypted_json = encrypt_card_data(card, key)
    print(f"\n[CARD] Données carte chiffrées :")
    print(encrypted_json)

    # 3. Déchiffrement
    decrypted = decrypt_card_data(encrypted_json, key)
    assert decrypted["prenom"] == "Ousmane", "ERREUR déchiffrement"
    print(f"\n[CARD] ✓ Déchiffrement correct : {decrypted['prenom']} {decrypted['nom']}")

    # 4. Test tamper detection (GCM tag)
    import json as _json
    tampered = _json.loads(encrypted_json)
    # Modifier un seul byte du ciphertext
    blob = bytearray(base64.b64decode(tampered["prenom"]))
    blob[15] ^= 0xFF
    tampered["prenom"] = base64.b64encode(bytes(blob)).decode()
    try:
        decrypt_card_data(_json.dumps(tampered), key)
        print("[TAMPER] ✗ Falsification non détectée !")
    except InvalidTag:
        print("[TAMPER] ✓ Falsification détectée par GCM tag — données rejetées")

    print("\n✅ Module cryptographique opérationnel.\n")
