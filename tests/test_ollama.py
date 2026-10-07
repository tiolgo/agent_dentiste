"""Client Ollama (urllib) testé contre un faux serveur HTTP local, et minimisation des données."""

import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from assistant_mails.llm import ClientOllama, ErreurLLM, LecteurLLM

from tests.donnees_test import FICHES_IDEALES, PATIENTS, REF, assistant_test, mails_dev


class FauxOllama(BaseHTTPRequestHandler):
    mode = "ok"
    appels: list = []
    reponse = FICHES_IDEALES["1"]

    def log_message(self, *args):
        pass

    def _envoyer(self, code, corps):
        donnees = corps if isinstance(corps, bytes) else json.dumps(corps).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(donnees)))
        self.end_headers()
        try:
            self.wfile.write(donnees)
        except BrokenPipeError:            # le client a abandonné (test du délai dépassé)
            pass

    def do_GET(self):
        self._envoyer(200, {"models": [{"name": "mistral-small3.2:latest"}]})

    def do_POST(self):
        charge = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/generate":                      # préchargement du modèle
            return self._envoyer(200, {"model": charge["model"], "done": True})
        FauxOllama.appels.append(charge)
        mode = FauxOllama.mode
        if mode == "404":
            return self._envoyer(404, {"error": "model 'x' not found"})
        if mode == "500_puis_ok" and len(FauxOllama.appels) == 1:
            return self._envoyer(500, {"error": "boom"})
        if mode == "lent":
            time.sleep(1.5)
        contenu = "pas du json" if mode == "json_invalide" else json.dumps(FauxOllama.reponse)
        self._envoyer(200, {"model": charge["model"], "message": {"role": "assistant", "content": contenu},
                            "done": True, "eval_count": 42})


class ClientHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.serveur = ThreadingHTTPServer(("127.0.0.1", 0), FauxOllama)
        cls.url = f"http://127.0.0.1:{cls.serveur.server_port}"
        threading.Thread(target=cls.serveur.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.serveur.shutdown()

    def setUp(self):
        FauxOllama.appels = []
        FauxOllama.mode = "ok"

    def client(self, **kw):
        return ClientOllama(self.url, "mistral-small3.2", timeout=kw.pop("timeout", 5), **kw)

    def test_verification_du_modele(self):
        self.assertTrue(self.client().verifier()[0])
        ok, message = ClientOllama(self.url, "autre-modele").verifier()
        self.assertFalse(ok)
        self.assertIn("ollama pull", message)

    def test_lecture_et_requete_envoyee(self):
        mail = mails_dev()[0]
        analyse, fiche, meta = LecteurLLM(self.client(), REF).lire(mail)
        self.assertEqual(analyse.intentions, ["demande_facture"])
        charge = FauxOllama.appels[0]
        self.assertFalse(charge["stream"])
        self.assertEqual(charge["options"]["temperature"], 0)
        self.assertEqual(charge["format"]["type"], "object")       # sortie contrainte par le schéma
        self.assertNotIn("think", charge)

    def test_le_llm_ne_recoit_aucune_donnee_du_dossier(self):
        """Seul le mail est transmis : ni téléphone, ni date de naissance, ni facture d'un autre patient."""
        LecteurLLM(self.client(), REF).lire(mails_dev()[3])              # Anne demande la facture de Paul
        envoye = json.dumps(FauxOllama.appels[0], ensure_ascii=False)
        for p in PATIENTS:
            self.assertNotIn(p.date_naissance.isoformat(), envoye)
            if p.telephone:
                self.assertNotIn(p.telephone, envoye)
        for interdit in ("paul.muller@pt.lu", "F-2025-0188", "contrôle annuel", "détartrage"):
            self.assertNotIn(interdit, envoye)

    def test_modele_absent_pas_de_nouvel_essai(self):
        FauxOllama.mode = "404"
        with self.assertRaises(ErreurLLM):
            self.client().chat_json("s", "u", {"type": "object"})
        self.assertEqual(len(FauxOllama.appels), 1)

    def test_erreur_serveur_puis_succes(self):
        FauxOllama.mode = "500_puis_ok"
        fiche, _ = self.client().chat_json("s", "u", {"type": "object"})
        self.assertEqual(fiche["intentions"], ["demande_facture"])
        self.assertEqual(len(FauxOllama.appels), 2)

    def test_reponse_non_json(self):
        FauxOllama.mode = "json_invalide"
        with self.assertRaises(ErreurLLM):
            self.client(essais=1).chat_json("s", "u", {"type": "object"})

    def test_delai_depasse_sans_nouvel_essai(self):
        """Un serveur trop lent ne fait pas attendre le lot : pas de nouvel essai."""
        FauxOllama.mode = "lent"
        debut = time.monotonic()
        with self.assertRaises(ErreurLLM):
            self.client(timeout=0.3, essais=2).chat_json("s", "u", {"type": "object"})
        self.assertEqual(len(FauxOllama.appels), 1)
        self.assertLess(time.monotonic() - debut, 1.0)

    def test_prechargement(self):
        self.client().prechauffer()

    def test_serveur_injoignable(self):
        client = ClientOllama("http://127.0.0.1:9", "mistral-small3.2", timeout=1)
        ok, message = client.verifier()
        self.assertFalse(ok)
        self.assertIn("injoignable", message)

    def test_chaine_complete_avec_le_faux_serveur(self):
        FauxOllama.reponse = FICHES_IDEALES["5"]
        assistant, _ = assistant_test(LecteurLLM(self.client(), REF))
        mail = [m for m in mails_dev() if m.source_id == "5"][0]
        res = assistant.traiter(mail)
        FauxOllama.reponse = FICHES_IDEALES["1"]
        self.assertIn("règles + LLM", res.lecture)
        self.assertIn("21. Oktober 2026", res.reponse)


if __name__ == "__main__":
    unittest.main()
