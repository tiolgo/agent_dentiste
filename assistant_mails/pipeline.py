"""Orchestration du traitement d'un lot d'e-mails.

Pour chaque mail : lecture par règles (instantanée) → lecture par le LLM (si disponible) →
fusion prudente → décision (code) → rédaction (textes validés) → garde-fous → brouillon.

- Les urgences possibles repérées par les règles sont traitées en premier : avec un LLM lent,
  elles sont en tête de pile en quelques secondes, pas après les 60 mails du jour.
- Une erreur sur un mail ne bloque jamais les autres : il produit un brouillon
  « à traiter manuellement » (en priorité urgente si des signes d'urgence ont été vus).
"""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .analyse_regles import analyser_regles
from .attestation_pdf import generer_attestation
from .decision import Decision, decider
from .fusion import fusionner
from .garde_fous import controler, neutraliser
from .llm import ErreurLLM
from .modeles import Analyse, Mail, rang_urgence
from .redaction import composer_note, rediger
from .stockage import BrouillonAEnregistrer

journal = logging.getLogger("assistant_mails")
RANG_URGENCE_POSSIBLE = rang_urgence("possible")


@dataclass
class Resultat:
    mail: Mail
    brouillon_id: int | None = None
    categorie: str = ""
    priorite: str = ""
    statut: str = ""
    langue: str | None = None
    reponse: str | None = None
    pieces: list[str] = field(default_factory=list)
    note: str = ""
    alerte: str | None = None
    lecture: str = ""
    intentions: list[str] = field(default_factory=list)
    drapeaux: list[str] = field(default_factory=list)
    duree_ms: int = 0
    deja_traite: bool = False
    erreur: str | None = None
    segments: list[tuple[str, bool, str]] = field(default_factory=list)   # (bloc, tarif ?, texte) pour les tests


def alerte_console(brouillon_id: int, message: str) -> None:
    barre = "!" * 78
    print(f"\n{barre}\n!!! {message}\n!!! Brouillon n° {brouillon_id} placé en tête de pile : à traiter immédiatement."
          f"\n{barre}\n", file=sys.stderr, flush=True)


