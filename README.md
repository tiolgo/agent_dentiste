# Assistant e-mails — Cabinet dentaire Dr Reuter & associés

Chaque e-mail entrant est lu, classé et **préparé pour Martine** : une réponse proposée dans la langue du
patient, le document joint s'il est autorisé, une priorité, et une note interne qui explique quoi vérifier ou
compléter. **Rien n'est jamais envoyé** : tout arrive dans la table `brouillons`, que Martine relit, complète
et valide.

> Principe d'architecture : **le LLM lit, le code décide, des textes validés à l'avance écrivent.**

- Python 3.11+ ; dépendance unique : `psycopg` (le reste est la bibliothèque standard : `urllib` pour Ollama,
  `email`, `json`…).
- PostgreSQL (docker-compose fourni), LLM local via **Ollama** : `qwen3:8b` par défaut (installé sur le serveur de
  test et validé en réel) ; `mistral-small3.2` (modèle européen de 24 B) recommandé pour le matériel définitif du cabinet.
- Aucune donnée ne quitte le cabinet ; le LLM ne voit jamais le dossier patient.

---

## 1. Démarrage rapide

```bash
# 1) Base de test (copie de DentaGest)
docker compose up -d

# 2) Environnement Python
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
#    (ou : uv venv && uv pip install -r requirements.txt)

# 3) Installation dans la base — une seule fois, avec le compte propriétaire :
#    schéma « assistant » + rôle restreint « assistant_mails »
.venv/bin/python -m assistant_mails installer

# 4) Vérifications : base, droits, serveur Ollama, cohérence des tarifs
.venv/bin/python -m assistant_mails verifier

# 5) Traitement des 10 mails de développement (date de référence du jeu de test)
.venv/bin/python -m assistant_mails traiter mails_dev.json --date-reference 2026-10-07

# 6) La pile de Martine, urgences d'abord
.venv/bin/python -m assistant_mails pile --details
```

Autres commandes :

| Commande | Rôle |
|---|---|
| `traiter FICHIER [--sans-llm] [--retraiter] [--resume] [--rapport chemin.md]` | traite un lot : JSON au format de `mails_dev.json`, fichier `.eml` ou dossier de `.eml` |
| `reinitialiser --oui` | **environnement de test** : efface les brouillons créés par l'assistant |
| `python -m unittest discover -s tests -t .` | 71 tests (sans Docker ni Ollama, sauf `test_integration` qui utilise la base si elle est là) |

Configuration : variables d'environnement ou fichier `.env` (modèle : `.env.example`). Par défaut :
base `localhost:5433/dentagest`, Ollama `http://192.168.1.124:11434`, modèle `qwen3:8b` (réflexion désactivée
automatiquement). Pour passer au modèle européen : `ollama pull mistral-small3.2` sur le serveur, puis
`OLLAMA_MODELE=mistral-small3.2` (il demande une carte graphique de 16 à 24 Go pour rester rapide).

Un mail déjà traité (même expéditeur, objet et texte) n'est pas dédoublé ; `--retraiter` force un nouveau
brouillon. Chaque traitement écrit aussi un rapport `sorties/sortie_<fichier>.md` et `.json`.

---

## 2. Architecture : ce qui est en code, ce qui est en LLM, et pourquoi

```
 e-mail entrant
      │
      ▼
 1. LECTURE PAR RÈGLES (instantanée, toujours exécutée) ─ signes d'urgence, manipulation/usurpation,
      │                                                    langue, dates, mots-clés — 5 langues
      ├──────────► 2. LECTURE PAR LE LLM (Ollama local) ─ reçoit UNIQUEMENT le mail ;
      │                                                    renvoie une fiche JSON contrainte par schéma
      ▼
 3. FUSION PRUDENTE ─ sécurité : le plus prudent des deux ; compréhension fine : le LLM, règles en secours
      ▼
 4. DÉCISION (code) ─ qui écrit ? de qui parle-t-on ? document autorisé ? (autorisation.py)
      │               DentaGest lu en lecture seule, SANS le motif des rendez-vous
      ▼
 5. RÉDACTION ─ assemblage de paragraphes pré-validés, en 5 langues (le LLM n'écrit rien)
      ▼
 6. GARDE-FOUS ─ contrôles indépendants : ré-autorisation des pièces jointes, aucun conseil médical,
      │          aucun vocabulaire de soins, aucune coordonnée d'un tiers, aucun texte du LLM
      ▼
 table brouillons  +  assistant.analyses (note interne)  ──►  Martine relit / complète / valide
```

