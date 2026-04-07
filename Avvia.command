#!/bin/bash
cd "$(dirname "$0")"

echo "======================================"
echo "  Presenze Academy — Avvio in corso"
echo "======================================"

# Trova un Python 3 funzionante
PYTHON=""
for candidate in /usr/bin/python3 /usr/local/bin/python3 /opt/homebrew/bin/python3; do
    if [ -x "$candidate" ]; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo ""
    echo "ERRORE: Python 3 non trovato."
    echo "Scaricalo da https://www.python.org/downloads/"
    read -p "Premi Invio per chiudere..."
    exit 1
fi

echo "Python: $PYTHON"
echo ""

# Installa dipendenze se mancanti
for dep in easyocr Pillow numpy streamlit; do
    if ! "$PYTHON" -c "import $dep" 2>/dev/null; then
        echo "Installazione $dep (solo al primo avvio)..."
        "$PYTHON" -m pip install "$dep" -q
    fi
done

# Disabilita il prompt email di Streamlit
mkdir -p ~/.streamlit
echo '[general]' > ~/.streamlit/credentials.toml
echo 'email = ""' >> ~/.streamlit/credentials.toml

echo ""
echo "Apertura nel browser..."
echo "(Per chiudere l'app: torna qui e premi Ctrl+C)"
echo ""

# Avvia Streamlit e apri il browser dopo 3 secondi
sleep 3 && open http://localhost:8501 &
"$PYTHON" -m streamlit run app.py --server.headless true --browser.gatherUsageStats false
