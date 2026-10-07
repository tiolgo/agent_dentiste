"""Tests : python -m unittest discover -s tests -t ."""

import logging

# Les avertissements attendus (LLM simulé injoignable, panne simulée) ne polluent pas la sortie des tests.
logging.getLogger("assistant_mails").setLevel(logging.CRITICAL)