| Tâche | Qui la fait | Pourquoi |
|---|---|---|
| Comprendre la demande : intentions (souvent plusieurs), personne concernée, résumé pour Martine | **LLM**, règles en secours | Langage naturel, 5 langues, formulations imprévisibles. Une erreur ici dégrade la qualité, jamais la sécurité. |
| Faits littéraux : dates, période d'une facture, numéro de facture, action sur un rendez-vous (« verschieben », « missed ») | **Règles d'abord**, LLM en complément | Vu en réel : le modèle se trompe d'année (« ma facture de septembre » → 2025), oublie ou invente une action ; une expression régulière ne se trompe pas sur « 21. Oktober ». |
| Détecter une urgence possible | **Règles ET LLM**, le plus grave l'emporte | Une urgence manquée est inacceptable : le LLM peut ajouter une alerte, jamais en retirer. |
| Détecter manipulation / hameçonnage | **Règles ET LLM** | Idem ; les règles reconnaissent l'injection de consignes, la demande de données en masse, l'usurpation (CNS, Doctena…). |
| Identifier l'expéditeur, le patient concerné, la facture ou le rendez-vous visé | **Code + SQL** | Exact et vérifiable : comparaison stricte de l'adresse, rapprochement avec le dossier. |
| Autoriser un document ou une donnée du dossier | **Code** (`autorisation.py`, ~60 lignes), appelé deux fois | Règle éliminatoire : aucune probabilité admise. |
| Écrire la réponse au patient | **Textes pré-validés** (`textes.py`) | Garantit par construction : aucun conseil médical, aucune information inventée, aucun contenu de dossier. |
| Langue de la réponse | Règles + LLM | Les modèles confondent luxembourgeois et allemand : des marqueurs nets (« Moien », « Kënnt Dir », « w.e.g. ») tranchent. |
| Priorité, catégorie, statut, note interne | **Code** | Cohérent, explicable, traçable. |

Conséquence vérifiée par les tests : **même un LLM manipulé** (injection réussie, fiche fantaisiste) ne peut
provoquer aucun manquement aux règles 1 à 4 — il peut seulement rendre un brouillon moins utile
(`tests/test_securite.py`, `FICHES_MALVEILLANTES`).

Si le serveur Ollama est injoignable ou répond mal, le système bascule en **mode règles seules** : même
sécurité, davantage de passages « à compléter ».

---

## 3. Les règles du cabinet : comment elles sont garanties

