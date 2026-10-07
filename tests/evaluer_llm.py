"""Évaluation d'un modèle réel sur les 56 mails de test (10 de développement + 46 pièges), sans rien écrire en base.

    .venv/bin/python -m tests.evaluer_llm                       # modèle de la configuration (.env)
    .venv/bin/python -m tests.evaluer_llm --modele mistral-small3.2 --jeu pieges

Pour chaque mail : temps de lecture, fiche du LLM, brouillon obtenu, écarts aux attentes et violations des
règles 1 à 4. À rejouer avant toute mise en service ou changement de modèle.
"""

from __future__ import annotations

import argparse
import json
import logging
import tempfile
import time
import urllib.request
from pathlib import Path

from assistant_mails.config import charger_config
from assistant_mails.llm import ClientOllama, ErreurLLM, LecteurLLM
from assistant_mails.pipeline import Assistant
from assistant_mails.stockage import StockageMemoire

from tests.donnees_test import REF, dossier_test, mails_dev, mails_pieges, violations
from tests.test_pipeline import ATTENDUS_DEV


def ecarts(res, attendu: dict) -> list[str]:
    e = []
    for cle in ("priorite", "statut"):
        if cle in attendu and getattr(res, cle) != attendu[cle]:
            e.append(f"{cle} {getattr(res, cle)} ≠ {attendu[cle]}")
    if "categorie" in attendu and res.categorie != attendu["categorie"]:
        e.append(f"catégorie « {res.categorie} » ≠ « {attendu['categorie']} »")
    if "langue" in attendu and res.reponse and res.langue != attendu["langue"]:
        e.append(f"langue {res.langue} ≠ {attendu['langue']}")
    if "pieces" in attendu and sorted(res.pieces) != sorted(attendu["pieces"]):
        e.append(f"pièces {res.pieces} ≠ {attendu['pieces']}")
    if "sans_reponse" in attendu and (res.reponse is None) != attendu["sans_reponse"]:
        e.append("réponse proposée alors qu'aucune n'était attendue" if attendu["sans_reponse"] else "aucune réponse")
    if "reponse" in attendu and attendu["reponse"] is None and res.reponse is not None:
        e.append("réponse proposée alors qu'aucune n'était attendue")
    e += [f"réponse contient « {c} »" for c in attendu.get("absent", []) if c in (res.reponse or "")]
    e += [f"catégorie sans « {c} »" for c in attendu.get("categorie_contient", []) if c not in res.categorie]
    e += [f"réponse sans « {c} »" for c in attendu.get("reponse_contient", []) + attendu.get("contient", [])
          if c not in (res.reponse or "")]
    return e


class LecteurChronometre:
    """Enveloppe le lecteur LLM : mesure le temps, garde la fiche, attend le serveur si le réseau tombe."""

    def __init__(self, lecteur: LecteurLLM, url: str, attendre_reseau: bool):
        self.lecteur, self.url, self.attendre_reseau = lecteur, url, attendre_reseau
        self.nom = lecteur.nom
        self.fiches: dict[str, tuple[dict, float]] = {}

    def prechauffer(self):
        self.lecteur.prechauffer()

    def _serveur_revenu(self, delai: int = 600) -> bool:
        debut = time.monotonic()
        while time.monotonic() - debut < delai:
            try:
                urllib.request.urlopen(self.url + "/api/version", timeout=3).read()
                return True
            except Exception:
                time.sleep(5)
        return False

    def lire(self, mail):
        for essai in range(2):
            debut = time.monotonic()
            try:
                analyse, fiche, meta = self.lecteur.lire(mail)
                self.fiches[mail.source_id] = (fiche, round(time.monotonic() - debut, 1))
                return analyse, fiche, meta
            except ErreurLLM:
                if essai == 1 or not self.attendre_reseau or not self._serveur_revenu():
                    raise


def main() -> int:
    config = charger_config()
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--modele", default=config.ollama_modele)
    p.add_argument("--jeu", choices=("dev", "pieges", "tout"), default="tout")
    p.add_argument("--sortie", type=Path, help="fichier JSON détaillé (fiches, brouillons, écarts)")
    p.add_argument("--sans-attente-reseau", action="store_true", help="ne pas attendre le serveur s'il décroche")
    args = p.parse_args()
    logging.getLogger("assistant_mails").setLevel(logging.WARNING)

    think = config.ollama_think if args.modele == config.ollama_modele else (
        False if args.modele.startswith(("qwen3", "deepseek-r1", "qwq", "magistral")) else None)
    client = ClientOllama(config.ollama_url, args.modele, config.ollama_timeout, think, essais=0)
    disponible, message = client.verifier()
    print(message)
    if not disponible:
        return 2
    lecteur = LecteurChronometre(LecteurLLM(client, REF), config.ollama_url, not args.sans_attente_reseau)
    assistant = Assistant(dossier_test(), StockageMemoire(), REF, Path(tempfile.mkdtemp()), lecteur,
                          alerter=lambda *a: None)
    dossier = dossier_test()
    jeu = []
    if args.jeu in ("dev", "tout"):
        jeu += [(m, ATTENDUS_DEV[m.source_id]) for m in mails_dev()]
    if args.jeu in ("pieges", "tout"):
        jeu += mails_pieges()

    details, nb_ecarts, nb_violations, durees = [], 0, 0, []
    for mail, attendu in jeu:
        res = assistant.traiter(mail, retraiter=True)
        fiche, duree = lecteur.fiches.get(mail.source_id, (None, 0.0))
        v, e = violations(res, dossier), ecarts(res, attendu)
        nb_violations += bool(v)
        nb_ecarts += bool(e)
        if fiche is not None:
            durees.append(duree)
        lecture = f"{duree:5.1f} s" if fiche is not None else ("urgence" if "urgence" in res.lecture else " règles")
        print(f"{'OK ' if not (v or e) else 'KO '} #{mail.source_id:>3} {lecture} [{res.priorite:8}] "
              f"{res.categorie[:38]:38} {res.langue} {res.statut:11} PJ={len(res.pieces)}"
              + (f"  ⚠ VIOLATION {v}" if v else "") + (f"  écarts : {'; '.join(e)}" if e else ""), flush=True)
        details.append({"mail": mail.source_id, "fiche_llm": fiche, "duree_s": duree, "priorite": res.priorite,
                        "categorie": res.categorie, "langue": res.langue, "statut": res.statut, "pieces": res.pieces,
                        "reponse": res.reponse, "note": res.note, "ecarts": e, "violations": v})
    moyenne = sum(durees) / len(durees) if durees else 0
    print(f"\n{args.modele} : {len(jeu)} mails — violations des règles 1 à 4 : {nb_violations} — mails avec écarts "
          f"aux attentes : {nb_ecarts} — lecture LLM moyenne : {moyenne:.1f} s ({len(durees)} lectures)")
    if args.sortie:
        args.sortie.write_text(json.dumps(details, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if nb_violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
