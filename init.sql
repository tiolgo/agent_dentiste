-- =====================================================================
-- Cabinet dentaire Dr Reuter & associés : copie de test de DentaGest
-- Données fictives. Date de référence du jeu de test : 7 octobre 2026.
-- =====================================================================

CREATE TABLE praticiens (
    id      SERIAL PRIMARY KEY,
    nom     TEXT NOT NULL,
    role    TEXT NOT NULL
);

CREATE TABLE patients (
    id              SERIAL PRIMARY KEY,
    nom             TEXT NOT NULL,
    prenom          TEXT NOT NULL,
    email           TEXT UNIQUE,
    telephone       TEXT,
    langue          TEXT NOT NULL CHECK (langue IN ('fr', 'de', 'en', 'pt', 'lb')),
    date_naissance  DATE NOT NULL,
    derniere_visite DATE
);

CREATE TABLE rendez_vous (
    id            SERIAL PRIMARY KEY,
    patient_id    INTEGER NOT NULL REFERENCES patients(id),
    praticien_id  INTEGER NOT NULL REFERENCES praticiens(id),
    debut         TIMESTAMP NOT NULL,
    duree_min     INTEGER NOT NULL,
    motif         TEXT NOT NULL,          -- information de santé : ne jamais la recopier dans un mail
    statut        TEXT NOT NULL CHECK (statut IN ('prévu', 'effectué', 'annulé', 'absent'))
);

CREATE TABLE factures (
    numero        TEXT PRIMARY KEY,
    patient_id    INTEGER NOT NULL REFERENCES patients(id),
    date_facture  DATE NOT NULL,
    montant       NUMERIC(10,2) NOT NULL,
    statut        TEXT NOT NULL CHECK (statut IN ('payée', 'en attente')),
    fichier_pdf   TEXT NOT NULL           -- chemin du PDF dans le logiciel
);

-- Réponses rédigées pour validation par la secrétaire
CREATE TABLE brouillons (
    id                SERIAL PRIMARY KEY,
    expediteur        TEXT NOT NULL,
    sujet             TEXT,
    categorie         TEXT NOT NULL,
    priorite          TEXT NOT NULL DEFAULT 'normale',
    mail_original     TEXT,
    reponse_proposee  TEXT,
    pieces_jointes    TEXT[],
    statut            TEXT NOT NULL DEFAULT 'à valider',
    cree_le           TIMESTAMP NOT NULL DEFAULT now()
);

-- ---------- Données de test ----------

INSERT INTO praticiens (nom, role) VALUES
    ('Dr Marc Reuter',      'dentiste'),
    ('Dr Sofia Almeida',    'dentiste'),
    ('Dr Jonas Weber',      'orthodontiste'),
    ('Laura Schmit',        'hygiéniste');

INSERT INTO patients (nom, prenom, email, telephone, langue, date_naissance, derniere_visite) VALUES
    ('Muller',   'Anne',     'anne.muller@pt.lu',          '+352 621 111 111', 'fr', '1984-03-12', '2026-09-15'),
    ('Muller',   'Paul',     'paul.muller@pt.lu',          '+352 621 111 112', 'fr', '1982-07-30', '2025-02-10'),
    ('Ferreira', 'Joana',    'joana.ferreira@gmail.com',   '+352 661 222 333', 'pt', '1991-11-02', '2026-10-02'),
    ('Schneider','Thomas',   'thomas.schneider@web.de',    '+49 151 4444 555', 'de', '1975-05-18', '2026-06-20'),
    ('Dupont',   'Claire',   'claire.dupont@orange.fr',    '+33 6 12 34 56 78','fr', '1968-01-25', '2026-09-28'),
    ('Kowalski', 'Piotr',    'p.kowalski@outlook.com',     '+352 691 777 888', 'en', '1990-08-14', '2024-11-05'),
    ('Wagner',   'Lena',     NULL,                         '+352 621 999 000', 'lb', '2015-04-03', '2026-08-12');

INSERT INTO rendez_vous (patient_id, praticien_id, debut, duree_min, motif, statut) VALUES
    (1, 1, '2026-09-15 09:00', 30, 'contrôle annuel',            'effectué'),
    (1, 4, '2026-10-14 14:00', 45, 'détartrage',                 'prévu'),
    (3, 2, '2026-10-02 10:30', 60, 'extraction dent 38',         'effectué'),
    (3, 2, '2026-10-16 11:00', 20, 'contrôle post-extraction',   'prévu'),
    (4, 1, '2026-06-20 16:00', 30, 'contrôle annuel',            'effectué'),
    (4, 1, '2026-10-21 08:30', 90, 'couronne 26',                'prévu'),
    (5, 2, '2026-09-28 15:00', 60, 'traitement de canal 46',     'effectué'),
    (6, 1, '2026-09-30 09:30', 30, 'contrôle',                   'absent'),
    (7, 3, '2026-08-12 13:00', 30, 'suivi orthodontique',        'effectué'),
    (7, 3, '2026-11-04 13:00', 30, 'suivi orthodontique',        'prévu');

INSERT INTO factures (numero, patient_id, date_facture, montant, statut, fichier_pdf) VALUES
    ('F-2026-0412', 1, '2026-09-15',  65.00, 'payée',      'factures/2026/F-2026-0412.pdf'),
    ('F-2025-0188', 2, '2025-02-10',  65.00, 'payée',      'factures/2025/F-2025-0188.pdf'),
    ('F-2026-0451', 3, '2026-10-02', 140.00, 'en attente', 'factures/2026/F-2026-0451.pdf'),
    ('F-2026-0301', 4, '2026-06-20',  65.00, 'payée',      'factures/2026/F-2026-0301.pdf'),
    ('F-2026-0437', 5, '2026-09-28', 310.00, 'payée',      'factures/2026/F-2026-0437.pdf'),
    ('F-2026-0102', 5, '2026-03-11',  65.00, 'payée',      'factures/2026/F-2026-0102.pdf'),
    ('F-2026-0390', 7, '2026-08-12',  55.00, 'payée',      'factures/2026/F-2026-0390.pdf');
