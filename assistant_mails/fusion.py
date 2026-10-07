"""Fusion de la lecture par règles et de la lecture par le LLM.

Règle d'or :
- sécurité (urgence, question médicale, suspicion) : on garde le plus prudent des deux,
  le LLM ne peut jamais faire baisser un signal détecté par les règles ;
- compréhension fine (intentions, personne concernée, dates, période) : le LLM prime,
  les règles servent de secours et de contre-vérification ;
- toute divergence notable est consignée pour la secrétaire.
"""

from __future__ import annotations

from .modeles import LANGUES, Analyse, rang_suspicion, rang_urgence

_LIBELLE_LANGUE = {"fr": "français", "de": "allemand", "en": "anglais", "pt": "portugais", "lb": "luxembourgeois"}


def _langue(regles: Analyse, llm: Analyse) -> tuple[str | None, float, str | None]:
    r, c, l = regles.langue, regles.langue_confiance, llm.langue
    if r and l and r == l:
        return r, max(c, 0.9), None
    if r and r not in LANGUES and c >= 0.3:
        # langue non prise en charge reconnue par les règles : le LLM a tendance à la « ranger » dans une
        # langue connue (italien lu comme allemand) ; on garde la langue réelle, la réponse partira en français
        return r, c, f"langue : règles = {r} (non prise en charge), LLM = {_LIBELLE_LANGUE.get(l, l)} → {r} retenu"
    if not r and regles.nb_mots < 6:
        return None, 0.0, None          # texte quasi vide : pas de devinette, langue du dossier ou français
    if not l:
        return r, c, None
    if not r:
        return l, 0.7, None
    ecart = f"langue : règles = {_LIBELLE_LANGUE.get(r, r)}, LLM = {_LIBELLE_LANGUE.get(l, l)}"
    # Marqueurs luxembourgeois nets : les modèles confondent volontiers lb et de.
    if r == "lb" and c >= 0.5:
        return "lb", c, ecart + " → luxembourgeois retenu (marqueurs nets)"
    if c >= 0.75:
        return r, c, ecart + f" → {_LIBELLE_LANGUE.get(r, r)} retenu (marqueurs nets)"
    return l, 0.7, ecart + f" → {_LIBELLE_LANGUE.get(l, l)} retenu"


def _union(*listes: list[str]) -> list[str]:
    vus: list[str] = []
    for liste in listes:
        for x in liste:
            if x not in vus:
                vus.append(x)
    return vus


