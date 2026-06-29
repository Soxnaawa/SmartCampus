#!/usr/bin/env python3
"""
SmartCampus — Audit Sécurité (M3 - Semaine 4)
==============================================
Analyse statique du code des autres modules :
  - P2 (hardware)  : injection dans les payloads MQTT
  - P3 (backend)   : SQL injection, JWT mal configuré, secrets hardcodés
  - P5 (frontend)  : XSS, tokens exposés

Sorties :
  - Console colorée
  - audit_report.json (machine-readable)
  - audit_report.md   (pour le rapport final)

Auteur: P4 — Cybersécurité
"""

import os
import re
import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal

Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]

# ─── ANSI colors ──────────────────────────────────────────────────────────────
RESET  = "\033[0m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
BOLD   = "\033[1m"

SEV_COLOR = {
    "CRITICAL": RED + BOLD,
    "HIGH":     RED,
    "MEDIUM":   YELLOW,
    "LOW":      CYAN,
    "INFO":     GREEN,
}

# ─── Modèles ──────────────────────────────────────────────────────────────────

@dataclass
class Finding:
    rule_id:   str
    severity:  Severity
    file:      str
    line:      int
    column:    int
    message:   str
    snippet:   str
    fix:       str

@dataclass
class AuditReport:
    project:   str   = "SmartCampus"
    auditor:   str   = "P4 — Cybersécurité"
    findings:  list  = field(default_factory=list)
    stats:     dict  = field(default_factory=dict)

    def add(self, f: Finding):
        self.findings.append(asdict(f))

    def summary(self) -> dict:
        from collections import Counter
        c = Counter(f["severity"] for f in self.findings)
        return dict(c)


# ─── Règles d'audit ───────────────────────────────────────────────────────────