class Assistant:
    def __init__(self, dossier, stockage, ref: date, racine_documents: Path, lecteur=None, alerter=None,
                 etat_sans_llm: str = "règles seules (LLM désactivé)"):
        self.etat_sans_llm = etat_sans_llm
        self.dossier = dossier
        self.stockage = stockage
        self.ref = ref
        self.racine_documents = Path(racine_documents)
        self.lecteur = lecteur
        self.alerter = alerter or alerte_console
        self._echecs_connexion = 0

    # ------------------------------------------------------------------ lot
    def traiter_lot(self, mails: list[Mail], retraiter: bool = False) -> list[Resultat]:
        ordre = []
        for position, mail in enumerate(mails):
            try:
                rang = rang_urgence(analyser_regles(mail, self.ref)[0].urgence)
            except Exception:                       # le pré-tri ne doit jamais bloquer le lot
                rang = 0
            ordre.append((-rang, position, mail))
        ordre.sort(key=lambda x: (x[0], x[1]))
        urgents = [m for r, _, m in ordre if -r >= RANG_URGENCE_POSSIBLE]
        autres = [m for r, _, m in ordre if -r < RANG_URGENCE_POSSIBLE]
        resultats = [self.traiter(mail, retraiter) for mail in urgents]     # sans attendre le LLM
        if autres:
            self._prechauffer()
        return resultats + [self.traiter(mail, retraiter) for mail in autres]

    def _prechauffer(self) -> None:
        if self.lecteur is None or not hasattr(self.lecteur, "prechauffer") or self._echecs_connexion >= 2:
            return
        try:
            self.lecteur.prechauffer()
        except ErreurLLM as e:
            self._echecs_connexion += 1
            journal.warning("Chargement du modèle impossible : %s", e)

    # ------------------------------------------------------------------ un mail
    def traiter(self, mail: Mail, retraiter: bool = False) -> Resultat:
        debut = time.monotonic()
        res = Resultat(mail=mail)
        if not retraiter:
            existant = self.stockage.deja_traite(mail.empreinte)
            if existant:
                res.deja_traite, res.brouillon_id = True, existant
                return res
        regles = Analyse(source="regles")
        try:
            regles, _ = analyser_regles(mail, self.ref)
            return self._traiter(mail, regles, res, debut)
        except Exception as erreur:                 # jamais de mail perdu : brouillon de secours
            journal.exception("Échec du traitement du mail %s", mail.source_id)
            return self._secours(mail, regles, res, debut, erreur)

    def _lire_llm(self, mail: Mail, regles: Analyse):
        if rang_urgence(regles.urgence) >= RANG_URGENCE_POSSIBLE:
            # Règle 2 : une urgence possible remonte immédiatement, sans attendre la lecture du LLM
            # (le LLM ne pourrait de toute façon pas baisser ce niveau d'urgence).
            return None, None, "règles seules — urgence possible : brouillon immédiat, sans attendre le LLM"
        if self.lecteur is None:
            return None, None, self.etat_sans_llm
        if self._echecs_connexion >= 2:
            return None, None, "règles seules (LLM injoignable pendant ce lot)"
        try:
            analyse, fiche, _meta = self.lecteur.lire(mail)
            self._echecs_connexion = 0
            return analyse, fiche, f"règles + LLM ({self.lecteur.nom})"
        except ErreurLLM as e:
            if "injoignable" in str(e):
                self._echecs_connexion += 1
            journal.warning("Lecture LLM impossible pour le mail %s : %s", mail.source_id, e)
            return None, None, f"règles seules — LLM indisponible ({e})"

    def _traiter(self, mail: Mail, regles: Analyse, res: Resultat, debut: float) -> Resultat:
        analyse_llm, fiche, etat = self._lire_llm(mail, regles)
        analyse = fusionner(regles, analyse_llm)
        decision = decider(mail, analyse, self.dossier, self.ref)
        reponse = rediger(decision)
        problemes = controler(mail, decision, reponse, self.dossier, self.ref, analyse_llm)
        if problemes:
            journal.warning("Garde-fou déclenché pour le mail %s : %s", mail.source_id, problemes)
            decision = neutraliser(decision, problemes)
            reponse = rediger(decision)
            if controler(mail, decision, reponse, self.dossier, self.ref, analyse_llm):
                decision.sans_reponse, reponse = True, None
        pieces = self._preparer_pieces(decision)
        statut = "à compléter" if decision.a_completer and not decision.sans_reponse else "à valider"
        note = composer_note(decision, analyse, etat, pieces, problemes)
        duree = int((time.monotonic() - debut) * 1000)
        brouillon_id = self.stockage.enregistrer(BrouillonAEnregistrer(
            expediteur=mail.expediteur, sujet=mail.sujet, categorie=decision.categorie, priorite=decision.priorite,
            mail_original=mail.corps, reponse_proposee=reponse.texte if reponse else None, pieces_jointes=pieces,
            statut=statut, empreinte=mail.empreinte, source_id=mail.source_id, langue=decision.langue,
            patient_id=decision.patient_expediteur.id if decision.patient_expediteur else None,
            personne_concernee_id=decision.personne_concernee.id if decision.personne_concernee else None,
            destinataire=decision.destinataire, intentions=decision.intentions, drapeaux=decision.drapeaux,
            note_interne=note, resume=analyse.resume, analyse_regles=regles.vers_dict(), analyse_llm=fiche,
            modele=self.lecteur.nom if fiche is not None else None, duree_ms=duree))
        if decision.alerte:
            self.alerter(brouillon_id, decision.alerte)
        self._remplir(res, brouillon_id, decision, statut, reponse.texte if reponse else None, pieces, note, etat,
                      duree)
        res.segments = [(b.cle, b.tarif, t) for b, t in reponse.segments] if reponse else []
        return res

    def _preparer_pieces(self, decision: Decision) -> list[str]:
        chemins = []
        for piece in decision.pieces:
            if piece.type == "attestation":
                patient = self.dossier.patient(piece.patient_id)
                generer_attestation(self.racine_documents / piece.chemin, patient, piece.rdv, decision.langue, self.ref)
            chemins.append(piece.chemin)
        return chemins

    def _secours(self, mail: Mail, regles: Analyse, res: Resultat, debut: float, erreur: Exception) -> Resultat:
        urgent = regles.urgence in ("possible", "probable")
        lignes = []
        if urgent:
            lignes.append(f"⚠ URGENCE POSSIBLE (signes repérés : {', '.join(regles.signes_urgence)}) — À TRAITER "
                          "IMMÉDIATEMENT.")
        lignes.append(f"Erreur pendant le traitement automatique ({type(erreur).__name__}) : traiter ce message "
                      "manuellement. Aucune réponse ni pièce jointe n'a été préparée.")
        note = "\n".join(lignes)
        duree = int((time.monotonic() - debut) * 1000)
        try:
            brouillon_id = self.stockage.enregistrer(BrouillonAEnregistrer(
                expediteur=mail.expediteur or "(inconnu)", sujet=mail.sujet, categorie="à traiter manuellement",
                priorite="urgente" if urgent else "normale", mail_original=mail.corps, reponse_proposee=None,
                pieces_jointes=[], statut="à compléter", empreinte=mail.empreinte, source_id=mail.source_id,
                langue=regles.langue, patient_id=None, personne_concernee_id=None, destinataire=mail.expediteur,
                intentions=regles.intentions, drapeaux=["erreur_traitement"] + (["urgence"] if urgent else []),
                note_interne=note, resume=regles.resume, analyse_regles=regles.vers_dict(), duree_ms=duree))
        except Exception as e:
            res.erreur = f"{type(erreur).__name__} : {erreur} — et enregistrement impossible : {e}"
            return res
        if urgent:
            self.alerter(brouillon_id, f"Urgence possible — {mail.expediteur} — « {mail.sujet} » (traitement en erreur)")
        res.brouillon_id, res.categorie, res.priorite, res.statut = (
            brouillon_id, "à traiter manuellement", "urgente" if urgent else "normale", "à compléter")
        res.note, res.lecture, res.duree_ms, res.langue = note, "erreur", duree, regles.langue
        res.erreur = f"{type(erreur).__name__} : {erreur}"
        return res

    @staticmethod
    def _remplir(res: Resultat, brouillon_id: int, decision: Decision, statut: str, reponse: str | None,
                 pieces: list[str], note: str, etat: str, duree: int) -> None:
        res.brouillon_id, res.categorie, res.priorite, res.statut = (
            brouillon_id, decision.categorie, decision.priorite, statut)
        res.langue, res.reponse, res.pieces, res.note = decision.langue, reponse, pieces, note
        res.alerte, res.lecture, res.duree_ms = decision.alerte, etat, duree
        res.intentions, res.drapeaux = decision.intentions, decision.drapeaux
