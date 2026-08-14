# Extinia

**v1.2 · par dodosiiii**

Application Windows avec interface graphique : réglez un compte à rebours personnalisé et
choisissez l'action à exécuter automatiquement à la fin (éteindre le PC, mettre en veille,
redémarrer, verrouiller la session ou se déconnecter).

## Fonctionnalités

**Réglage du temps**
- Champs heures / minutes / secondes ou boutons rapides (1 min, 5 min, 10 min, 30 min, 1 h)
- Clic ou tabulation dans un champ : le contenu se sélectionne automatiquement, il suffit de
  taper pour remplacer la valeur
- **Molette de la souris** au-dessus d'un champ pour ajuster rapidement (+1 / -1)
- **+1 min / +5 min** pendant le compte à rebours pour le rallonger sans tout arrêter

**Suivi visuel**
- Anneau de progression circulaire (violet > 1 min, orange < 1 min, rouge < 10 s)
- **Heure de fin prévue** affichée sous l'anneau (ex : « fin prévue à 23:45 »), y compris en
  aperçu avant de démarrer
- Boutons Démarrer / Pause / Reprendre / Arrêter, avec raccourcis clavier :
  - **Espace** : Démarrer / Pause
  - **Échap** : Arrêter (ou annuler l'action en cours de déclenchement)

**Barre des tâches**
- Icône dans la zone de notification, avec les **minutes restantes** et l'action prévue
  (infobulle)
- **Alertes automatiques** à 5 minutes et 1 minute restantes, même fenêtre réduite
- **Icône clignotante** dans les 10 dernières secondes
- Un **clic sur l'icône rouvre l'application** ; clic droit : Ouvrir, Pause / Reprendre,
  Arrêter, Quitter
- Bouton dédié (🗕) et croix de la fenêtre pour réduire dans la barre des tâches : le compte à
  rebours continue en arrière-plan

**Options**
- **Toujours au premier plan** : garde la fenêtre visible par-dessus les autres
- **Son désactivé** : coupe le bip de fin sans toucher au volume Windows
- **Délai avant action configurable** (3 / 5 / 10 s) avant l'exécution automatique
- **Préférences mémorisées** : temps, action et options sont sauvegardés automatiquement et
  rechargés au prochain lancement

**Fin du compte à rebours**
- Avertissement sonore (sauf si coupé) + fenêtre de confirmation avec le délai choisi pour
  annuler ou exécuter immédiatement
- Pendant cette confirmation, les contrôles principaux (Pause / Arrêter / +1 min / +5 min)
  sont désactivés pour éviter toute action contradictoire : seuls **Annuler** et **Exécuter
  maintenant** dans la fenêtre de confirmation (ou **Échap**) permettent de revenir en arrière

**Actions disponibles**
- Éteindre le PC
- Mettre en veille
- Redémarrer
- Verrouiller la session
- Déconnexion

## Installation

### Avec Python

```bash
pip install -r requirements.txt
python main.py
```

### En .exe (optionnel)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "extinia" main.py
```

L'exécutable se trouve dans `dist/`.

## Utilisation

1. Réglez le temps (champs, molette, ou boutons rapides).
2. Choisissez l'action à exécuter à la fin.
3. Cliquez sur **Démarrer** (ou appuyez sur **Espace**).
4. Réduisez dans la barre des tâches si besoin : l'icône affiche les minutes restantes et
   vous prévient à 5 min et 1 min de la fin.

À la fin, une fenêtre s'affiche avec un compte à rebours (délai configurable) et un bouton
**Annuler** si vous changez d'avis. L'action est exécutée même si la fenêtre est réduite.

## Structure du projet

| Fichier | Rôle |
|---|---|
| `main.py` | Point d'entrée de l'application |
| `app.py` | Interface graphique (tkinter) et logique de contrôle |
| `config.py` | Nom de l'application, version, auteur, palette de couleurs |
| `countdown.py` | Logique du compte à rebours, basée sur le temps réel |
| `actions.py` | Actions système Windows (éteindre, veille, redémarrer, verrouiller, déconnexion) |
| `tray.py` | Icône et menu de la barre des tâches |
| `settings.py` | Sauvegarde / chargement des préférences (`%APPDATA%\Extinia\settings.json`) |

## Licence

MIT