| Règle | Garantie |
|---|---|
| **1. Aucun conseil médical** | Le LLM n'écrit aucune phrase destinée au patient. Une question médicale reçoit un paragraphe fixe : « nous ne donnons pas d'avis médical par e-mail, votre question est transmise à l'équipe soignante, appelez-nous ; hors horaires : garde, urgence vitale : 112 ». Un test vérifie tous les textes dans les 5 langues ; un garde-fou bloque toute formulation de conseil (« prenez… », « c'est normal », « ne vous inquiétez pas »…). |
| **2. Urgence en tête de pile, immédiatement** | Double détection (lexiques en 5 langues + LLM, sans possibilité de baisse). Les mails sont **pré-triés en quelques millisecondes avant toute lecture LLM** ; une urgence repérée par les règles obtient son brouillon **sans attendre le LLM** (ni ses lenteurs, ni ses pannes), avant tous les autres mails. Priorité `urgente`, alerte affichée immédiatement, note « rappeler au n° du dossier », réponse : appeler le cabinet / la garde / le 112. |
| **3. Document uniquement à l'adresse enregistrée** (ou au représentant légal d'un mineur) | `autorisation.py` est le seul point de décision : l'expéditeur doit être *exactement* l'adresse du dossier ; pour un mineur, uniquement un représentant légal enregistré (`assistant.representants_legaux`, jamais l'adresse du dossier de l'enfant). Revérifié par les garde-fous juste avant l'écriture. En-tête « Répondre à » différent → rien n'est joint. Les refus sont **neutres** : ils ne confirment même pas qu'un dossier existe (réponse identique que le conjoint soit patient ou non). |
| **4. Contenu du dossier jamais dans une réponse** | Le motif des rendez-vous n'est **jamais lu** : absent des requêtes et du modèle de données, et **interdit par la base elle-même** (le rôle `assistant_mails` a des droits par colonne, sans `motif`). L'attestation de présence ne mentionne ni soin ni praticien. Garde-fou : aucun vocabulaire de soins ni numéro de dent hors grille tarifaire générale. |
| Langue du patient | Langue du message (règles + LLM) ; à défaut, langue du dossier ; à défaut, français + action « à adapter ». |
| Rien n'est envoyé | Aucun code d'envoi (vérifié par un test) ; le rôle base de données ne peut qu'**ajouter** des brouillons (ni modifier, ni supprimer). |
| Modèle local | Ollama sur un PC du cabinet. Le LLM ne reçoit que le texte du mail (test : ni téléphone, ni date de naissance, ni facture d'un autre patient dans la requête). |

**Pourquoi local plutôt qu'une API européenne** : le coût d'une API (Mistral, hébergée à Paris) serait
négligeable (≈ 1 €/mois pour 60 mails/jour), mais chaque e-mail de patient — donc des données de santé — sortirait
du cabinet, ce qui impose un contrat de sous-traitance et contredit la préférence du Dr Reuter. Le local est
possible ici parce que le LLM ne fait que *lire et classer* : un modèle de 8 B paramètres suffit déjà (validé en
réel). Pour la production, un modèle plus grand et européen (`mistral-small3.2`, 24 B) est recommandé, à valider
avec les mêmes jeux de test avant la mise en service.

---

## 4. Gestion de l'imprévu : ce que fait le système quand il ne sait pas

| Situation | Comportement |
|---|---|
| LLM injoignable, lent ou réponse invalide | Mode règles seules, mention dans la note. Pas de nouvel essai après un délai dépassé ; après 2 échecs de connexion, plus aucune attente pour le reste du lot. Une urgence n'attend jamais le LLM. |
| Demande non reconnue, mail vide | Accusé de réception + `[[À COMPLÉTER PAR LE SECRÉTARIAT : …]]`, statut **`à compléter`**. |
| Information absente de `infos_cabinet.md` (RDV manqué facturé ?, parking…) | Jamais inventée : passage `[[À COMPLÉTER]]` avec la raison. |
| Tiers (conjoint, comptable…), mineur, adresse inconnue, nom usurpé | Aucune donnée ni pièce jointe ; réponse neutre ; constat détaillé dans la note (dossier trouvé, adresse autorisée). |
| Facture / rendez-vous introuvable ou ambigu, RDV « absent » pour une attestation | Rien n'est joint ; la raison précise est dans le brouillon à compléter. |
| Les deux lectures divergent | Le plus prudent pour la sécurité ; divergences listées dans la note. |
| Message suspect (injection, usurpation, demande en masse) | Aucune réponse, aucune pièce jointe ; consigne dans la note (« compte peut-être piraté » si l'adresse est celle d'un patient). |
| Erreur interne sur un mail | Brouillon « à traiter manuellement » (en priorité urgente si des signes d'urgence ont été vus) ; les autres mails continuent. Aucun mail perdu. |
| Un garde-fou se déclenche | Brouillon neutralisé (aucune donnée, aucune pièce jointe) + explication dans la note. |

---

## 5. Résultat sur les 10 mails de développement

Sortie complète (mails, réponses proposées, notes internes) : **[`sorties/sortie_mails_dev.md`](sorties/sortie_mails_dev.md)**
(et `.json`), produite par la commande ci-dessous avec le **vrai LLM** (`qwen3:8b` sur le serveur Ollama du réseau) :
9 mails lus par règles + LLM, le mail urgent traité par les règles seules — par conception, une urgence n'attend
pas le LLM. Les mêmes 10 brouillons sont obtenus en mode règles seules (test
`test_pipeline.MailsDeDeveloppement`). Pour la régénérer : `reinitialiser --oui` puis
`traiter mails_dev.json --date-reference 2026-10-07`.

| # | Expéditeur | Catégorie | Priorité | Langue | Pièce jointe | Point clé |
|---|---|---|---|---|---|---|
| 2 | joana.ferreira | urgence médicale | **urgente** (n° 1 de la pile) | pt | — | fièvre + joue gonflée + forte douleur : appeler le cabinet / garde / 112, rappel au n° du dossier, aucun avis |
| 6 | claire.dupont | question médicale + attestation | haute | fr | attestation PDF | attestation sans motif ni praticien ; « est-ce normal ? » transmis à l'équipe, sans réponse médicale |
| 1 | anne.muller | facture | normale | fr | F-2026-0412.pdf | adresse = dossier ; « contrôle » non repris dans la réponse |
| 3 | lucas.bernard | tarif | normale | fr | — | 75 € + remboursement CNS partiel (montant exact non garanti) + Doctena |
| 4 | anne.muller | facture | normale | fr | — | facture du mari **refusée** sans confirmer qu'il est patient ; note : seule adresse autorisée = celle de Paul |
| 5 | thomas.schneider | rendez-vous | normale | de | — | RDV du 21/10 à 8h30 identifié ; « couronne 26 » jamais mentionnée ; créneau de 90 min dans la note |
| 8 | p.kowalski | rendez-vous + facturation | normale | en | — | absence du 30/09 reconnue ; facturation de l'absence non inventée → **à compléter** |
| 9 | maman.wagner | facture | normale | lb | — | Lena est mineure, aucun représentant légal enregistré → refus neutre, en luxembourgeois |
| 7 | facturation-cns@secure-lu-… | suspect | basse | — | — | injection de consignes + usurpation CNS + demande de toute la patientèle → aucune réponse |
| 10 | dentalsupplies-promo | publicité | basse | — | — | aucune réponse |

---

## 6. Tests

`python -m unittest discover -s tests -t .` — 71 tests, ~15 s :

- **sécurité** (`test_securite.py`) : invariants des règles 1 à 4 vérifiés sur **56 mails** (10 de développement +
  46 mails pièges inédits, `tests/mails_pieges.json` : urgences dans les 5 langues, injections, faux Dr Reuter,
  faux Doctena, conjoint, comptable, mineurs, « Répondre à » piégé, nouvelle adresse, RDV d'un tiers…), lus de
  trois façons : règles seules, LLM correct, **LLM manipulé** ; matrice d'autorisation ; lint de tous les textes ;
- **justesse** (`test_pipeline.py`) : catégorie, priorité, langue, pièces jointes et contenu des 10 brouillons ;
  attentes sur les 46 mails pièges ; doublons, panne du LLM en cours de lot, erreur interne, mails dégradés ;
- **lecture** (`test_lecture.py`) : langues (dont luxembourgeois/allemand), dates en 5 langues, détecteurs,
  revalidation des fiches LLM fantaisistes ;
- **client Ollama** (`test_ollama.py`) : faux serveur HTTP local (succès, modèle absent, erreur 500, JSON
  invalide, délai dépassé, serveur injoignable) et preuve que le LLM ne reçoit aucune donnée du dossier ;
- **base réelle** (`test_integration.py`) : le rôle ne lit pas le motif, ne modifie ni ne supprime rien ;
  résultats identiques à la copie en mémoire ;
- **leçons du modèle réel** (`test_pipeline.LeconsDuModeleReel`) : rejoue les fiches *réellement* renvoyées par
  `qwen3:8b` (`tests/fiches_qwen3_reelles.json`), erreurs comprises.

**Validation avec le vrai modèle** (`qwen3:8b`, serveur Ollama du réseau, 7 octobre 2026) :

| Jeu | Résultat |
|---|---|
| 10 mails de développement | 10/10 conformes (catégorie, priorité, langue, pièces jointes) |
| 46 mails pièges | **0 manquement aux règles 1 à 4** ; 44/46 conformes aux attentes écrites du premier coup, et 3 autres défauts de qualité trouvés en relisant les brouillons (détail ci-dessous) |
| Temps de lecture | 28 s par mail en moyenne (carte graphique du serveur de test) ; 60 mails ≈ 30 min de calcul étalées sur la journée |

Ce que le modèle réel a révélé, et qui a été corrigé puis revérifié avec lui : il se trompe d'année (« ma facture
de septembre » → 2025), oublie ou invente une action sur un rendez-vous, range un e-mail italien en « allemand »,
lit une réclamation comme une demande d'information, ajoute « facturation » à une simple question de prix. D'où la
règle de fusion « le LLM pour le sens, les règles pour les faits littéraux ». Écart conservé volontairement : un
saignement léger de la gencive après un soin classé « urgent » par le LLM (excès de prudence assumé).

**Évaluation avec un vrai modèle** (rien n'est écrit en base) — à rejouer avant toute mise en service ou tout
changement de modèle :

```bash
.venv/bin/python -m tests.evaluer_llm                                # modèle de la configuration
.venv/bin/python -m tests.evaluer_llm --modele mistral-small3.2 --sortie sorties/eval_mistral.json
```

---

## 7. Limites connues et mise en production

- **Validation humaine indispensable** : le système prépare, Martine décide. Les détecteurs sont volontairement
  prudents : quelques alertes en trop sont possibles et assumées.
- **Usurpation d'adresse** : le système se fie à l'adresse d'expéditeur. En production, lire aussi les en-têtes
  SPF/DKIM (`Authentication-Results`) du serveur de messagerie ; d'ici là, la règle « documents uniquement à
  l'adresse du dossier » limite le risque (une réponse part vers le vrai titulaire).
- **Luxembourgeois et portugais** : les textes de `textes.py` doivent être relus une fois par un locuteur natif.
- **Mineurs** : le registre `assistant.representants_legaux` doit être alimenté par le cabinet après
  vérification d'identité ; tant qu'il est vide, aucun document d'enfant ne part par e-mail.
- **Agenda** : pas d'accès à Doctena (pas d'API publique) — l'assistant identifie le rendez-vous, Martine
  le déplace.
- **Intégration** : lecture de la boîte en IMAP (lecture seule) et écran de validation pour Martine (la vue
  `assistant.pile` est prête) ; pour l'instant, entrée par fichier JSON ou `.eml`.
- **RGPD** : définir avec le cabinet la durée de conservation des analyses (`assistant.analyses`).
- **Attestations** : générées en PDF pour relecture ; à signer et tamponner avant envoi.

---

## 8. Organisation du code

```
assistant_mails/
  __main__.py        ligne de commande (installer, verifier, traiter, pile, reinitialiser)
  config.py          variables d'environnement / .env
  entree.py          chargement JSON ou .eml          normalisation.py  adresses, HTML, historique cité
  analyse_regles.py  lecture déterministe              detecteurs.py     urgence, manipulation, publicité
  langue.py          détection de langue (lb/de...)     dates.py          dates en 5 langues
  llm.py             client Ollama (urllib), consigne, schéma JSON, revalidation de la fiche
  fusion.py          fusion prudente règles + LLM
  dossier.py         lecture DentaGest (sans le motif)  autorisation.py   règle 3, seul point de décision
  decision.py        décisions métier                   connaissances.py  infos et tarifs du cabinet
  textes.py          réponses pré-validées (5 langues)  redaction.py      mise en forme, note interne
  garde_fous.py      contrôles finaux indépendants      attestation_pdf.py PDF sans dépendance
  stockage.py        écriture des brouillons            pipeline.py       orchestration, pré-tri, secours
  installation.py    schéma « assistant » + rôle restreint (droits par colonne)
  rapport.py         sortie console / Markdown / JSON
tests/               71 tests, mails pièges, copie mémoire de init.sql, LLM simulés
sorties/             sortie du programme sur les 10 mails
NOTE_Dr_Reuter.md    note d'une page pour le client
```
