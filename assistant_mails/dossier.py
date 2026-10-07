"""Accès en lecture au logiciel de cabinet (DentaGest).

Toutes les requêtes listent leurs colonnes : le motif des rendez-vous (information de santé)
n'est JAMAIS lu. En production, le rôle PostgreSQL de l'assistant n'a d'ailleurs pas le droit
de le lire (privilèges par colonne, voir installation.py).
"""

from __future__ import annotations

import psycopg

from .modeles import Facture, Patient, RendezVous, Representant
from .normalisation import replier

_COLONNES_PATIENT = "id, nom, prenom, email, telephone, langue, date_naissance"


def _patient(ligne) -> Patient:
    return Patient(*ligne)


class DossierPostgres:
    def __init__(self, connexion: psycopg.Connection):
        self.cx = connexion
        self._patients: list[Patient] | None = None
        self._representants_disponibles: bool | None = None

    def tous_les_patients(self) -> list[Patient]:
        if self._patients is None:
            lignes = self.cx.execute(f"SELECT {_COLONNES_PATIENT} FROM patients ORDER BY id").fetchall()
            self._patients = [_patient(l) for l in lignes]
        return self._patients

    def patient(self, patient_id: int) -> Patient | None:
        ligne = self.cx.execute(f"SELECT {_COLONNES_PATIENT} FROM patients WHERE id = %s", (patient_id,)).fetchone()
        return _patient(ligne) if ligne else None

    def patient_par_email(self, email: str) -> Patient | None:
        if not email:
            return None
        ligne = self.cx.execute(
            f"SELECT {_COLONNES_PATIENT} FROM patients WHERE lower(trim(email)) = lower(trim(%s))", (email,)
        ).fetchone()
        return _patient(ligne) if ligne else None

    def chercher_par_nom(self, prenom: str = "", nom: str = "") -> list[Patient]:
        p, n = replier(prenom).strip(), replier(nom).strip()
        if not p and not n:
            return []
        return [x for x in self.tous_les_patients()
                if (not p or replier(x.prenom) == p) and (not n or replier(x.nom) == n)]

    def factures(self, patient_id: int) -> list[Facture]:
        lignes = self.cx.execute(
            "SELECT numero, patient_id, date_facture, statut, fichier_pdf FROM factures "
            "WHERE patient_id = %s ORDER BY date_facture DESC, numero DESC", (patient_id,)).fetchall()
        return [Facture(*l) for l in lignes]

    def facture(self, numero: str) -> Facture | None:
        ligne = self.cx.execute(
            "SELECT numero, patient_id, date_facture, statut, fichier_pdf FROM factures "
            "WHERE upper(numero) = upper(%s)", (numero,)).fetchone()
        return Facture(*ligne) if ligne else None

    def facture_par_fichier(self, chemin: str) -> Facture | None:
        ligne = self.cx.execute(
            "SELECT numero, patient_id, date_facture, statut, fichier_pdf FROM factures WHERE fichier_pdf = %s",
            (chemin,)).fetchone()
        return Facture(*ligne) if ligne else None

    def rendez_vous(self, patient_id: int) -> list[RendezVous]:
        # Pas de « motif » : volontairement absent de la requête.
        lignes = self.cx.execute(
            "SELECT r.id, r.patient_id, r.debut, r.duree_min, r.statut, p.nom "
            "FROM rendez_vous r JOIN praticiens p ON p.id = r.praticien_id "
            "WHERE r.patient_id = %s ORDER BY r.debut", (patient_id,)).fetchall()
        return [RendezVous(*l) for l in lignes]

    def representants(self, patient_id: int) -> list[Representant]:
        if self._representants_disponibles is False:
            return []
        try:
            lignes = self.cx.execute(
                "SELECT patient_id, prenom, nom, email, lien FROM assistant.representants_legaux "
                "WHERE patient_id = %s", (patient_id,)).fetchall()
        except psycopg.errors.UndefinedTable:
            self._representants_disponibles = False     # schéma non installé : aucun représentant connu
            return []
        return [Representant(*l) for l in lignes]


class DossierMemoire:
    """Même interface, en mémoire (tests et démonstrations sans base)."""

    def __init__(self, patients=(), factures=(), rendez_vous=(), representants=()):
        self._patients = list(patients)
        self._factures = list(factures)
        self._rdv = list(rendez_vous)
        self._representants = list(representants)

    def tous_les_patients(self):
        return list(self._patients)

    def patient(self, patient_id):
        return next((p for p in self._patients if p.id == patient_id), None)

    def patient_par_email(self, email):
        e = (email or "").strip().lower()
        return next((p for p in self._patients if p.email and p.email.strip().lower() == e), None) if e else None

    def chercher_par_nom(self, prenom="", nom=""):
        p, n = replier(prenom).strip(), replier(nom).strip()
        if not p and not n:
            return []
        return [x for x in self._patients if (not p or replier(x.prenom) == p) and (not n or replier(x.nom) == n)]

    def factures(self, patient_id):
        return sorted((f for f in self._factures if f.patient_id == patient_id),
                      key=lambda f: (f.date_facture, f.numero), reverse=True)

    def facture(self, numero):
        return next((f for f in self._factures if f.numero.upper() == (numero or "").upper()), None)

    def facture_par_fichier(self, chemin):
        return next((f for f in self._factures if f.fichier_pdf == chemin), None)

    def rendez_vous(self, patient_id):
        return sorted((r for r in self._rdv if r.patient_id == patient_id), key=lambda r: r.debut)

    def representants(self, patient_id):
        return [r for r in self._representants if r.patient_id == patient_id]