def fusionner(regles: Analyse, llm: Analyse | None) -> Analyse:
    if llm is None:
        return regles
    f = Analyse(source="regles+llm", nb_mots=regles.nb_mots)
    f.langue, f.langue_confiance, ecart = _langue(regles, llm)
    if ecart:
        f.divergences.append(ecart)

    # Intentions : le LLM prime ; les règles complètent s'il n'a rien trouvé.
    intentions = list(llm.intentions) if set(llm.intentions) - {"autre"} else list(regles.intentions)
    # Intentions que les règles repèrent sur un vocabulaire explicite et très fiable : conservées même si le LLM
    # les manque (vu en réel : une réclamation allemande lue comme une demande d'information).
    for fiable in ("question_medicale", "message_automatique", "reclamation"):
        if fiable in regles.intentions and fiable not in intentions:
            intentions.append(fiable)
            f.divergences.append(f"« {fiable.replace('_', ' ')} » repéré par les règles mais pas par le LLM : conservé")
    if "autre" in intentions and len(intentions) > 1:
        intentions.remove("autre")
    if ("question_facturation" in intentions and "question_tarif" in intentions
            and not regles.indice_facturation):
        # vu en réel : « combien coûte un détartrage ? » étiqueté aussi « facturation » ; sans aucun mot de
        # facturation (payé, facturé, frais...), c'est la même question que le tarif, déjà traitée
        intentions.remove("question_facturation")
        f.divergences.append("« facturation » proposé par le LLM sans aucun mot de facturation dans le message : "
                             "traité comme une question de tarif")
    manques = [i for i in regles.intentions if i not in intentions and i not in ("autre",)]
    if manques:
        f.divergences.append("repéré par les règles seulement (non retenu) : " + ", ".join(m.replace("_", " ") for m in manques))
    f.intentions = intentions

    # Sécurité : le plus prudent des deux.
    f.urgence = max(regles.urgence, llm.urgence, key=rang_urgence)
    f.signes_urgence = _union(regles.signes_urgence, llm.signes_urgence)
    f.question_medicale = regles.question_medicale or llm.question_medicale
    if f.question_medicale and "question_medicale" not in f.intentions:
        f.intentions.append("question_medicale")
    f.suspect = max(regles.suspect, llm.suspect, key=rang_suspicion)
    f.raisons_suspect = _union(regles.raisons_suspect, llm.raisons_suspect)
    if llm.urgence != regles.urgence:
        f.divergences.append(f"urgence : règles = {regles.urgence}, LLM = {llm.urgence} → {f.urgence} retenu")
    if llm.suspect != regles.suspect:
        f.divergences.append(f"suspicion : règles = {regles.suspect}, LLM = {llm.suspect} → {f.suspect} retenu")

    # Sens de la demande : LLM d'abord, règles en secours.
    f.personne_concernee = llm.personne_concernee if llm.personne_concernee != "inconnu" else regles.personne_concernee
    if (regles.personne_concernee not in ("expediteur", "inconnu")
            and f.personne_concernee != regles.personne_concernee):
        f.divergences.append(f"personne concernée : règles = {regles.personne_concernee}, LLM = {llm.personne_concernee}")
    f.prenom_concerne = llm.prenom_concerne or regles.prenom_concerne
    f.nom_concerne = llm.nom_concerne or regles.nom_concerne
    f.toutes_factures = llm.toutes_factures or regles.toutes_factures

    # Faits littéraux (dates, période, numéro, signature) : les règles d'abord quand elles en ont trouvé —
    # les petits modèles calculent mal les dates (« contrôle de septembre » lu « 2025 ») ; le LLM complète.
    f.nom_signature = regles.nom_signature or llm.nom_signature
    f.facture_numero = regles.facture_numero or llm.facture_numero
    if regles.periode_mois or regles.periode_annee:           # la période forme un tout (mois + année)
        f.periode_mois, f.periode_annee = regles.periode_mois, regles.periode_annee
    else:
        f.periode_mois, f.periode_annee = llm.periode_mois, llm.periode_annee
    if (llm.periode_mois, llm.periode_annee) not in ((0, 0), (f.periode_mois, f.periode_annee)):
        f.divergences.append(f"période : règles = {regles.periode_mois or '?'}/{regles.periode_annee or '?'}, "
                             f"LLM = {llm.periode_mois or '?'}/{llm.periode_annee or '?'} → "
                             f"{f.periode_mois or '?'}/{f.periode_annee or '?'} retenu")
    f.dates = list(regles.dates) if any(d.jour for d in regles.dates) else _union(regles.dates, llm.dates)
    def compatibles(a, b) -> bool:      # même jour et même mois ; année identique ou absente d'un côté
        return a.jour == b.jour and a.mois == b.mois and (a.annee is None or b.annee is None or a.annee == b.annee)
    if any(not any(compatibles(d, r) for r in f.dates) for d in llm.dates):
        f.divergences.append("date : LLM = " + ", ".join(map(str, llm.dates)) + " ; retenu : "
                             + (", ".join(map(str, f.dates)) or "aucune"))
    f.plage = regles.plage
    f.heure_rdv = regles.heure_rdv or llm.heure_rdv
    # Actions sur les rendez-vous : expressions explicites (« missed », « verschieben », « remarcar »...) repérées
    # par les règles d'abord ; vu en réel : le LLM en oublie (« missed ») ou en invente (« retard »).
    f.actions_rdv = list(regles.actions_rdv) or list(llm.actions_rdv)
    if regles.actions_rdv and llm.actions_rdv and set(regles.actions_rdv) != set(llm.actions_rdv):
        f.divergences.append(f"rendez-vous : règles = {', '.join(regles.actions_rdv)}, LLM = "
                             f"{', '.join(llm.actions_rdv)} → règles retenues")
    f.type_attestation = "medicale" if "medicale" in (llm.type_attestation, regles.type_attestation) else "presence"
    f.actes_tarif = llm.actes_tarif or regles.actes_tarif
    f.question_remboursement = llm.question_remboursement or regles.question_remboursement
    f.infos_demandees = llm.infos_demandees or regles.infos_demandees
    f.envoi_autre_adresse = llm.envoi_autre_adresse or regles.envoi_autre_adresse
    f.questions_ouvertes = llm.questions_ouvertes or regles.questions_ouvertes
    f.resume = llm.resume or regles.resume
    return f
