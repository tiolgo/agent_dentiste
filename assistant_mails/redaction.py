"""Mise en forme : réponse proposée (blocs pré-validés) et note interne pour le secrétariat."""

from __future__ import annotations

from dataclasses import dataclass, field

from .connaissances import ADRESSE, DOCTENA, HORAIRES, NOM_CABINET, TARIFS, TELEPHONE, formater_date, formater_heure
from .decision import Bloc, Decision
from .modeles import Analyse
from .textes import A_COMPLETER, TEXTES

_REMPLACENT_INTRO = {"rdv_retard"}          # blocs qui commencent déjà par un remerciement
_AVEC_JOUR = {"attestation_jointe", "rdv_deplacer", "rdv_annuler", "rdv_confirmer", "rdv_manque"}
_SEPARATEUR_LISTE = {"fr": " ; ", "de": "; ", "en": "; ", "pt": "; ", "lb": "; "}


@dataclass
class Reponse:
    texte: str
    segments: list[tuple[Bloc, str]] = field(default_factory=list)


def rendre_bloc(bloc: Bloc, langue: str) -> str:
    p = {"tel": TELEPHONE, "horaires": HORAIRES[langue], "doctena": DOCTENA[langue], "adresse": ADRESSE,
         "cabinet": NOM_CABINET, "rappel": ""}
    params = bloc.params
    if "nom" in params:
        p["nom"] = params["nom"]
    if bloc.cle == "urgence" and params.get("rappel"):
        p["rappel"] = TEXTES["urgence_rappel"][langue]
    if "numero" in params:
        p["numero"] = params["numero"]
    if "date" in params:
        p["date"] = formater_date(params["date"], langue, jour_semaine=bloc.cle in _AVEC_JOUR)
    if "heure" in params:
        p["heure"] = formater_heure(params["heure"], langue)
    if "factures" in params:
        p["liste"] = _SEPARATEUR_LISTE[langue].join(
            TEXTES["facture_element"][langue].format(numero=n, date=formater_date(d, langue, False))
            for n, d in params["factures"])
    if "actes" in params:
        p["lignes"] = "\n".join("- " + TARIFS[acte][langue] for acte in params["actes"])
    texte = TEXTES[bloc.cle][langue].format(**p)
    if bloc.a_completer:
        texte += "\n" + A_COMPLETER.format(raison=bloc.a_completer)
    return texte


def rediger(decision: Decision) -> Reponse | None:
    """Assemble la réponse proposée ; None si aucune réponse ne doit être envoyée."""
    if decision.sans_reponse:
        return None
    langue = decision.langue
    salutation = (Bloc("salutation_nom", {"nom": decision.nom_salutation}) if decision.nom_salutation
                  else Bloc("salutation"))
    segments = [(salutation, rendre_bloc(salutation, langue))]
    segments += [(b, rendre_bloc(b, langue)) for b in decision.blocs]
    for cle in ("conclusion", "signature"):
        b = Bloc(cle)
        segments.append((b, rendre_bloc(b, langue)))

    paragraphes: list[str] = []
    intro = ""
    for bloc, texte in segments:
        if bloc.cle == "intro":          # « Merci pour votre message. » ouvre le premier paragraphe
            intro = texte
            continue
        if intro and bloc.cle in _REMPLACENT_INTRO:
            pass
        elif intro and bloc.cle not in ("conclusion", "signature"):
            texte = f"{intro} {texte}"
        elif intro:
            paragraphes.append(intro)
        intro = ""
        paragraphes.append(texte)
    return Reponse(texte="\n\n".join(paragraphes), segments=segments)


def composer_note(decision: Decision, analyse: Analyse, etat_lecture: str, pieces: list[str],
                  garde_fous: list[str]) -> str:
    """Note interne (jamais envoyée) : ce qu'il faut faire, ce que le système a constaté, ses limites."""
    lignes: list[str] = []
    if "urgence" in decision.drapeaux:
        lignes.append("⚠ URGENCE POSSIBLE — À TRAITER IMMÉDIATEMENT.")
    if "suspect" in decision.drapeaux:
        lignes.append("⚠ MESSAGE SUSPECT — NE PAS RÉPONDRE.")
    a_faire = list(decision.actions)
    if decision.a_completer and not decision.sans_reponse:
        a_faire.append("Compléter les passages [[À COMPLÉTER...]] de la réponse avant envoi.")
    if a_faire:
        lignes.append("À faire :")
        lignes += [f"  - {a}" for a in a_faire]
    if analyse.resume:
        lignes.append(f"Résumé : {analyse.resume}")
    if analyse.questions_ouvertes:
        lignes.append("Questions posées (vérifier qu'une réponse est apportée à chacune) :")
        lignes += [f"  - {q}" for q in analyse.questions_ouvertes]
    if decision.notes:
        lignes.append("Constats :")
        lignes += [f"  - {n}" for n in decision.notes]
    if not decision.sans_reponse:
        lignes.append(f"Répondre uniquement à : {decision.destinataire} — langue : {decision.langue} "
                      f"({decision.langue_raison}).")
        lignes.append("Pièces jointes : " + (", ".join(pieces) if pieces else "aucune") + ".")
    lignes.append(f"Lecture automatique : {etat_lecture}.")
    if analyse.divergences:
        lignes.append("Points de désaccord entre les deux lectures (à vérifier) :")
        lignes += [f"  - {x}" for x in analyse.divergences]
    if garde_fous:
        lignes.append("GARDE-FOU DÉCLENCHÉ — le brouillon automatique a été bloqué :")
        lignes += [f"  - {g}" for g in garde_fous]
    return "\n".join(lignes)
