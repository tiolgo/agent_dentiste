"""Ligne de commande.

  python -m assistant_mails installer              une fois : schéma « assistant » + rôle restreint
  python -m assistant_mails verifier               base, droits, serveur Ollama, cohérence des tarifs
  python -m assistant_mails traiter mails.json     traite un lot et écrit les brouillons
  python -m assistant_mails pile                   affiche la pile du secrétariat (urgences d'abord)
  python -m assistant_mails reinitialiser --oui    TEST : efface les brouillons produits par l'assistant
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

import psycopg

from .config import RACINE_PROJET, Config, charger_config
from .connaissances import verifier_coherence
from .dossier import DossierPostgres
from .entree import charger
from .installation import installer, reinitialiser_test
from .llm import ClientOllama, LecteurLLM
from .pipeline import Assistant
from .rapport import afficher_console, ecrire_json, ecrire_markdown
from .stockage import StockagePostgres


def _connexion(config: Config, admin: bool = False) -> psycopg.Connection:
    try:
        return psycopg.connect(**config.parametres_connexion(admin=admin), autocommit=True)
    except psycopg.OperationalError as e:
        compte = config.pg_admin_utilisateur if admin else config.pg_utilisateur
        print(f"Connexion impossible à PostgreSQL ({config.pg_hote}:{config.pg_port}/{config.pg_base}, compte "
              f"« {compte} ») : {str(e).strip()}", file=sys.stderr)
        if not admin:
            print("→ Le rôle restreint a-t-il été créé ? Lancer : python -m assistant_mails installer", file=sys.stderr)
        raise SystemExit(2)


def _client(config: Config) -> ClientOllama:
    return ClientOllama(config.ollama_url, config.ollama_modele, config.ollama_timeout, config.ollama_think)


def cmd_traiter(args, config: Config) -> int:
    ref = args.date_reference or config.date_reference or date.today()
    mails = charger(args.source)
    if not mails:
        print(f"Aucun e-mail trouvé dans {args.source}.", file=sys.stderr)
        return 1
    lecteur, lecture = None, "règles seules (LLM désactivé)"
    if config.llm_actif and not args.sans_llm:
        client = _client(config)
        disponible, message = client.verifier()
        if disponible:
            lecteur, lecture = LecteurLLM(client, ref), f"règles + LLM ({client.modele} sur {client.url})"
        else:
            lecture = f"règles seules — LLM indisponible ({message})"
            print(f"⚠ LLM indisponible : {message}\n  → traitement en mode dégradé : règles seules, sans perte de "
                  "sécurité, avec davantage de champs « à compléter ».", file=sys.stderr)
    print(f"{len(mails)} e-mail(s) à traiter — date de référence {ref:%d/%m/%Y} — lecture : {lecture}")
    with _connexion(config) as cx:
        assistant = Assistant(DossierPostgres(cx), StockagePostgres(cx), ref, config.dossier_documents, lecteur,
                              etat_sans_llm=lecture)
        resultats = assistant.traiter_lot(mails, retraiter=args.retraiter)
    afficher_console(resultats, details=not args.resume)
    rapport = args.rapport or (config.dossier_sorties / f"sortie_{args.source.stem}.md")
    contexte = {"source": args.source.name, "date_reference": f"{ref:%d/%m/%Y}", "lecture": lecture}
    ecrire_markdown(resultats, rapport, contexte)
    ecrire_json(resultats, rapport.with_suffix(".json"))
    print(f"\nRapport : {rapport}  (et {rapport.with_suffix('.json').name})")
    erreurs = [r for r in resultats if r.erreur]
    if erreurs:
        print(f"⚠ {len(erreurs)} mail(s) en erreur : brouillons « à traiter manuellement » créés.", file=sys.stderr)
    return 1 if any(r.erreur and not r.brouillon_id for r in resultats) else 0


def cmd_pile(args, config: Config) -> int:
    with _connexion(config) as cx:
        lignes = cx.execute(
            "SELECT brouillon, priorite, categorie, statut, expediteur, sujet, pieces_jointes, note_interne, "
            "reponse_proposee FROM assistant.pile ORDER BY rang, brouillon").fetchall()
    if not lignes:
        print("Pile vide : aucun brouillon à valider.")
    for b, priorite, categorie, statut, expediteur, sujet, pieces, note, reponse in lignes:
        print(f"[{priorite.upper():8}] n° {b:<4} {categorie} — {expediteur} — « {sujet} » ({statut})"
              + (f" — PJ : {', '.join(pieces)}" if pieces else ""))
        if args.details:
            print("    " + (note or "").replace("\n", "\n    "))
            print("    --- réponse ---\n    " + (reponse or "(aucune)").replace("\n", "\n    ") + "\n")
    return 0


def cmd_verifier(args, config: Config) -> int:
    ok = True
    print(f"Base : {config.pg_hote}:{config.pg_port}/{config.pg_base}, rôle « {config.pg_utilisateur} »")
    try:
        with psycopg.connect(**config.parametres_connexion(), autocommit=True) as cx:
            n = cx.execute("SELECT count(*) FROM patients").fetchone()[0]
            print(f"  ✔ connexion OK ({n} patients)")
            try:
                cx.execute("SELECT motif FROM rendez_vous LIMIT 1")
                print("  ✘ ATTENTION : ce rôle peut lire le motif des rendez-vous (relancer « installer »)")
                ok = False
            except psycopg.errors.InsufficientPrivilege:
                print("  ✔ le motif des rendez-vous est illisible pour l'assistant (droits par colonne)")
    except psycopg.Error as e:
        print(f"  ✘ {str(e).strip()}")
        ok = False
    client = _client(config)
    disponible, message = client.verifier()
    print(f"LLM : {'✔' if disponible else '✘'} {message}")
    ecarts = verifier_coherence(RACINE_PROJET / "infos_cabinet.md")
    print("Tarifs et coordonnées : " + ("✔ cohérents avec infos_cabinet.md" if not ecarts else "✘ " + " ; ".join(ecarts)))
    return 0 if ok and not ecarts else 1


def cmd_installer(args, config: Config) -> int:
    with _connexion(config, admin=True) as cx:
        for etape in installer(cx, config.pg_base, config.pg_utilisateur, config.pg_mot_de_passe,
                               creer_role=not args.sans_role):
            print(f"✔ {etape}")
    return 0


def cmd_reinitialiser(args, config: Config) -> int:
    if not args.oui:
        print("Environnement de TEST uniquement : supprime les brouillons créés par l'assistant. Ajouter --oui.")
        return 1
    with _connexion(config, admin=True) as cx:
        print(f"{reinitialiser_test(cx)} brouillon(s) supprimé(s).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m assistant_mails",
                                     description="Assistant de tri des e-mails — Cabinet dentaire Dr Reuter & associés")
    sous = parser.add_subparsers(dest="commande", required=True)
    p = sous.add_parser("traiter", help="traiter un lot d'e-mails (JSON, .eml ou dossier de .eml)")
    p.add_argument("source", type=Path)
    p.add_argument("--sans-llm", action="store_true", help="règles seules (sans appel au LLM)")
    p.add_argument("--date-reference", type=date.fromisoformat, help="date « du jour » (AAAA-MM-JJ)")
    p.add_argument("--retraiter", action="store_true", help="retraiter des mails déjà traités")
    p.add_argument("--rapport", type=Path, help="chemin du rapport Markdown (défaut : sorties/sortie_<source>.md)")
    p.add_argument("--resume", action="store_true", help="n'afficher que la pile, sans le détail des brouillons")
    sous.add_parser("installer", help="créer le schéma et le rôle restreint (compte propriétaire)") \
        .add_argument("--sans-role", action="store_true", help="ne pas créer le rôle restreint")
    sous.add_parser("verifier", help="vérifier base, droits, LLM et cohérence des tarifs")
    pile = sous.add_parser("pile", help="afficher la pile du secrétariat")
    pile.add_argument("--details", action="store_true")
    r = sous.add_parser("reinitialiser", help="TEST : effacer les brouillons créés par l'assistant")
    r.add_argument("--oui", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s : %(message)s")
    config = charger_config()
    commandes = {"traiter": cmd_traiter, "pile": cmd_pile, "verifier": cmd_verifier, "installer": cmd_installer,
                 "reinitialiser": cmd_reinitialiser}
    return commandes[args.commande](args, config)


if __name__ == "__main__":
    sys.exit(main())