RULES = [
    # ── SQL Injection ──────────────────────────────────────────────────────
    {
        "id":       "SEC-001",
        "severity": "CRITICAL",
        "pattern":  re.compile(
            # f-string SQL : toujours suspect
            r'f["\'].*\b(SELECT|INSERT|UPDATE|DELETE)\b.*\{.*\}.*["\']'
            # % interpolation dans execute (mais PAS cursor.execute(sql, (param,)) — safe)
            r'|(cursor\.execute|connection\.execute|db\.execute)\s*\(\s*["\'][^"\']*%\s*[^,)]+\)',
            re.IGNORECASE
        ),
        "message":  "Possible SQL injection via interpolation directe (f-string ou % sans paramètre)",
        "fix":      "Utiliser des requêtes paramétrées : cursor.execute(sql, (param,))",
        "exts":     {".py"},
    },
    # ── Hardcoded secrets ──────────────────────────────────────────────────
    {
        "id":       "SEC-002",
        "severity": "HIGH",
        "pattern":  re.compile(
            r'(SECRET_KEY|JWT_SECRET|HMAC_KEY|API_KEY|PASSWORD|PASSWD)\s*=\s*["\'][^"\']{6,}["\']',
            re.IGNORECASE
        ),
        "message":  "Secret hardcodé dans le code source",
        "fix":      "Utiliser des variables d'environnement (os.environ.get) ou un vault",
        "exts":     {".py", ".js", ".ts", ".env.example"},
    },
    # ── JWT none algorithm ─────────────────────────────────────────────────
    {
        "id":       "SEC-003",
        "severity": "CRITICAL",
        "pattern":  re.compile(r'algorithm\s*=\s*["\']none["\']', re.IGNORECASE),
        "message":  "JWT algorithm=none : bypass complet de la signature",
        "fix":      "Forcer algorithm='HS256' ou 'RS256' et valider explicitement",
        "exts":     {".py"},
    },
    # ── JWT algorithm non spécifié ─────────────────────────────────────────
    {
        "id":       "SEC-004",
        "severity": "HIGH",
        "pattern":  re.compile(r'jwt\.decode\s*\([^)]*algorithms\s*=\s*\[["\'].*["\'][^)]*\)', re.IGNORECASE),
        "message":  "Vérifier que jwt.decode() n'accepte pas des algorithmes multiples dont 'none'",
        "fix":      "algorithms=['HS256'] ou ['RS256'] — liste mono-algo",
        "exts":     {".py"},
    },
    # ── Debug=True en production ───────────────────────────────────────────
    {
        "id":       "SEC-005",
        "severity": "MEDIUM",
        "pattern":  re.compile(r'DEBUG\s*=\s*True', re.IGNORECASE),
        "message":  "DEBUG=True expose les stack traces et la configuration Django",
        "fix":      "DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'",
        "exts":     {".py"},
    },
    # ── CORS wildcard ──────────────────────────────────────────────────────
    {
        "id":       "SEC-006",
        "severity": "HIGH",
        "pattern":  re.compile(r"CORS_ALLOW_ALL_ORIGINS\s*=\s*True|cors\(\s*origin\s*=\s*['\"]?\*"),
        "message":  "CORS wildcard (*) : toute origine peut appeler l'API",
        "fix":      "CORS_ALLOWED_ORIGINS = ['https://smartcampus.esp.sn']",
        "exts":     {".py", ".js"},
    },
    # ── Pas de TLS sur MQTT ────────────────────────────────────────────────
    {
        "id":       "SEC-007",
        "severity": "HIGH",
        "pattern":  re.compile(r'connect\s*\(\s*["\'][^"\']+["\'],\s*1883\s*\)'),
        "message":  "Connexion MQTT sur port 1883 (non chiffré) — susceptible au sniffing",
        "fix":      "Utiliser port 8883 (MQTT over TLS) avec tls_set()",
        "exts":     {".py"},
    },
    # ── Eval / exec ────────────────────────────────────────────────────────
    {
        "id":       "SEC-008",
        "severity": "CRITICAL",
        "pattern":  re.compile(r'\beval\s*\(|\bexec\s*\('),
        "message":  "eval()/exec() : exécution de code arbitraire",
        "fix":      "Supprimer. Utiliser ast.literal_eval() pour les données structurées",
        "exts":     {".py", ".js"},
    },
    # ── Print de tokens/passwords ──────────────────────────────────────────
    {
        "id":       "SEC-009",
        "severity": "MEDIUM",
        "pattern":  re.compile(r'print\s*\(.*\b(token|password|secret|key|signature)\b', re.IGNORECASE),
        "message":  "Possible fuite de credential dans les logs",
        "fix":      "Supprimer le print ou masquer : print(token[:4]+'****')",
        "exts":     {".py"},
    },
    # ── Randomness faible ──────────────────────────────────────────────────
    {
        "id":       "SEC-010",
        "severity": "HIGH",
        "pattern":  re.compile(r'\brandom\.(random|randint|choice|seed)\b(?!.*secrets)'),
        "message":  "random.* non cryptographique utilisé (prévisible)",
        "fix":      "Remplacer par secrets.token_hex() / secrets.token_bytes()",
        "exts":     {".py"},
    },
    # ── XSS innerHTML ──────────────────────────────────────────────────────
    {
        "id":       "SEC-011",
        "severity": "HIGH",
        "pattern":  re.compile(r'\.innerHTML\s*='),
        "message":  "innerHTML affecté : vecteur XSS si données non assainies",
        "fix":      "Utiliser textContent ou une bibliothèque DOMPurify",
        "exts":     {".js", ".jsx", ".ts", ".tsx"},
    },
    # ── Token dans localStorage ────────────────────────────────────────────
    {
        "id":       "SEC-012",
        "severity": "MEDIUM",
        "pattern":  re.compile(r'localStorage\.(set|get)Item\s*\(\s*["\'].*token', re.IGNORECASE),
        "message":  "JWT stocké dans localStorage : accessible par XSS",
        "fix":      "Préférer httpOnly cookies + SameSite=Strict",
        "exts":     {".js", ".jsx", ".ts", ".tsx"},
    },
]


# ─── Scanner ──────────────────────────────────────────────────────────────────

