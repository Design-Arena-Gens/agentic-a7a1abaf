# Graphique Paramétrable (Python + Matplotlib)

Application web déployable sur Vercel permettant de générer dynamiquement un graphique via un service Python.

## 🚀 Aperçu

- Interface web légère (`index.html`) pour saisir une expression mathématique et personnaliser le rendu.
- Fonction serverless Vercel (`api/plot.py`) qui évalue l'expression avec NumPy et produit un graphique Matplotlib.
- Réponse JSON contenant l'image PNG encodée en base64, directement affichée côté client.

## 🧰 Prérequis

- Python 3.11+
- `pip`
- (Optionnel) Serveur HTTP statique pour prévisualiser la page (`python -m http.server`)

## ▶️ Utilisation locale

1. Créer un environnement virtuel (optionnel mais recommandé) :
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. Installer les dépendances pour la fonction Python :
   ```bash
   pip install -r requirements.txt
   ```

3. Exécuter la fonction en local (serveur simple) :
   ```bash
   python api/plot.py
   ```
   Le service écoute sur `http://127.0.0.1:8001/api/plot`.

4. Servir `index.html` :
   ```bash
   python -m http.server 8000
   ```
   Puis ouvrir `http://localhost:8000`. L'interface détecte automatiquement le serveur API local sur `127.0.0.1:8001`.

## 📦 Déploiement Vercel

1. Vérifier que `VERCEL_TOKEN` est configuré (fourni séparément).
2. Déployer :
   ```bash
   vercel deploy --prod --yes --token $VERCEL_TOKEN --name agentic-a7a1abaf
   ```
3. Vérifier :
   ```bash
   curl https://agentic-a7a1abaf.vercel.app
   ```

## 🗂 Structure

```
.
├── api/
│   └── plot.py          # Fonction serverless Python (matplotlib + numpy)
├── index.html           # Interface utilisateur
├── requirements.txt     # Dépendances Python
└── README.md
```

## ✨ Fonctions supportées

L'expression accepte la variable `x` et les fonctions NumPy usuelles (`sin`, `cos`, `exp`, `log`, etc.). Les constantes `pi` et `e` sont disponibles.

## ⚠️ Limitations

- Les expressions sont évaluées dans un environnement sécurisé mais limité.
- Les graphiques sont générés en PNG et encodés en base64 (taille maximale de la réponse limitée).

## 📄 Licence

MIT.
