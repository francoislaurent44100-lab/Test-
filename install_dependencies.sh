#!/bin/bash
# Installation des dépendances du pipeline DPE

set -e

echo "================================================"
echo "Installation des dépendances du pipeline DPE"
echo "================================================"

# Vérifier si pip est installé
if ! command -v pip3 &> /dev/null; then
    echo "ERROR: pip3 n'est pas installé"
    exit 1
fi

echo ""
echo "1. Installation des bibliothèques de base..."
pip3 install requests

echo ""
echo "2. Installation des bibliothèques Google (optionnel)..."
pip3 install google-auth-oauthlib google-auth-httplib2 google-api-python-client

echo ""
echo "3. Installation des utilitaires de données..."
pip3 install pandas openpyxl

echo ""
echo "================================================"
echo "✓ Installation complétée"
echo "================================================"
echo ""
echo "Prochaines étapes:"
echo "  1. Configurer les credentials Google (si utilisation Google Sheets)"
echo "  2. Modifier les variables de config dans dpe_pipeline.py"
echo "  3. Tester: python3 dpe_pipeline.py"
echo ""
