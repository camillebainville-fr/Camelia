# 🏛️ ATLAS — Agent Patrimonial

## Installation en 3 étapes

### 1. Installe les dépendances Python
```bash
pip install flask anthropic
```

### 2. Configure ta clé API Anthropic
Crée un compte sur https://console.anthropic.com et génère une clé API.

**Mac/Linux :**
```bash
export ANTHROPIC_API_KEY="ta-clé-ici"
```

**Windows (PowerShell) :**
```powershell
$env:ANTHROPIC_API_KEY="ta-clé-ici"
```

### 3. Lance l'agent
```bash
python app.py
```

Puis ouvre **http://localhost:5000** dans ton navigateur.

---

## Structure des fichiers
```
agent_patrimonial/
├── app.py        ← Le cerveau (backend Python + API Claude)
├── index.html    ← L'interface web
└── README.md     ← Ce fichier
```

---

## Comment ça marche

1. **L'interface** envoie tes messages au backend Flask
2. **Flask** les transmet à l'API Claude (Sonnet 4.6) avec un prompt système expert
3. **Claude** répond comme un conseiller patrimonial senior
4. **Le bouton "Générer le bilan"** déclenche une analyse complète de la conversation

---

## Prochaines étapes

- [ ] Ajouter une base de données (SQLite) pour sauvegarder les sessions
- [ ] Ajouter l'Agent Trader (couche 2)
- [ ] Ajouter l'Orchestrateur multi-agents
- [ ] Connecter à une API de données marché (yfinance)
- [ ] Déployer sur un serveur (Railway, Render, ou VPS)
