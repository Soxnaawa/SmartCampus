#!/usr/bin/env python3
"""
SmartCampus — Démo Replay Attack + Contre-mesure Nonce (M3 §4.3)
=================================================================
Objectif pédagogique (Semaine 3) :
  1. ATTAQUE  : Capturer un scan MQTT valide et le rejouer → fraude
  2. DÉFENSE  : Le serveur maintient un cache de nonces utilisés
                → second envoi rejeté (HTTP 409 / MQTT error)

Structure :
  - ReplayAttackSimulator  : rejoue une transaction capturée
  - NonceRegistry          : registre serveur (in-memory + Redis-ready)
  - terminal_handler()     : point d'entrée backend simulé

Auteur: P4 — Cybersécurité
"""

import json
import time
import hmac
import hashlib
import secrets
import threading
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional

# ─── Modèles ──────────────────────────────────────────────────────────────────

@dataclass
class ScanEvent:
    """Message MQTT publié par un terminal (topic: campus/reader/scan)."""
    uid:       str
    timestamp: int          # epoch milliseconds
    nonce:     str          # 32 bytes hex = 64 chars
    signature: str          # HMAC-SHA256(uid|timestamp|nonce, secret) en hex
    amount:    int          # montant en FCFA × 100
    terminal:  str          # identifiant terminal

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, s: str) -> "ScanEvent":
        return cls(**json.loads(s))


# ─── Générateur de scan légitime ──────────────────────────────────────────────

TERMINAL_SECRET = b"terminal_hmac_secret_v1"   # clé partagée terminal ↔ backend

def generate_legitimate_scan(uid: str, amount: int, terminal: str) -> ScanEvent:
    """Simule un scan authentique d'un terminal autorisé."""
    nonce     = secrets.token_hex(32)
    timestamp = int(time.time() * 1000)
    # Signature HMAC : lie uid + timestamp + nonce → non forgeable sans la clé
    msg = f"{uid}|{timestamp}|{nonce}".encode()
    sig = hmac.new(TERMINAL_SECRET, msg, hashlib.sha256).hexdigest()
    return ScanEvent(uid=uid, timestamp=timestamp, nonce=nonce,
                     signature=sig, amount=amount, terminal=terminal)


