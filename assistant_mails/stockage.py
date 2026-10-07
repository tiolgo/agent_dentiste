"""Écriture des brouillons.

Rien n'est jamais envoyé : l'unique sortie du système est la table « brouillons » (à valider
par le secrétariat), complétée par la table assistant.analyses (note interne, traçabilité).
Le programme ne contient aucun code d'envoi d'e-mail.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import psycopg
from psycopg.types.json import Jsonb


@dataclass
class BrouillonAEnregistrer:
    expediteur: str
    sujet: str
    categorie: str
    priorite: str
    mail_original: str
    reponse_proposee: str | None
    pieces_jointes: list[str]
    statut: str
    empreinte: str
    source_id: str | None
    langue: str | None
    patient_id: int | None
    personne_concernee_id: int | None
    destinataire: str
    intentions: list[str]
    drapeaux: list[str]
    note_interne: str
    resume: str
    analyse_regles: dict
    analyse_llm: dict | None = None
    modele: str | None = None
    duree_ms: int = 0
    extras: dict = field(default_factory=dict)


class StockagePostgres:
    def __init__(self, connexion: psycopg.Connection):
        self.cx = connexion

    def deja_traite(self, empreinte: str) -> int | None:
        ligne = self.cx.execute(
            "SELECT brouillon_id FROM assistant.analyses WHERE empreinte = %s ORDER BY id DESC LIMIT 1",
            (empreinte,)).fetchone()
        return ligne[0] if ligne else None

    def enregistrer(self, b: BrouillonAEnregistrer) -> int:
        with self.cx.transaction():
            brouillon_id = self.cx.execute(
                "INSERT INTO brouillons (expediteur, sujet, categorie, priorite, mail_original, reponse_proposee, "
                "pieces_jointes, statut) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (b.expediteur, b.sujet, b.categorie, b.priorite, b.mail_original, b.reponse_proposee,
                 b.pieces_jointes, b.statut)).fetchone()[0]
            self.cx.execute(
                "INSERT INTO assistant.analyses (brouillon_id, empreinte, source_id, langue, patient_id, "
                "personne_concernee_id, destinataire, intentions, drapeaux, note_interne, resume, analyse_regles, "
                "analyse_llm, modele, duree_ms) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (brouillon_id, b.empreinte, b.source_id, b.langue, b.patient_id, b.personne_concernee_id,
                 b.destinataire, b.intentions, b.drapeaux, b.note_interne, b.resume, Jsonb(b.analyse_regles),
                 Jsonb(b.analyse_llm) if b.analyse_llm is not None else None, b.modele, b.duree_ms))
        return brouillon_id


class StockageMemoire:
    """Même interface, en mémoire (tests)."""

    def __init__(self):
        self.brouillons: list[BrouillonAEnregistrer] = []

    def deja_traite(self, empreinte: str) -> int | None:
        for i, b in enumerate(self.brouillons, start=1):
            if b.empreinte == empreinte:
                return i
        return None

    def enregistrer(self, b: BrouillonAEnregistrer) -> int:
        self.brouillons.append(b)
        return len(self.brouillons)
