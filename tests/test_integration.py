"""Tests sur la vraie base (docker-compose). Ignorés si la base ou le rôle restreint ne sont pas disponibles.

Ils n'écrivent rien : lecture via le rôle restreint, brouillons gardés en mémoire.
"""

import tempfile
import unittest
from pathlib import Path

import psycopg

from assistant_mails.config import charger_config
from assistant_mails.dossier import DossierPostgres
from assistant_mails.pipeline import Assistant
from assistant_mails.stockage import StockageMemoire

from tests.donnees_test import REF, assistant_test, dossier_test, mails_dev, mails_pieges, violations


def _connexion():
    try:
        return psycopg.connect(**charger_config().parametres_connexion(), autocommit=True)
    except psycopg.Error:
        return None


class BaseReelle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cx = _connexion()
        if cls.cx is None:
            raise unittest.SkipTest("base PostgreSQL ou rôle assistant_mails indisponible")

    @classmethod
    def tearDownClass(cls):
        cls.cx.close()

    def test_le_role_ne_peut_pas_lire_le_motif(self):
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            self.cx.execute("SELECT motif FROM rendez_vous LIMIT 1")

    def test_le_role_ne_peut_ni_modifier_ni_supprimer(self):
        for ordre in ("UPDATE patients SET email = 'x@y.lu' WHERE id = 1", "DELETE FROM brouillons",
                      "UPDATE brouillons SET statut = 'envoyé'"):
            with self.subTest(ordre=ordre), self.assertRaises(psycopg.errors.InsufficientPrivilege):
                self.cx.execute(ordre)

    def test_memes_resultats_qu_avec_la_copie_memoire(self):
        mails = mails_dev() + [m for m, _ in mails_pieges()]
        reel = Assistant(DossierPostgres(self.cx), StockageMemoire(), REF, Path(tempfile.mkdtemp()),
                         alerter=lambda *a: None)
        memoire, _ = assistant_test()
        dossier = dossier_test()
        for mail in mails:
            a, b = reel.traiter(mail), memoire.traiter(mail)
            with self.subTest(mail=mail.source_id):
                self.assertEqual((a.priorite, a.categorie, a.statut, a.pieces, a.reponse),
                                 (b.priorite, b.categorie, b.statut, b.pieces, b.reponse))
                self.assertEqual(violations(a, dossier), [])


if __name__ == "__main__":
    unittest.main()
