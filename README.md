Extinia

v1.0 · par dodosiiii

Application Windows avec interface graphique : réglez un compte à rebours personnalisé et choisissez l'action à exécuter automatiquement à la fin (éteindre le PC, mettre en veille, redémarrer, verrouiller la session ou se déconnecter).

Fonctionnalités
-Réglage du temps en heures / minutes / secondes ou via les boutons rapides (1 min, 5 min, 10 min, 30 min, 1 h)
-Compte à rebours animé avec anneau de progression circulaire (violet > 1 min, orange < 1 min, rouge < 10 s)
-Boutons Démarrer / Pause / Reprendre / Arrêter, avec raccourcis clavier :
-Espace : Démarrer / Pause / Reprendre
-Échap : Arrêter (ou annuler l'exécution finale)
-Icône dans la barre des tâches (zone de notification) :
-affiche en permanence les minutes restantes et l'action prévue (infobulle)
-un clic sur l'icône rouvre l'application
-clic droit : Ouvrir, Pause / Reprendre, Arrêter, Quitter
-Bouton dédié pour réduire directement dans la barre des tâches, en plus de la croix qui fait de même
-Toujours au premier plan (optionnel) : garde la fenêtre visible par-dessus les autres
-Son désactivé (optionnel) : coupe le bip de fin sans toucher au volume de Windows
-Mémorisation des réglages : le dernier temps réglé, l'action choisie et vos préférences sont sauvegardés automatiquement et restaurés au prochain lancement
-À la fin du compte à rebours : avertissement sonore (désactivable) + fenêtre de confirmation avec 3 secondes pour annuler


Actions disponibles :
-⏻ Éteindre le PC
-🌙 Mettre en veille
-⟳ Redémarrer
🔒 Verrouiller la session
-⎋ Déconnexion

Installation:
Avec Python
bash
pip install -r requirements.txt
python main.py
En .exe (optionnel)
bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "extinia" main.py

L'exécutable se trouve dans dist/.

Utilisation:
Réglez le temps (champs ou boutons rapides).
Choisissez l'action à exécuter à la fin.
Cliquez sur Démarrer (ou appuyez sur Espace).
Réduisez dans la barre des tâches si besoin (bouton dédié ou croix de fermeture) : l'icône affiche les minutes restantes.

À la fin, une fenêtre s'affiche avec un compte à rebours de 3 secondes et un bouton Annuler si vous changez d'avis. L'action est exécutée même si la fenêtre est réduite.

Structure du projet
Fichier	Rôle
main.py	Point d'entrée de l'application
app.py	Interface graphique (Tkinter) et logique d'affichage
config.py	Identité de l'application et palette de couleurs
settings.py	Sauvegarde / chargement des préférences (%APPDATA%\Extinia)
countdown.py	Logique du compte à rebours, basée sur le temps réel
actions.py	Actions système exécutées à la fin (extinction, veille, etc.)
tray.py	Icône et menu dans la barre des tâches
