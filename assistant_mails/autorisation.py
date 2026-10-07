"""Règle 3 — à qui a-t-on le droit d'envoyer des informations d'un dossier ?

Un document (facture, attestation) — et plus largement toute donnée d'un dossier, comme la
date d'un rendez-vous — ne part qu'à l'adresse e-mail enregistrée dans le dossier du patient
concerné ou, pour un mineur, à celle de son représentant légal enregistré.

Ce module est volontairement court : c'est le SEUL endroit qui en décide. Il est appelé deux
fois pour chaque brouillon : par la décision, puis par les garde-fous, juste avant l'écriture.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .modeles import Mail, Patient


@dataclass(frozen=True)
class Verdict:
    autorise: bool
    raison: str                      # explication en français, pour la note interne
    adresses_autorisees: tuple[str, ...] = ()


def adresses_autorisees(patient: Patient, dossier, ref: date) -> tuple[str, ...]:
    """Adresses qui peuvent recevoir les documents de ce patient."""
    if patient.est_mineur(ref):
        # Mineur : uniquement le représentant légal enregistré (jamais l'adresse du dossier
        # de l'enfant, dont on ne sait pas à qui elle appartient).
        return tuple(sorted({r.email.strip().lower() for r in dossier.representants(patient.id) if r.email}))
    return (patient.email.strip().lower(),) if patient.email else ()


def verifier(mail: Mail, patient: Patient | None, dossier, ref: date) -> Verdict:
    if patient is None:
        return Verdict(False, "personne concernée non identifiée de façon certaine dans le dossier")
    expediteur = mail.expediteur.strip().lower()
    autorisees = adresses_autorisees(patient, dossier, ref)
    mineur = patient.est_mineur(ref)
    if mail.repondre_a and mail.repondre_a != expediteur:
        return Verdict(False, f"l'en-tête « Répondre à » ({mail.repondre_a}) diffère de l'expéditeur : "
                              "risque de détournement de la réponse", autorisees)
    if not autorisees:
        if mineur:
            return Verdict(False, "patient mineur et aucun représentant légal avec adresse e-mail enregistré")
        return Verdict(False, "aucune adresse e-mail enregistrée dans le dossier")
    if expediteur in autorisees:
        qui = "du représentant légal enregistré" if mineur else "enregistrée dans le dossier"
        return Verdict(True, f"l'expéditeur est l'adresse {qui}", autorisees)
    qui = "d'un représentant légal enregistré" if mineur else "enregistrée dans le dossier du patient"
    return Verdict(False, f"l'expéditeur n'est pas l'adresse {qui}", autorisees)
