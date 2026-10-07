"""Chargement des e-mails à traiter.

Formats acceptés :
- fichier JSON au format de mails_dev.json : liste de {"id", "de", "sujet", "corps"}
  (clés anglaises from/subject/body également acceptées, ainsi que "repondre_a"/"reply_to") ;
- fichier .eml (export d'une messagerie) ou dossier contenant des .eml.
"""

from __future__ import annotations

import json
from email import policy
from email.parser import BytesParser
from pathlib import Path

from .modeles import Mail
from .normalisation import preparer_mail


def _premier(d: dict, *cles: str) -> str:
    for cle in cles:
        valeur = d.get(cle)
        if valeur:
            return str(valeur)
    return ""


def lire_json(chemin: Path) -> list[Mail]:
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    if isinstance(donnees, dict):
        donnees = donnees.get("mails") or donnees.get("emails") or [donnees]
    mails = []
    for position, d in enumerate(donnees, start=1):
        if not isinstance(d, dict):
            continue
        mails.append(preparer_mail(
            expediteur_brut=_premier(d, "de", "from", "expediteur", "sender"),
            sujet=_premier(d, "sujet", "subject", "objet"),
            corps=_premier(d, "corps", "body", "texte", "message", "contenu"),
            source_id=str(d.get("id", position)),
            repondre_a=_premier(d, "repondre_a", "reply_to", "reply-to") or None))
    return mails


def lire_eml(chemin: Path) -> Mail:
    with chemin.open("rb") as f:
        message = BytesParser(policy=policy.default).parse(f)
    partie = message.get_body(preferencelist=("plain", "html"))
    corps = partie.get_content() if partie is not None else ""
    return preparer_mail(str(message.get("From", "")), str(message.get("Subject", "")), corps,
                         source_id=chemin.name, repondre_a=str(message.get("Reply-To", "")) or None)


def charger(chemin: Path) -> list[Mail]:
    chemin = Path(chemin)
    if chemin.is_dir():
        return [lire_eml(f) for f in sorted(chemin.glob("*.eml"))]
    if chemin.suffix.lower() == ".eml":
        return [lire_eml(chemin)]
    return lire_json(chemin)