def verify_hmac(event: ScanEvent) -> bool:
    """Vérifie la signature HMAC du scan."""
    msg      = f"{event.uid}|{event.timestamp}|{event.nonce}".encode()
    expected = hmac.new(TERMINAL_SECRET, msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(event.signature, expected)


# ─── Registre de nonces ───────────────────────────────────────────────────────

class NonceRegistry:
    """
    Cache des nonces déjà consommés.
    En production : Redis SETEX avec TTL = durée de validité de transaction.
    Ici : dict thread-safe en mémoire.
    """

    def __init__(self, ttl_seconds: int = 300):
        self._lock   = threading.Lock()
        self._store: dict[str, float] = {}   # nonce → expiry timestamp
        self._ttl    = ttl_seconds

    def consume(self, nonce: str) -> bool:
        """
        Tente de consommer un nonce.
        Retourne True si accepté (première utilisation), False si replay.
        """
        now = time.time()
        with self._lock:
            # Nettoyage lazy des nonces expirés
            expired = [k for k, exp in self._store.items() if exp < now]
            for k in expired:
                del self._store[k]

            if nonce in self._store:
                return False   # REPLAY DÉTECTÉ

            self._store[nonce] = now + self._ttl
            return True

    def size(self) -> int:
        with self._lock:
            return len(self._store)


# ─── Simulateur d'attaque ─────────────────────────────────────────────────────

class ReplayAttackSimulator:
    """
    Simule un attaquant qui capture un message MQTT valide et le rejoue.
    Scénario : attaquant passif sur le réseau WiFi du campus.
    """

    def __init__(self):
        self._captured: Optional[str] = None

    def capture(self, scan_json: str):
        """Capture (sniff) un message MQTT en clair."""
        self._captured = scan_json
        print(f"  [ATTAQUANT] 📡 Message capturé à t={time.time():.3f}")

    def replay(self, delay_seconds: float = 2.0) -> Optional[str]:
        """Rejoue le message capturé après un délai."""
        if self._captured is None:
            print("  [ATTAQUANT] Rien à rejouer.")
            return None
        time.sleep(delay_seconds)
        print(f"  [ATTAQUANT] 🔄 Replay à t={time.time():.3f} (délai {delay_seconds}s)")
        return self._captured


# ─── Backend simulé ───────────────────────────────────────────────────────────

class TransactionResult:
    OK      = "OK"
    REPLAY  = "REPLAY_DETECTED"
    HMAC    = "INVALID_SIGNATURE"
    EXPIRED = "TIMESTAMP_EXPIRED"
    INVALID = "INVALID_PAYLOAD"

MAX_TIMESTAMP_DRIFT_MS = 30_000   # 30 secondes

def process_scan(scan_json: str, nonce_registry: NonceRegistry) -> tuple[str, str]:
    """
    Traitement d'un scan par le backend.
    Retourne (status, message).
    """
    try:
        event = ScanEvent.from_json(scan_json)
    except Exception as e:
        return TransactionResult.INVALID, f"Payload invalide : {e}"

    now_ms = int(time.time() * 1000)

    # 1. Vérification horodatage (anti-replay temporel)
    drift = abs(now_ms - event.timestamp)
    if drift > MAX_TIMESTAMP_DRIFT_MS:
        return TransactionResult.EXPIRED, (
            f"Timestamp trop ancien/futur : drift={drift}ms > {MAX_TIMESTAMP_DRIFT_MS}ms"
        )

    # 2. Vérification HMAC
    if not verify_hmac(event):
        return TransactionResult.HMAC, "Signature HMAC invalide — transaction rejetée"

    # 3. Consommation du nonce (protection replay principale)
    if not nonce_registry.consume(event.nonce):
        return TransactionResult.REPLAY, (
            f"⚠️  REPLAY DÉTECTÉ — nonce '{event.nonce[:16]}...' déjà utilisé !"
        )

    # 4. Transaction légitime
    return TransactionResult.OK, (
        f"Transaction acceptée — {event.uid} / {event.amount/100:.0f} FCFA "
        f"via {event.terminal}"
    )


# ─── Scénario complet ─────────────────────────────────────────────────────────

def run_demo():
    print("=" * 62)
    print("  SmartCampus — Replay Attack Demo (M3)")
    print("=" * 62)

    registry  = NonceRegistry(ttl_seconds=300)
    attacker  = ReplayAttackSimulator()

    # ── Scan légitime ────────────────────────────────────────────
    print("\n[PHASE 1] Scan légitime par l'étudiant SC-2025-00101")
    print("-" * 45)
    scan = generate_legitimate_scan("SC-2025-00101", amount=60000, terminal="RESTO-A1")
    scan_json = scan.to_json()
    print(f"  [TERMINAL] Scan publié : nonce={scan.nonce[:16]}...")

    # Attaquant capture le message (sniff WiFi/MQTT non TLS)
    attacker.capture(scan_json)

    # Backend traite
    status, msg = process_scan(scan_json, registry)
    print(f"  [BACKEND]  Status : {status}")
    print(f"  [BACKEND]  {msg}")
    assert status == TransactionResult.OK

    # ── Replay attack ────────────────────────────────────────────
    print("\n[PHASE 2] Replay attack — l'attaquant rejoue le même scan")
    print("-" * 45)
    replayed_json = attacker.replay(delay_seconds=0)   # délai 0 pour la démo

    status2, msg2 = process_scan(replayed_json, registry)
    print(f"  [BACKEND]  Status : {status2}")
    print(f"  [BACKEND]  {msg2}")
    assert status2 == TransactionResult.REPLAY

    # ── Replay après 30s (timestamp expiry) ─────────────────────
    print("\n[PHASE 3] Replay avec timestamp expiré (simulé)")
    print("-" * 45)
    old_scan = generate_legitimate_scan("SC-2025-00102", amount=20000, terminal="PHOTO-B2")
    old_data = json.loads(old_scan.to_json())
    old_data["timestamp"] -= 60_000   # 60 secondes dans le passé
    # Recalculer signature avec le vieux timestamp
    msg_bytes = f"{old_data['uid']}|{old_data['timestamp']}|{old_data['nonce']}".encode()
    old_data["signature"] = hmac.new(TERMINAL_SECRET, msg_bytes, hashlib.sha256).hexdigest()

    status3, msg3 = process_scan(json.dumps(old_data), registry)
    print(f"  [BACKEND]  Status : {status3}")
    print(f"  [BACKEND]  {msg3}")
    assert status3 == TransactionResult.EXPIRED

    # ── HMAC forgery ─────────────────────────────────────────────
    print("\n[PHASE 4] Scan forgé (attaquant sans la clé HMAC)")
    print("-" * 45)
    forged = generate_legitimate_scan("SC-2025-00103", amount=500000, terminal="RESTO-A1")
    forged_data = json.loads(forged.to_json())
    forged_data["signature"] = "deadbeef" * 8   # signature arbitraire

    status4, msg4 = process_scan(json.dumps(forged_data), registry)
    print(f"  [BACKEND]  Status : {status4}")
    print(f"  [BACKEND]  {msg4}")
    assert status4 == TransactionResult.HMAC

    # ── Résumé ───────────────────────────────────────────────────
    print("\n" + "=" * 62)
    print("  RÉSUMÉ DES CONTRE-MESURES")
    print("=" * 62)
    print("  ✅ Nonce usage unique    → Replay bloqué (phase 2)")
    print("  ✅ Fenêtre temporelle    → Replay tardif bloqué (phase 3)")
    print("  ✅ HMAC-SHA256 terminal  → Forgeage impossible (phase 4)")
    print("  ✅ TLS MQTT (prod)       → Capture impossible sans MITM")
    print()


if __name__ == "__main__":
    run_demo()
