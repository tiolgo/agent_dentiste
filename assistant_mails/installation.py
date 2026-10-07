"""Installation dans la base du cabinet (à lancer une fois, avec le compte propriétaire).

1. Crée le schéma « assistant » : analyses (note interne, traçabilité), représentants légaux
   (à alimenter par le cabinet après vérification d'identité) et la vue « pile » pour le secrétariat.
2. Crée le rôle restreint « assistant_mails » avec des droits PAR COLONNE : il peut lire ce dont il a
   besoin, mais PAS le motif des rendez-vous (règle 4 garantie par la base elle-même), et il ne peut
   qu'AJOUTER des brouillons (aucune modification, aucune suppression).
"""

from __future__ import annotations

import psycopg
from psycopg import sql

SCHEMA = """
CREATE SCHEMA IF NOT EXISTS assistant;

CREATE TABLE IF NOT EXISTS assistant.analyses (
    id                     SERIAL PRIMARY KEY,
    brouillon_id           INTEGER NOT NULL REFERENCES public.brouillons(id) ON DELETE CASCADE,
    empreinte              TEXT NOT NULL,           -- empreinte du mail (évite les doublons)
    source_id              TEXT,
    langue                 TEXT,
    patient_id             INTEGER,                 -- expéditeur reconnu (NULL si inconnu)
    personne_concernee_id  INTEGER,
    destinataire           TEXT NOT NULL,           -- seule adresse à laquelle répondre
    intentions             TEXT[] NOT NULL DEFAULT '{}',
    drapeaux               TEXT[] NOT NULL DEFAULT '{}',
    note_interne           TEXT,                    -- pour le secrétariat, jamais envoyée
    resume                 TEXT,
    analyse_regles         JSONB,
    analyse_llm            JSONB,
    modele                 TEXT,
    duree_ms               INTEGER,
    cree_le                TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS analyses_empreinte_idx ON assistant.analyses (empreinte);
CREATE INDEX IF NOT EXISTS analyses_brouillon_idx ON assistant.analyses (brouillon_id);

-- Représentants légaux des patients mineurs : seule source autorisée pour leur envoyer des documents.
CREATE TABLE IF NOT EXISTS assistant.representants_legaux (
    id           SERIAL PRIMARY KEY,
    patient_id   INTEGER NOT NULL REFERENCES public.patients(id),
    prenom       TEXT NOT NULL,
    nom          TEXT NOT NULL,
    email        TEXT NOT NULL,
    lien         TEXT NOT NULL,          -- mère, père, tuteur...
    verifie_par  TEXT NOT NULL,          -- qui a vérifié l'identité au cabinet
    verifie_le   DATE NOT NULL,
    UNIQUE (patient_id, email)
);

-- Pile du secrétariat : urgences d'abord.
CREATE OR REPLACE VIEW assistant.pile AS
SELECT b.id AS brouillon,
       CASE b.priorite WHEN 'urgente' THEN 0 WHEN 'haute' THEN 1 WHEN 'normale' THEN 2 ELSE 3 END AS rang,
       b.priorite, b.categorie, b.statut, b.expediteur, b.sujet, a.langue, b.pieces_jointes,
       b.reponse_proposee, a.note_interne, b.cree_le
FROM public.brouillons b
LEFT JOIN assistant.analyses a ON a.brouillon_id = b.id
WHERE b.statut IN ('à valider', 'à compléter');
"""

DROITS = [
    "GRANT CONNECT ON DATABASE {base} TO {role}",
    "GRANT USAGE ON SCHEMA public TO {role}",
    "GRANT SELECT (id, nom, prenom, email, telephone, langue, date_naissance) ON public.patients TO {role}",
    "GRANT SELECT (id, nom, role) ON public.praticiens TO {role}",
    # rendez_vous : toutes les colonnes SAUF « motif »
    "GRANT SELECT (id, patient_id, praticien_id, debut, duree_min, statut) ON public.rendez_vous TO {role}",
    "GRANT SELECT (numero, patient_id, date_facture, statut, fichier_pdf) ON public.factures TO {role}",
    "GRANT SELECT, INSERT ON public.brouillons TO {role}",
    "GRANT USAGE ON SEQUENCE public.brouillons_id_seq TO {role}",
    "GRANT USAGE ON SCHEMA assistant TO {role}",
    "GRANT SELECT, INSERT ON assistant.analyses TO {role}",
    "GRANT USAGE ON SEQUENCE assistant.analyses_id_seq TO {role}",
    "GRANT SELECT ON assistant.representants_legaux TO {role}",
    "GRANT SELECT ON assistant.pile TO {role}",
]


def installer(cx_admin: psycopg.Connection, base: str, role: str, mot_de_passe: str,
              creer_role: bool = True) -> list[str]:
    etapes = []
    with cx_admin.transaction():
        cx_admin.execute(SCHEMA)
    etapes.append("schéma « assistant » prêt (analyses, representants_legaux, vue pile)")
    if not creer_role:
        return etapes
    with cx_admin.transaction():
        existe = cx_admin.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
        ordre = "ALTER ROLE {} WITH LOGIN PASSWORD {}" if existe else "CREATE ROLE {} WITH LOGIN PASSWORD {}"
        cx_admin.execute(sql.SQL(ordre).format(sql.Identifier(role), sql.Literal(mot_de_passe)))
        cx_admin.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}").format(sql.Identifier(role)))
        for droit in DROITS:
            cx_admin.execute(sql.SQL(droit).format(base=sql.Identifier(base), role=sql.Identifier(role)))
    etapes.append(f"rôle « {role} » {'mis à jour' if existe else 'créé'} : lecture sans le motif des rendez-vous, "
                  "ajout de brouillons uniquement")
    return etapes


def reinitialiser_test(cx_admin: psycopg.Connection) -> int:
    """Environnement de TEST uniquement : supprime les brouillons produits par l'assistant."""
    with cx_admin.transaction():
        n = cx_admin.execute(
            "DELETE FROM public.brouillons WHERE id IN (SELECT brouillon_id FROM assistant.analyses)").rowcount
        restants = cx_admin.execute("SELECT count(*) FROM public.brouillons").fetchone()[0]
        if restants == 0:
            cx_admin.execute("ALTER SEQUENCE public.brouillons_id_seq RESTART WITH 1")
            cx_admin.execute("ALTER SEQUENCE assistant.analyses_id_seq RESTART WITH 1")
    return n
