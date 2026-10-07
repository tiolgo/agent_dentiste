"""Configuration : variables d'environnement (ou fichier .env à la racine du projet).

Les valeurs par défaut correspondent à l'environnement de test (docker-compose fourni,
serveur Ollama du réseau local).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

RACINE_PROJET = Path(__file__).resolve().parent.parent


def _lire_fichier_env(chemin: Path) -> None:
    """Charge un fichier .env minimal (CLE=valeur) sans écraser les variables déjà définies."""
    if not chemin.is_file():
        return
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        os.environ.setdefault(cle.strip(), valeur.strip().strip("\"'"))


def _booleen(valeur: str | None, defaut: bool) -> bool:
    if valeur is None or not valeur.strip():
        return defaut
    return valeur.strip().lower() in {"1", "true", "vrai", "oui", "yes", "on"}


@dataclass(frozen=True)
class Config:
    pg_hote: str
    pg_port: int
    pg_base: str
    pg_utilisateur: str          # rôle restreint, utilisé pour traiter les mails
    pg_mot_de_passe: str
    pg_admin_utilisateur: str    # propriétaire de la base : installation uniquement
    pg_admin_mot_de_passe: str
    ollama_url: str
    ollama_modele: str
    ollama_timeout: float
    ollama_think: bool | None    # None : paramètre non envoyé (modèles sans « réflexion »)
    llm_actif: bool
    dossier_documents: Path      # racine des documents (attestations générées)
    dossier_sorties: Path        # rapports de traitement
    date_reference: date | None  # None : date du jour

    def parametres_connexion(self, admin: bool = False) -> dict:
        return {
            "host": self.pg_hote,
            "port": self.pg_port,
            "dbname": self.pg_base,
            "user": self.pg_admin_utilisateur if admin else self.pg_utilisateur,
            "password": self.pg_admin_mot_de_passe if admin else self.pg_mot_de_passe,
            "connect_timeout": 5,
            "application_name": "assistant_mails",
        }

    def avec(self, **changements) -> "Config":
        return replace(self, **changements)


# Modèles « à réflexion » : on désactive la réflexion (réponse directe, plus rapide, JSON seul).
_MODELES_A_REFLEXION = ("qwen3", "deepseek-r1", "qwq", "magistral")


def charger_config() -> Config:
    _lire_fichier_env(RACINE_PROJET / ".env")
    env = os.environ.get
    date_ref = env("DATE_REFERENCE")
    modele = env("OLLAMA_MODELE", "qwen3:8b")
    think = env("OLLAMA_THINK")
    if think:
        reflexion = _booleen(think, False)
    else:
        reflexion = False if modele.startswith(_MODELES_A_REFLEXION) else None
    return Config(
        pg_hote=env("PG_HOTE", "localhost"),
        pg_port=int(env("PG_PORT", "5433")),
        pg_base=env("PG_BASE", "dentagest"),
        pg_utilisateur=env("PG_UTILISATEUR", "assistant_mails"),
        pg_mot_de_passe=env("PG_MOT_DE_PASSE", "assistant_mails_test"),
        pg_admin_utilisateur=env("PG_ADMIN_UTILISATEUR", "cabinet"),
        pg_admin_mot_de_passe=env("PG_ADMIN_MOT_DE_PASSE", "cabinet"),
        ollama_url=env("OLLAMA_URL", "http://192.168.1.124:11434").rstrip("/"),
        ollama_modele=modele,
        ollama_timeout=float(env("OLLAMA_TIMEOUT", "120")),
        ollama_think=reflexion,
        llm_actif=_booleen(env("LLM_ACTIF"), True),
        dossier_documents=Path(env("DOSSIER_DOCUMENTS", str(RACINE_PROJET / "documents"))),
        dossier_sorties=Path(env("DOSSIER_SORTIES", str(RACINE_PROJET / "sorties"))),
        date_reference=date.fromisoformat(date_ref) if date_ref else None,
    )
