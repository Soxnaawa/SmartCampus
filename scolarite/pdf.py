"""
Génération du reçu de paiement de scolarité en PDF (reportlab).

Le reçu inclut : établissement, identité de l'étudiant (déchiffrée), période,
montant, date et numéro de reçu. Il n'est téléchargeable que par l'étudiant
concerné (contrôle d'accès assuré côté vue).
"""
from __future__ import annotations

import io

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .models import PaiementScolarite


def _fcfa(centimes: int) -> str:
    """Formate un montant en centimes vers une chaîne FCFA lisible."""
    fcfa = centimes / 100
    # Séparateur de milliers par espace insécable, sans décimales superflues.
    return f"{fcfa:,.0f}".replace(",", " ") + " FCFA"


def generer_recu_pdf(paiement: PaiementScolarite) -> bytes:
    """Construit le PDF du reçu et renvoie ses octets."""
    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    largeur, hauteur = A4

    marge = 20 * mm
    y = hauteur - marge

    # --- En-tête établissement ---
    c.setFont("Helvetica-Bold", 16)
    c.drawString(marge, y, settings.ETABLISSEMENT_NOM)
    y -= 7 * mm
    c.setFont("Helvetica", 10)
    c.drawString(marge, y, settings.ETABLISSEMENT_VILLE)
    y -= 4 * mm
    c.setStrokeColor(colors.HexColor("#1a4f8b"))
    c.setLineWidth(1.5)
    c.line(marge, y, largeur - marge, y)
    y -= 12 * mm

    # --- Titre ---
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(largeur / 2, y, "REÇU DE PAIEMENT DE SCOLARITÉ")
    y -= 12 * mm

    # --- Numéro & date ---
    c.setFont("Helvetica", 11)
    c.drawString(marge, y, f"N° de reçu : {paiement.numero_recu}")
    c.drawRightString(
        largeur - marge, y, f"Date : {paiement.cree_le:%d/%m/%Y %H:%M}"
    )
    y -= 12 * mm

    # --- Bloc identité étudiant ---
    etu = paiement.etudiant
    lignes = [
        ("Étudiant", etu.nom_complet),
        ("Matricule", etu.matricule),
        ("UID carte", etu.uid_carte),
        ("Filière", etu.filiere),
    ]
    c.setFont("Helvetica", 11)
    for libelle, valeur in lignes:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(marge, y, f"{libelle} :")
        c.setFont("Helvetica", 11)
        c.drawString(marge + 35 * mm, y, str(valeur))
        y -= 8 * mm

    y -= 6 * mm
    c.setStrokeColor(colors.HexColor("#cccccc"))
    c.setLineWidth(0.8)
    c.line(marge, y, largeur - marge, y)
    y -= 12 * mm

    # --- Détail du paiement ---
    details = [
        ("Type de période", paiement.get_type_periode_display()),
        ("Période couverte", paiement.periode_couverte or "—"),
        ("Statut", paiement.get_statut_display()),
    ]
    for libelle, valeur in details:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(marge, y, f"{libelle} :")
        c.setFont("Helvetica", 11)
        c.drawString(marge + 45 * mm, y, str(valeur))
        y -= 8 * mm

    y -= 6 * mm
    # --- Montant (encadré) ---
    c.setFillColor(colors.HexColor("#eef4fb"))
    c.rect(marge, y - 10 * mm, largeur - 2 * marge, 16 * mm, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(marge + 5 * mm, y - 3 * mm, "MONTANT PAYÉ :")
    c.drawRightString(
        largeur - marge - 5 * mm, y - 3 * mm, _fcfa(paiement.montant)
    )
    y -= 30 * mm

    # --- Pied de page ---
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawCentredString(
        largeur / 2,
        marge,
        "Document généré automatiquement par Smart Campus — sans valeur fiscale.",
    )

    c.showPage()
    c.save()
    tampon.seek(0)
    return tampon.read()
