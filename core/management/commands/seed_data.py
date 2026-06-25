"""
Génère un jeu de données de test réaliste pour Smart Campus.

Crée :
- les comptes de chaque rôle (admin / caissier / contrôleur) ;
- des terminaux variés ;
- ~30 étudiants (données chiffrées) avec leur paire de clés / certificat X.509 ;
- pour chaque étudiant : un compte de connexion, un solde, un historique de
  transactions, et des paiements de scolarité produisant des statuts variés
  (à jour, en retard, exonéré) ;
- les clés privées de carte sont écrites dans `certs/cards/<uid>.pem` afin de
  pouvoir simuler des scans signés valides (commande `simuler_scan`).

Usage :
    python manage.py seed_data            # ne fait rien si des étudiants existent
    python manage.py seed_data --vider    # purge puis régénère
"""
import random
import secrets
from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from comptes.models import Role
from core.signatures import generer_paire_et_certificat
from etudiants.models import Etudiant, StatutCarte
from iot.models import JournalScan
from monetique.models import (
    Solde,
    StatutTransaction,
    Transaction,
    TypeTransaction,
)
from scolarite.models import PaiementScolarite, StatutPaiement, TypePeriode
from terminaux.models import Terminal, TypeTerminal

Utilisateur = get_user_model()

PRENOMS = [
    "Awa", "Mamadou", "Fatou", "Cheikh", "Aïssatou", "Ibrahima", "Mariama",
    "Ousmane", "Khady", "Modou", "Bineta", "Abdoulaye", "Ndeye", "Moussa",
    "Sokhna", "Pape", "Adama", "Seynabou", "Lamine", "Rama", "Babacar",
    "Coumba", "Saliou", "Dieynaba", "Alioune", "Mame", "Daouda", "Astou",
    "Serigne", "Yacine",
]
NOMS = [
    "Diop", "Ndiaye", "Fall", "Sow", "Ba", "Sarr", "Gueye", "Diallo", "Sy",
    "Faye", "Mbaye", "Camara", "Touré", "Sané", "Cissé", "Diouf", "Niang",
    "Ka", "Seck", "Dione",
]
FILIERES = [
    "DIC1 — L3 Informatique",
    "DIC2 — M1 Génie Logiciel",
    "DIC3 — M2 SSI/SOIR",
    "GEE — L3 Électronique",
    "GC — M1 Génie Civil",
]


