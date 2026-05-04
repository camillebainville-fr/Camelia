from flask import Flask, request, jsonify, send_from_directory
import anthropic
import json
import os
import sqlite3
from datetime import datetime

app = Flask(__name__, static_folder='.')
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

DB_PATH = "camelia.db"

# ─────────────────────────────────────────────
# BASE DE DONNÉES
# ─────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS profils (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            created_at TEXT,
            updated_at TEXT,
            profil_json TEXT DEFAULT '{}'
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profil_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT,
            FOREIGN KEY (profil_id) REFERENCES profils(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bilans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profil_id INTEGER,
            contenu TEXT,
            created_at TEXT,
            FOREIGN KEY (profil_id) REFERENCES profils(id)
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Base de données Camélia initialisée")


def get_or_create_profil(profil_id=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if profil_id:
        c.execute("SELECT * FROM profils WHERE id = ?", (profil_id,))
        row = c.fetchone()
        if row:
            conn.close()
            return {"id": row[0], "nom": row[1], "profil_json": json.loads(row[4] or '{}')}
    now = datetime.now().isoformat()
    c.execute(
        "INSERT INTO profils (created_at, updated_at, profil_json) VALUES (?, ?, ?)",
        (now, now, '{}')
    )
    profil_id = c.lastrowid
    conn.commit()
    conn.close()
    return {"id": profil_id, "nom": None, "profil_json": {}}


def save_message(profil_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (profil_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (profil_id, role, content, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_messages(profil_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT role, content FROM messages WHERE profil_id = ? ORDER BY id ASC",
        (profil_id,)
    )
    rows = c.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]


def save_bilan(profil_id, contenu):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO bilans (profil_id, contenu, created_at) VALUES (?, ?, ?)",
        (profil_id, contenu, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def update_profil_nom(profil_id, nom):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE profils SET nom = ?, updated_at = ? WHERE id = ?",
        (nom, datetime.now().isoformat(), profil_id)
    )
    conn.commit()
    conn.close()


def list_profils():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT p.id, p.nom, p.created_at, p.updated_at,
               COUNT(m.id) as nb_messages
        FROM profils p
        LEFT JOIN messages m ON m.profil_id = p.id
        GROUP BY p.id
        ORDER BY p.updated_at DESC
    """)
    rows = c.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "nom": row[1] or f"Profil #{row[0]}",
            "created_at": row[2],
            "updated_at": row[3],
            "nb_messages": row[4]
        }
        for row in rows
    ]


# ─────────────────────────────────────────────
# PROMPT SYSTÈME CAMÉLIA
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """Tu es Camélia, une conseillère en gestion de patrimoine d'exception.
Tu incarnes le luxe accessible : l'expertise d'un family office, la chaleur d'une conseillère de confiance, pour tous.

Ta mission : accompagner chaque personne dans la construction et l'optimisation de son patrimoine, 
quelle que soit sa situation de départ — 10 000€ ou 10 millions€, tu apportes le même niveau d'excellence.

TON CARACTÈRE :
- Chaleureuse et bienveillante, jamais condescendante
- Experte mais pédagogue — tu expliques sans jargon inutile
- Directe et honnête — tu dis ce qui est, pas ce qu'on veut entendre
- Élégante dans ta façon de t'exprimer, jamais froide

TON APPROCHE :
1. Tu poses des questions de manière conversationnelle, naturelle
2. Une ou deux questions maximum à la fois
3. Tu expliques pourquoi chaque information est importante
4. Tu valides et enrichis chaque réponse avant de continuer
5. Tu te souviens de tout ce qui a été dit — tu ne repose jamais une question déjà posée

LES DOMAINES QUE TU COUVRES :
- Situation personnelle et familiale (âge, situation maritale, enfants, régime matrimonial)
- Situation professionnelle (statut, revenus, épargne salariale, retraite)
- Patrimoine immobilier (résidence principale, investissements locatifs, SCI)
- Patrimoine financier (PEA, assurance-vie, CTO, livrets, crypto)
- Patrimoine professionnel (parts de société, BSPCE, stock-options)
- Passifs (crédits immobiliers, consommation)
- Objectifs patrimoniaux (horizon, projets de vie, transmission)
- Situation fiscale (TMI, IFI, optimisations possibles)

DISPOSITIFS FISCAUX FRANÇAIS À MAÎTRISER :
PEA, PER, assurance-vie, LMNP, déficit foncier, SCI à l'IS, démembrement,
donation, pacte Dutreil, loi Pinel (fin de régime), nue-propriété

IMPORTANT :
- Tu es en France, tu utilises exclusivement le droit et la fiscalité françaises
- Tu restes factuelle et pédagogue, jamais alarmiste
- Tu conclus toujours avec des actions concrètes et actionnables

Si c'est la première interaction, présente-toi comme Camélia et demande le prénom."""


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/profils', methods=['GET'])
def get_profils():
    return jsonify(list_profils())


@app.route('/profil/nouveau', methods=['POST'])
def nouveau_profil():
    profil = get_or_create_profil()
    return jsonify(profil)


@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    profil_id = data.get('profil_id')
    user_message = data.get('message', '')

    if not profil_id:
        return jsonify({"error": "profil_id manquant"}), 400

    save_message(profil_id, 'user', user_message)
    historique = get_messages(profil_id)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=historique
    )

    assistant_message = response.content[0].text
    save_message(profil_id, 'assistant', assistant_message)

    # Détecte le prénom
    if len(historique) <= 4:
        words = user_message.split()
        if words:
            nom_potentiel = words[-1].strip('.,!?').capitalize()
            if len(nom_potentiel) > 2:
                update_profil_nom(profil_id, nom_potentiel)

    return jsonify({"response": assistant_message, "profil_id": profil_id})


@app.route('/bilan', methods=['POST'])
def bilan():
    data = request.json
    profil_id = data.get('profil_id')

    if not profil_id:
        return jsonify({"error": "profil_id manquant"}), 400

    historique = get_messages(profil_id)
    if not historique:
        return jsonify({"error": "Pas encore de conversation"}), 400

    bilan_prompt = """Sur la base de notre conversation, génère un BILAN PATRIMONIAL COMPLET en markdown :

# 🌸 BILAN PATRIMONIAL CAMÉLIA

## 1. Situation Personnelle & Familiale
## 2. Situation Professionnelle & Revenus
## 3. Patrimoine Brut
   - Actifs immobiliers
   - Actifs financiers
   - Autres actifs
## 4. Passifs
## 5. Patrimoine Net
## 6. Situation Fiscale
## 7. 🎯 Recommandations Prioritaires (top 5 actions concrètes)
## 8. 🗺️ Feuille de Route (court / moyen / long terme)

Sois précise, chiffrée quand possible, et conclus avec les opportunités d'optimisation les plus importantes."""

    messages_with_bilan = historique + [{"role": "user", "content": bilan_prompt}]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=messages_with_bilan
    )

    contenu = response.content[0].text
    save_bilan(profil_id, contenu)
    return jsonify({"bilan": contenu})


@app.route('/reset', methods=['POST'])
def reset():
    data = request.json
    profil_id = data.get('profil_id')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE profil_id = ?", (profil_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    init_db()
    print("🌸 Camélia — Conseiller Patrimonial")
    print("💾 Base de données : camelia.db")
    print("📱 Ouvre http://localhost:5000 dans ton navigateur")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