def scan_file(path: Path, rules: list) -> list[Finding]:
    findings = []
    ext = path.suffix.lower()
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return findings

    for rule in rules:
        if ext not in rule["exts"]:
            continue
        for lineno, line in enumerate(lines, start=1):
            m = rule["pattern"].search(line)
            if m:
                findings.append(Finding(
                    rule_id  = rule["id"],
                    severity = rule["severity"],
                    file     = str(path),
                    line     = lineno,
                    column   = m.start() + 1,
                    message  = rule["message"],
                    snippet  = line.strip()[:120],
                    fix      = rule["fix"],
                ))
    return findings


def scan_directory(root: Path, rules: list, exclude: set[str] | None = None) -> list[Finding]:
    if exclude is None:
        exclude = {".git", "__pycache__", "node_modules", ".venv", "venv"}
    findings = []
    for p in root.rglob("*"):
        if any(ex in p.parts for ex in exclude):
            continue
        if p.is_file() and p.suffix in {".py", ".js", ".jsx", ".ts", ".tsx", ".env", ".env.example"}:
            findings.extend(scan_file(p, rules))
    return findings


# ─── Rapport ──────────────────────────────────────────────────────────────────

def print_finding(f: Finding):
    color = SEV_COLOR.get(f["severity"], "")
    print(f"  {color}[{f['severity']:8}]{RESET} {f['rule_id']} — {f['message']}")
    print(f"           Fichier : {f['file']}:{f['line']}:{f['column']}")
    print(f"           Code    : {f['snippet']}")
    print(f"           Fix     : {f['fix']}")
    print()


def generate_markdown_report(report: AuditReport, out: Path):
    lines = [
        "# SmartCampus — Rapport d'Audit Sécurité",
        "",
        f"**Auditeur :** {report.auditor}  ",
        f"**Projet :** {report.project}  ",
        "",
        "## Résumé des vulnérabilités",
        "",
        "| Criticité | Nombre |",
        "|-----------|--------|",
    ]
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        n = report.stats.get(sev, 0)
        if n:
            lines.append(f"| {sev} | {n} |")
    lines += ["", "## Détail des findings", ""]

    for f in report.findings:
        lines += [
            f"### `{f['rule_id']}` — {f['severity']}",
            "",
            f"**Fichier :** `{f['file']}` ligne {f['line']}",
            "",
            f"**Problème :** {f['message']}",
            "",
            f"```\n{f['snippet']}\n```",
            "",
            f"**Correction :** {f['fix']}",
            "",
            "---",
            "",
        ]
    out.write_text("\n".join(lines), encoding="utf-8")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SmartCampus Security Audit")
    parser.add_argument("path", nargs="?", default=".", help="Répertoire à auditer")
    parser.add_argument("--json-out", default="audit_report.json")
    parser.add_argument("--md-out",   default="audit_report.md")
    args = parser.parse_args()

    target = Path(args.path).resolve()
    print(f"\n{BOLD}SmartCampus — Security Audit{RESET}")
    print(f"Cible : {target}\n")

    findings = scan_directory(target, RULES)

    report = AuditReport()
    for f in findings:
        report.add(f)
    report.stats = report.summary()

    # Console
    if findings:
        for f in report.findings:
            print_finding(f)
    else:
        print(f"{GREEN}✅ Aucune vulnérabilité détectée.{RESET}\n")

    # Fichiers
    out_dir = Path(args.json_out).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    Path(args.json_out).write_text(
        json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    generate_markdown_report(report, Path(args.md_out))

    # Résumé
    stats = report.stats
    total = sum(stats.values())
    print(f"\n{BOLD}Résumé :{RESET}")
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        n = stats.get(sev, 0)
        if n:
            color = SEV_COLOR[sev]
            print(f"  {color}{sev:8}{RESET} : {n}")
    print(f"  {'TOTAL':8} : {total}")
    print(f"\nRapport JSON : {args.json_out}")
    print(f"Rapport MD   : {args.md_out}\n")

    # Exit code (CI/CD gate)
    if stats.get("CRITICAL", 0) > 0:
        sys.exit(2)   # CRITICAL → pipeline bloqué
    if stats.get("HIGH", 0) > 0:
        sys.exit(1)   # HIGH → warning CI


if __name__ == "__main__":
    main()