class Command(BaseCommand):
    help = "Génère des données de test (étudiants, soldes, transactions, scolarité)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--vider",
            action="store_true",
            help="Purge les données métier existantes avant de régénérer.",
        )
        parser.add_argument(
            "--nombre",
            type=int,
            default=30,
            help="Nombre d'étudiants à générer (défaut: 30).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)  # reproductibilité

        if options["vider"]:
            self._vider()

        if Etudiant.objects.exists():
            self.stdout.write(
                self.style.WARNING(
                    "Des étudiants existent déjà. Utilisez --vider pour régénérer."
                )
            )
            return

        self._creer_comptes_personnel()
        terminaux = self._creer_terminaux()
        self._creer_etudiants(options["nombre"], terminaux)

        self.stdout.write(self.style.SUCCESS("Données de test générées avec succès."))
        self.stdout.write(
            "Comptes : admin/admin1234 · caissier/caissier1234 · "
            "controleur/controleur1234 (et un compte par étudiant : "
            "<uid en minuscules>/etudiant1234)."
        )

    # ------------------------------------------------------------------
    def _vider(self):
        self.stdout.write("Purge des données métier…")
        JournalScan.objects.all().delete()
        Transaction.objects.all().delete()
        PaiementScolarite.objects.all().delete()
        Solde.objects.all().delete()
        Etudiant.objects.all().delete()
        Terminal.objects.all().delete()
        # On garde le superuser éventuel ; on supprime les comptes de seed.
        Utilisateur.objects.filter(role=Role.ETUDIANT).delete()

    def _creer_comptes_personnel(self):
        comptes = [
            ("admin", Role.ADMIN, "admin1234", True),
            ("caissier", Role.CAISSIER, "caissier1234", False),
            ("controleur", Role.CONTROLEUR, "controleur1234", False),
        ]
        for username, role, mdp, staff in comptes:
            u, cree = Utilisateur.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@smartcampus.sn",
                    "role": role,
                    "is_staff": staff or role == Role.ADMIN,
                    "is_superuser": role == Role.ADMIN,
                },
            )
            if cree:
                u.set_password(mdp)
                u.save()
        self.caissier = Utilisateur.objects.get(username="caissier")
        self.admin = Utilisateur.objects.get(username="admin")

    def _creer_terminaux(self):
        donnees = [
            ("RESTO-01", TypeTerminal.RESTAURANT, "Restaurant central"),
            ("RESTO-02", TypeTerminal.RESTAURANT, "Cafétéria pavillon B"),
            ("REPRO-01", TypeTerminal.REPROGRAPHIE, "Reprographie bibliothèque"),
            ("BUS-01", TypeTerminal.TRANSPORT, "Navette campus"),
            ("RECH-01", TypeTerminal.RECHARGE, "Borne de recharge accueil"),
            ("CTRL-01", TypeTerminal.CONTROLE, "Contrôle entrée principale"),
        ]
        terminaux = []
        for code, type_, libelle in donnees:
            t, _ = Terminal.objects.get_or_create(
                code=code, defaults={"type": type_, "libelle": libelle}
            )
            terminaux.append(t)
        return terminaux

    def _creer_etudiants(self, nombre, terminaux):
        dossier_cles = Path(settings.BASE_DIR) / "certs" / "cards"
        dossier_cles.mkdir(parents=True, exist_ok=True)

        terminaux_paiement = [
            t for t in terminaux if t.type != TypeTerminal.CONTROLE
        ]
        recharge = next(t for t in terminaux if t.type == TypeTerminal.RECHARGE)

        for i in range(1, nombre + 1):
            uid = f"SC-2025-{i:05d}"
            prenom = random.choice(PRENOMS)
            nom = random.choice(NOMS)
            filiere = random.choice(FILIERES)

            cle_privee_pem, certificat_pem = generer_paire_et_certificat(uid)
            (dossier_cles / f"{uid}.pem").write_text(cle_privee_pem)

            # Compte de connexion étudiant.
            compte = Utilisateur.objects.create(
                username=uid.lower(),
                email=f"{prenom.lower()}.{nom.lower()}{i}@etu.smartcampus.sn",
                role=Role.ETUDIANT,
            )
            compte.set_password("etudiant1234")
            compte.save()

            etu = Etudiant(
                uid_carte=uid,
                email=compte.email,
                filiere=filiere,
                statut=StatutCarte.ACTIF,
                certificat_pub=certificat_pem,
                compte=compte,
            )
            # Affectation via les setters → chiffrement automatique.
            etu.nom = nom
            etu.prenom = prenom
            etu.matricule = f"MAT{2025000 + i}"
            etu.save()

            self._creer_solde_et_transactions(etu, terminaux_paiement, recharge)
            self._creer_scolarite(etu, i)

        # Un étudiant suspendu et un bloqué pour tester les refus.
        for uid, statut in (
            ("SC-2025-00002", StatutCarte.SUSPENDU),
            ("SC-2025-00003", StatutCarte.BLOQUE),
        ):
            Etudiant.objects.filter(uid_carte=uid).update(statut=statut)

    def _creer_solde_et_transactions(self, etu, terminaux_paiement, recharge):
        # Recharge initiale puis quelques débits ⇒ solde cohérent.
        montant_initial = random.choice([500000, 1000000, 1500000])  # centimes
        solde = montant_initial

        Transaction.objects.create(
            etudiant=etu,
            terminal=recharge,
            type=TypeTransaction.CREDIT,
            montant=montant_initial,
            statut=StatutTransaction.VALIDE,
            nonce=secrets.token_hex(16),
            metadata={"origine": "seed"},
        )

        for _ in range(random.randint(2, 6)):
            montant = random.choice([15000, 25000, 50000, 75000, 100000])
            if montant > solde:
                continue
            solde -= montant
            Transaction.objects.create(
                etudiant=etu,
                terminal=random.choice(terminaux_paiement),
                type=TypeTransaction.DEBIT,
                montant=montant,
                statut=StatutTransaction.VALIDE,
                nonce=secrets.token_hex(16),
                metadata={"origine": "seed", "solde_apres": solde},
            )

        Solde.objects.update_or_create(
            etudiant=etu, defaults={"montant": solde, "version": 1}
        )

    def _creer_scolarite(self, etu, index):
        """Crée un historique de scolarité produisant des statuts variés."""
        aujourdhui = timezone.localdate()
        caissier = self.caissier

        # 1 étudiant sur 10 est exonéré.
        if index % 10 == 0:
            PaiementScolarite.objects.create(
                etudiant=etu,
                type_periode=TypePeriode.EXONERATION,
                periode_couverte=f"{aujourdhui.year}-S1",
                montant=0,
                caissier=self.admin,
                statut=StatutPaiement.VALIDE,
            )
            return

        # 1 sur 4 paie au semestre, les autres au mois.
        if index % 4 == 0:
            # Semestriel : la moitié à jour (paie le semestre courant), l'autre
            # en retard (ne paie qu'un ancien semestre).
            a_jour = index % 8 == 0
            label = self._semestre_label(aujourdhui, recul=0 if a_jour else 2)
            PaiementScolarite.objects.create(
                etudiant=etu,
                type_periode=TypePeriode.SEMESTRIEL,
                periode_couverte=label,
                montant=45000000,  # 450 000 FCFA
                caissier=caissier,
                statut=StatutPaiement.VALIDE,
            )
            return

        # Mensuel : à jour (paie jusqu'au mois courant) ou en retard.
        a_jour = index % 3 != 0
        recul_max = 0 if a_jour else 3  # 3 mois d'impayés si en retard
        for recul in range(recul_max, 8):
            annee, mois = self._mois_recule(aujourdhui, recul)
            PaiementScolarite.objects.create(
                etudiant=etu,
                type_periode=TypePeriode.MENSUEL,
                periode_couverte=f"{annee:04d}-{mois:02d}",
                montant=5000000,  # 50 000 FCFA / mois
                caissier=caissier,
                statut=StatutPaiement.VALIDE,
            )

    @staticmethod
    def _mois_recule(d: date, recul: int):
        mois = d.month - recul
        annee = d.year
        while mois <= 0:
            mois += 12
            annee -= 1
        return annee, mois

    @staticmethod
    def _semestre_label(d: date, recul: int) -> str:
        # Construit un label de semestre en reculant de `recul` semestres.
        if d.month >= 10:
            annee, sem = d.year, 1
        elif d.month < 3:
            annee, sem = d.year - 1, 1
        else:
            annee, sem = d.year, 2
        index = annee * 2 + (sem - 1) - recul
        annee, reste = divmod(index, 2)
        return f"{annee}-S{reste + 1}"
