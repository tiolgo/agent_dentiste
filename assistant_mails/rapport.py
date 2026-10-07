"""Restitution : affichage console, rapport Markdown et JSON d'un lot traité."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .pipeline import Resultat

RANG_PRIORITE = {"urgente": 0, "haute": 1, "normale": 2, "basse": 3}


def trier_pile(resultats: list[Resultat]) -> list[Resultat]:
    return sorted((r for r in resultats if r.brouillon_id),
                  key=lambda r: (RANG_PRIORITE.get(r.priorite, 2), r.brouillon_id or 0))


def _entete(r: Resultat) -> str:
    return f"Mail {r.mail.source_id} — {r.mail.expediteur} — « {r.mail.sujet} »"


def afficher_console(resultats: list[Resultat], details: bool = True) -> None:
    for r in resultats:
        print("=" * 78)
        print(_entete(r))
        if r.deja_traite:
            print(f"Déjà traité (brouillon n° {r.brouillon_id}) — ignoré. Utiliser --retraiter pour forcer.")
            continue
        if r.erreur and not r.brouillon_id:
            print(f"ERREUR : {r.erreur}")
            continue
        print(f"Brouillon n° {r.brouillon_id} | priorité {r.priorite.upper()} | catégorie : {r.categorie} | "
              f"statut : {r.statut} | langue : {r.langue}")
        print("Pièces jointes : " + (", ".join(r.pieces) if r.pieces else "aucune"))
        if details:
            print("--- Réponse proposée " + "-" * 57)
            print(r.reponse if r.reponse else "(aucune réponse proposée)")
            print("--- Note interne (secrétariat, jamais envoyée) " + "-" * 31)
            print(r.note)
    print("=" * 78)
    print("PILE DU SECRÉTARIAT (ordre de traitement)")
    for r in trier_pile(resultats):
        if r.deja_traite:
            continue
        print(f"  [{r.priorite.upper():8}] n° {r.brouillon_id:<4} {r.categorie[:40]:40} {r.mail.expediteur} "
              f"({r.statut})")


def ecrire_markdown(resultats: list[Resultat], chemin: Path, contexte: dict) -> Path:
    lignes = [f"# Brouillons produits — {contexte.get('source', '')}", ""]
    lignes += [f"- Date de traitement : {datetime.now():%d/%m/%Y %H:%M}",
               f"- Date de référence : {contexte.get('date_reference', '')}",
               f"- Lecture automatique : {contexte.get('lecture', '')}", ""]
    lignes += ["## Pile du secrétariat (ordre de traitement)", "",
               "| Priorité | Brouillon | Mail | Expéditeur | Catégorie | Statut | Langue | Pièces jointes |",
               "|---|---|---|---|---|---|---|---|"]
    for r in trier_pile(resultats):
        if r.deja_traite:
            continue
        lignes.append(f"| **{r.priorite}** | n° {r.brouillon_id} | {r.mail.source_id} | {r.mail.expediteur} | "
                      f"{r.categorie} | {r.statut} | {r.langue} | {', '.join(r.pieces) or '—'} |")
    lignes.append("")
    for r in sorted(resultats, key=lambda x: int(x.mail.source_id) if str(x.mail.source_id).isdigit() else 0):
        lignes += ["---", "", f"## {_entete(r)}", ""]
        if r.deja_traite:
            lignes += [f"Déjà traité (brouillon n° {r.brouillon_id}).", ""]
            continue
        lignes += ["**Mail reçu**", "", "```text", r.mail.corps.strip(), "```", ""]
        lignes += [f"- **Brouillon** : n° {r.brouillon_id}",
                   f"- **Priorité** : {r.priorite}",
                   f"- **Catégorie** : {r.categorie}",
                   f"- **Statut** : {r.statut}",
                   f"- **Langue de la réponse** : {r.langue}",
                   f"- **Pièces jointes** : {', '.join(r.pieces) if r.pieces else 'aucune'}", ""]
        lignes += ["**Réponse proposée**", ""]
        lignes += (["```text", r.reponse, "```"] if r.reponse else ["_(aucune réponse proposée)_"])
        lignes += ["", "**Note interne pour le secrétariat** (jamais envoyée)", "", "```text", r.note, "```", ""]
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text("\n".join(lignes), encoding="utf-8")
    return chemin


def ecrire_json(resultats: list[Resultat], chemin: Path) -> Path:
    donnees = [{
        "mail_id": r.mail.source_id, "expediteur": r.mail.expediteur, "sujet": r.mail.sujet,
        "brouillon_id": r.brouillon_id, "priorite": r.priorite, "categorie": r.categorie, "statut": r.statut,
        "langue": r.langue, "pieces_jointes": r.pieces, "reponse_proposee": r.reponse, "note_interne": r.note,
        "intentions": r.intentions, "drapeaux": r.drapeaux, "lecture": r.lecture, "deja_traite": r.deja_traite,
        "erreur": r.erreur,
    } for r in resultats]
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
    return chemin
