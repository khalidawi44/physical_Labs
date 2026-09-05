# Product

<!-- impeccable:product-schema 1 -->

Charte produit d'A.N.E.M.O.N.E. Rédigée le 5 septembre 2026 (première version
proposée par Codex, relue et alignée sur l'outil réel). Ce qui n'existe pas
encore est marqué **objectif**.

## Platform

web (application Streamlit locale, ouverte dans le navigateur de la machine)

## Users

Des chercheurs en physique des particules qui explorent des runs expérimentaux,
et des personnes sans formation en physique qui veulent comprendre le travail
sans modifier les réglages scientifiques.

## Product Purpose

A.N.E.M.O.N.E est un laboratoire local d'exploration de données de physique. Il
transforme une matrice d'événements en pistes explicables, teste les
explications instrumentales possibles et consigne un raisonnement
reproductible. Le succès n'est jamais une « découverte automatique » : c'est de
mettre un chercheur devant les pistes qui méritent réellement son expertise.

## Positioning

Le produit associe détection d'anomalies (Isolation Forest), tentative
systématique de réfutation (l'Architecte, la campagne de robustesse, Albert) et
carnet de recherche persistant (graphe de connaissances, base de connaissances,
cahier d'Albert) dans une même expérience.

## Operating Context

L'outil s'exécute localement dans un navigateur via Streamlit. Il lit des
fichiers CSV ou ROOT, dont les jeux CMS Open Data téléchargés dans
`donnees/cern_open_data/` (somme de contrôle vérifiée). Rien ne quitte la
machine : aucune statistique d'usage, écoute sur `localhost` seulement.

## Capabilities and Constraints

- Deux niveaux d'usage, choisis dans la barre latérale : « Découverte guidée »
  (lecture en langage courant, niveau de preuve en quatre paliers, glossaire,
  réglages repliés) et « Expert » (tous les réglages, bureau de l'Architecte).
  Deux façons de travailler : « Avec Albert » (le physicien robot apprend,
  débat, cherche seul) ou « Fred seul avec l'Architecte ».
- Le premier écran « Commencer » ouvre en un clic l'exemple livré, la démo
  synthétique ou un fichier réel du CERN.
- La vue 4D (trois axes + couleur) est interactive, avec le vecteur de tendance
  des anomalies ; elle ne masque pas la donnée et ne produit aucune
  interprétation physique non validée. La vidéo de l'événement de collision
  anime les trajectoires des particules mesurées depuis le vertex.
- Un run de découverte va de l'hypothèse à la thèse : chasse aux bosses sur les
  masses, autres explications testées une à une, hypothèse testée à l'endroit
  indiqué, thèse écrite et soumise au physicien. Validé à l'aveugle sur les
  données CMS 2011 (résonances connues retrouvées, rien d'inexpliqué).
- Les conclusions emploient des niveaux de preuve explicites et prudents :
  verdicts de campagne (solide, suspect de biais, fragile, queues du fond,
  faible, insuffisant), p-values et tailles d'effet affichées, Architecte qui ne
  verrouille rien sans statistique suffisante.
- L'application ne modifie jamais les fichiers de données chargés.
- Première cible : données CMS/LHC déjà fournies. Les autres expériences restent
  une extension future.

## Brand Commitments

Nom existant : A.N.E.M.O.N.E. Ton : exigeant, clair, non sensationnaliste. La
beauté visuelle doit servir la lecture scientifique.

## Evidence on Hand

Jeux CMS Open Data dans `donnees/cern_open_data/` (19 fichiers, enregistrements
545 et 700), démonstration synthétique clairement étiquetée, tests automatisés
sur Windows, macOS et Linux, rapports de campagne reproductibles (empreintes et
versions). Il n'existe pas encore de validation de découverte scientifique ;
aucun résultat ne doit être présenté comme tel.

## Product Principles

- Guider sans infantiliser.
- Une piste doit être falsifiable avant d'être mise en avant.
- Montrer la preuve, son incertitude et ses limites ensemble.
- Rendre le parcours simple par défaut, précis à la demande.
- Préserver une trace vérifiable de chaque décision.
- Ne jamais inventer un chiffre ni un fait ; vérifier avant de livrer.
