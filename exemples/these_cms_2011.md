<!-- Thèse produite par `python anemone_decouverte.py donnees/cern_open_data/545` sur les huit fichiers CMS 2011 du CERN Open Data (enregistrement 545), telle quelle. Elle montre ce que rend un run de découverte sur des données réelles où il n'y a rien de nouveau à trouver : l'instrument retrouve la physique établie. -->

# Run de découverte A.N.E.M.O.N.E — 2026-09-05T17:57:02

**Conclusion : Instrument validé, rien de nouveau : 15 résonance(s) connue(s) retrouvée(s) à l'aveugle, aucune bosse inexpliquée. (8 fichier(s), 39 bosse(s) examinées, 6 écartée(s).)**

## Hypothèse

Aucune hypothèse : recherche libre.

## Données

- `Dimuon_DoubleMu.csv` : 100000 événements, variables de chasse M (SHA-256 `58caa45c580f8bcf…`)
- `Dimuon_SingleMu.csv` : 83761 événements, variables de chasse M (SHA-256 `9901450546336067…`)
- `Jpsimumu.csv` : 20000 événements, variables de chasse M_paire, dérivées : M_paire (SHA-256 `95bf87f7c14758b4…`)
- `Wenu.csv` : 100000 événements, variables de chasse pt, HoverE, isoTrack, isoEcal, isoHcal, MET, Q (SHA-256 `03d32eaf82fc6821…`)
- `Wmunu.csv` : 100000 événements, variables de chasse pt, chiSq, dxy, iso, MET, Q (SHA-256 `8031d7f62935b75e…`)
- `Ymumu.csv` : 20000 événements, variables de chasse M_paire, dérivées : M_paire (SHA-256 `b2757444c7339f8e…`)
- `Zee.csv` : 10000 événements, variables de chasse M_paire, dérivées : M_paire (SHA-256 `ae6fbad67d78ffa7…`)
- `Zmumu.csv` : 10000 événements, variables de chasse M_paire, dérivées : M_paire (SHA-256 `7782778f8417d2c7…`)

## Méthode

Chasse aux bosses sur chaque variable de chasse : histogramme (classes logarithmiques ou linéaires), fond lisse ajusté sur les bandes latérales de chaque fenêtre, probabilité de Poisson d'un tel excès, correction du nombre de fenêtres et de variables testées (Bonferroni). Chaque bosse est ensuite soumise aux épreuves ci-dessous ; l'hypothèse localisée est testée à son endroit exact, sans facteur d'essais.

## Bosses examinées

### 🟢 connue — `Dimuon_DoubleMu.csv` : M ≈ 3.065
- fenêtre [2.903, 3.135] : 6923 observés pour 821.8 attendus, z local = 37.0, p globale = 0 (416 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 0 (416 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 4007 observés / 443.1 attendus, p = 0 ; 2de moitié : 2916 / 352.4, p = 0
- ✅ Tient avec un autre découpage : avec 120 classes : 8231 observés / 1221.5 attendus, p = 0
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 8 % (résonance attendue ≤ 12 %)
- coïncidence : J/ψ(1S) (3.0969 GeV, PDG)
- verdict : coïncide avec J/ψ(1S) (3.0969 GeV, PDG) : physique établie retrouvée, pas une nouveauté

### 🟢 connue — `Dimuon_DoubleMu.csv` : M ≈ 9.724
- fenêtre [9.203, 10.33] : 7810 observés pour 4121.7 attendus, z local = 37.0, p globale = 0 (416 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 0 (416 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 4060 observés / 2152.8 attendus, p = 6.2e-293 ; 2de moitié : 3750 / 1999.5, p = 1.6e-266
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 12 % (résonance attendue ≤ 12 %)
- coïncidence : Υ(1S) (9.4604 GeV, PDG), Υ(2S) (10.0233 GeV, PDG), Υ(3S) (10.3552 GeV, PDG)
- verdict : coïncide avec Υ(1S) (9.4604 GeV, PDG), Υ(2S) (10.0233 GeV, PDG), Υ(3S) (10.3552 GeV, PDG) : physique établie retrouvée, pas une nouveauté

### 🟢 connue — `Dimuon_SingleMu.csv` : M ≈ 3.049
- fenêtre [2.841, 3.196] : 5889 observés pour 2783.3 attendus, z local = 37.0, p globale = 0 (500 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 0 (500 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 3106 observés / 1448.8 attendus, p = 1.4e-311 ; 2de moitié : 2783 / 1355.4, p = 4.2e-252
- ✅ Tient avec un autre découpage : avec 120 classes : 6577 observés / 3488.8 attendus, p = 0
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 12 % (résonance attendue ≤ 12 %)
- coïncidence : J/ψ(1S) (3.0969 GeV, PDG)
- verdict : coïncide avec J/ψ(1S) (3.0969 GeV, PDG) : physique établie retrouvée, pas une nouveauté

### 🟢 connue — `Jpsimumu.csv` : M_paire ≈ 3.092
- fenêtre [2.974, 3.211] : 10115 observés pour 1202.7 attendus, z local = 37.0, p globale = 0 (543 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 0 (543 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 5171 observés / 485.1 attendus, p = 0 ; 2de moitié : 4944 / 485.9, p = 0
- ✅ Tient avec un autre découpage : avec 120 classes : 10175 observés / 976.9 attendus, p = 0
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 8 % (résonance attendue ≤ 12 %)
- coïncidence : J/ψ(1S) (3.0969 GeV, PDG)
- verdict : coïncide avec J/ψ(1S) (3.0969 GeV, PDG) : physique établie retrouvée, pas une nouveauté

### 🟢 connue — `Ymumu.csv` : M_paire ≈ 9.456
- fenêtre [9.355, 9.566] : 2543 observés pour 1058.5 attendus, z local = 37.0, p globale = 0 (594 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 0 (594 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 1272 observés / 510.5 attendus, p = 4.4e-176 ; 2de moitié : 1271 / 562.0, p = 6.2e-145
- ✅ Tient avec un autre découpage : avec 120 classes : 2942 observés / 1180.1 attendus, p = 0
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 2 % (résonance attendue ≤ 12 %)
- coïncidence : Υ(1S) (9.4604 GeV, PDG)
- verdict : coïncide avec Υ(1S) (9.4604 GeV, PDG) : physique établie retrouvée, pas une nouveauté

### 🟢 connue — `Zmumu.csv` : M_paire ≈ 90.89
- fenêtre [88.29, 93.54] : 5540 observés pour 2662.6 attendus, z local = 37.0, p globale = 0 (574 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 0 (574 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 2770 observés / 470.5 attendus, p = 0 ; 2de moitié : 2770 / 528.8, p = 0
- ✅ Tient avec un autre découpage : avec 120 classes : 5958 observés / 812.3 attendus, p = 0
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 6 % (résonance attendue ≤ 12 %)
- coïncidence : Z (91.1876 GeV, PDG)
- verdict : coïncide avec Z (91.1876 GeV, PDG) : physique établie retrouvée, pas une nouveauté

### 🟢 connue — `Dimuon_SingleMu.csv` : M ≈ 9.646
- fenêtre [8.878, 10.39] : 3479 observés pour 2129.1 attendus, z local = 26.8, p globale = 1.8e-155 (500 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 1.8e-155 (500 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 1800 observés / 1166.0 attendus, p = 2.2e-66 ; 2de moitié : 1679 / 1022.5, p = 7.2e-79
- ✅ Tient avec un autre découpage : avec 120 classes : 4108 observés / 2655.0 attendus, p = 3.4e-150
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 16 % (résonance attendue ≤ 12 %)
- coïncidence : Υ(1S) (9.4604 GeV, PDG), Υ(2S) (10.0233 GeV, PDG), Υ(3S) (10.3552 GeV, PDG)
- verdict : coïncide avec Υ(1S) (9.4604 GeV, PDG), Υ(2S) (10.0233 GeV, PDG), Υ(3S) (10.3552 GeV, PDG) : physique établie retrouvée, pas une nouveauté

### 🟢 connue — `Zee.csv` : M_paire ≈ 92.87
- fenêtre [91.54, 94.71] : 1591 observés pour 850.1 attendus, z local = 22.6, p globale = 6.4e-111 (603 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 6.4e-111 (603 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 739 observés / 373.3 attendus, p = 1.3e-62 ; 2de moitié : 852 / 533.7, p = 5.2e-37
- ✅ Tient avec un autre découpage : avec 120 classes : 2052 observés / 1054.6 attendus, p = 1.6e-162
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 3 % (résonance attendue ≤ 12 %)
- coïncidence : Z (91.1876 GeV, PDG)
- verdict : coïncide avec Z (91.1876 GeV, PDG) : physique établie retrouvée, pas une nouveauté

### 🟢 connue — `Jpsimumu.csv` : M_paire ≈ 3.695
- fenêtre [3.626, 3.784] : 687 observés pour 313.6 attendus, z local = 18.2, p globale = 2.4e-71 (543 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 2.4e-71 (543 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 331 observés / 143.4 attendus, p = 6.9e-41 ; 2de moitié : 356 / 168.2, p = 1.6e-36
- ✅ Tient avec un autre découpage : avec 120 classes : 721 observés / 331.7 attendus, p = 2.5e-76
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 4 % (résonance attendue ≤ 12 %)
- coïncidence : ψ(2S) (3.6861 GeV, PDG)
- verdict : coïncide avec ψ(2S) (3.6861 GeV, PDG) : physique établie retrouvée, pas une nouveauté

### 🟢 connue — `Zee.csv` : M_paire ≈ 89.66
- fenêtre [87.97, 91.14] : 1897 observés pour 1255.1 attendus, z local = 16.8, p globale = 4.9e-61 (603 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 4.9e-61 (603 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 844 observés / 606.5 attendus, p = 5.1e-20 ; 2de moitié : 1053 / 732.9, p = 7.9e-29
- ✅ Tient avec un autre découpage : avec 120 classes : 2103 observés / 1324.8 attendus, p = 1.9e-86
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 4 % (résonance attendue ≤ 12 %)
- coïncidence : Z (91.1876 GeV, PDG)
- verdict : coïncide avec Z (91.1876 GeV, PDG) : physique établie retrouvée, pas une nouveauté

### 🟢 connue — `Dimuon_DoubleMu.csv` : M ≈ 3.771
- fenêtre [3.656, 3.949] : 640 observés pour 376.0 attendus, z local = 12.3, p globale = 1e-32 (416 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 1e-32 (416 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 360 observés / 234.0 attendus, p = 1.4e-14 ; 2de moitié : 280 / 153.9, p = 5.2e-20
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 8 % (résonance attendue ≤ 12 %)
- coïncidence : ψ(2S) (3.6861 GeV, PDG)
- verdict : coïncide avec ψ(2S) (3.6861 GeV, PDG) : physique établie retrouvée, pas une nouveauté

### 🟢 connue — `Dimuon_DoubleMu.csv` : M ≈ 1.025
- fenêtre [0.9888, 1.068] : 773 observés pour 482.6 attendus, z local = 12.1, p globale = 1.5e-31 (416 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 1.5e-31 (416 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 405 observés / 282.2 attendus, p = 3.9e-12 ; 2de moitié : 368 / 200.5, p = 2.1e-26
- ✅ Tient avec un autre découpage : avec 120 classes : 872 observés / 614.7 attendus, p = 9.6e-23
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 8 % (résonance attendue ≤ 12 %)
- coïncidence : φ(1020) (1.01946 GeV, PDG)
- verdict : coïncide avec φ(1020) (1.01946 GeV, PDG) : physique établie retrouvée, pas une nouveauté

### 🟢 connue — `Dimuon_DoubleMu.csv` : M ≈ 0.7844
- fenêtre [0.7554, 0.8158] : 586 observés pour 360.7 attendus, z local = 10.9, p globale = 3.9e-25 (416 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 3.9e-25 (416 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 322 observés / 193.5 attendus, p = 2.2e-17 ; 2de moitié : 264 / 166.0, p = 1.5e-12
- ✅ Tient avec un autre découpage : avec 120 classes : 912 observés / 696.5 attendus, p = 3.6e-15
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 8 % (résonance attendue ≤ 12 %)
- coïncidence : ω(782) (0.78266 GeV, PDG)
- verdict : coïncide avec ω(782) (0.78266 GeV, PDG) : physique établie retrouvée, pas une nouveauté

### 🟢 connue — `Ymumu.csv` : M_paire ≈ 9.969
- fenêtre [9.856, 10.07] : 1510 observés pour 1139.4 attendus, z local = 10.4, p globale = 4.6e-23 (594 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 4.6e-23 (594 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 768 observés / 566.5 attendus, p = 5.6e-16 ; 2de moitié : 742 / 568.0, p = 1.7e-12
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 2 % (résonance attendue ≤ 12 %)
- coïncidence : Υ(2S) (10.0233 GeV, PDG)
- verdict : coïncide avec Υ(2S) (10.0233 GeV, PDG) : physique établie retrouvée, pas une nouveauté

### 🟢 connue — `Ymumu.csv` : M_paire ≈ 10.38
- fenêtre [10.3, 10.46] : 1115 observés pour 905.4 attendus, z local = 6.7, p globale = 5.8e-09 (594 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 5.8e-09 (594 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 552 observés / 438.9 attendus, p = 1.2e-07 ; 2de moitié : 563 / 464.6, p = 5.3e-06
- ✅ Tient avec un autre découpage : avec 120 classes : 1378 observés / 1175.0 attendus, p = 4.3e-09
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 2 % (résonance attendue ≤ 12 %)
- coïncidence : Υ(3S) (10.3552 GeV, PDG)
- verdict : coïncide avec Υ(3S) (10.3552 GeV, PDG) : physique établie retrouvée, pas une nouveauté

### 🟠 indice — `Wmunu.csv` : pt ≈ 131.6
- fenêtre [129.7, 133.6] : 27 observés pour 7.6 attendus, z local = 5.4, p globale = 0.00013 (3480 fenêtres testées)
- ❌ Fluctuation statistique (5 σ après correction) : p globale 0.00013 (3480 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ➖ Tient dans chaque moitié du run : fond non estimable sur une moitié (trop peu d'événements)
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 3 % (résonance attendue ≤ 12 %)
- verdict : significative après correction, mais sous 5 σ : indice, pas preuve

### 🟡 structure — `Wmunu.csv` : chiSq ≈ 0.7198
- fenêtre [0.6063, 0.8183] : 26867 observés pour 20126.8 attendus, z local = 37.0, p globale = 0 (3312 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 0 (3312 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 13753 observés / 10737.0 attendus, p = 2.4e-171 ; 2de moitié : 13114 / 9917.8, p = 1.8e-205
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 29 % (résonance attendue ≤ 12 %)
- verdict : excès large et solide : structure du spectre (seuil, cinématique, acceptance) plutôt qu'une résonance

### 🟡 structure — `Wmunu.csv` : MET ≈ 51.4
- fenêtre [46.26, 59.22] : 8197 observés pour 6461.6 attendus, z local = 20.7, p globale = 4.7e-92 (3564 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 4.7e-92 (3564 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ➖ Tient dans chaque moitié du run : fond non estimable sur une moitié (trop peu d'événements)
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 25 % (résonance attendue ≤ 12 %)
- verdict : excès large et solide : structure du spectre (seuil, cinématique, acceptance) plutôt qu'une résonance

### 🟡 structure — `Wmunu.csv` : pt ≈ 41.7
- fenêtre [39.67, 44.29] : 12079 observés pour 10259.3 attendus, z local = 17.5, p globale = 4.4e-65 (3480 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 4.4e-65 (3480 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 5808 observés / 4850.5 attendus, p = 8.2e-41 ; 2de moitié : 6271 / 5457.2, p = 2.8e-27
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 11 % (résonance attendue ≤ 12 %)
- verdict : excès solide sur pt, qui n'est pas une masse : structure cinématique ou instrumentale à interpréter, pas une résonance

### 🟡 structure — `Wenu.csv` : pt ≈ 28.91
- fenêtre [27.46, 30.14] : 5018 observés pour 3917.9 attendus, z local = 16.8, p globale = 2e-60 (2877 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 2e-60 (2877 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ➖ Tient dans chaque moitié du run : fond non estimable sur une moitié (trop peu d'événements)
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 9 % (résonance attendue ≤ 12 %)
- verdict : excès solide sur pt, qui n'est pas une masse : structure cinématique ou instrumentale à interpréter, pas une résonance

### 🟡 structure — `Wenu.csv` : MET ≈ 43.8
- fenêtre [39.15, 49.88] : 8092 observés pour 6794.3 attendus, z local = 15.3, p globale = 2.4e-49 (4291 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 2.4e-49 (4291 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 3065 observés / 2604.0 attendus, p = 8.2e-19 ; 2de moitié : 5027 / 4237.2, p = 2.5e-32
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 25 % (résonance attendue ≤ 12 %)
- verdict : excès large et solide : structure du spectre (seuil, cinématique, acceptance) plutôt qu'une résonance

### 🟡 structure — `Wenu.csv` : HoverE ≈ 0.0447
- fenêtre [0.04108, 0.0489] : 3583 observés pour 2816.3 attendus, z local = 13.9, p globale = 2.5e-40 (3983 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 2.5e-40 (3983 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 1943 observés / 1671.7 attendus, p = 5.2e-11 ; 2de moitié : 1640 / 1266.9, p = 6.6e-24
- ✅ Tient avec un autre découpage : avec 120 classes : 3969 observés / 3099.9 attendus, p = 7.9e-51
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 18 % (résonance attendue ≤ 12 %)
- verdict : excès large et solide : structure du spectre (seuil, cinématique, acceptance) plutôt qu'une résonance

### 🟡 structure — `Wenu.csv` : pt ≈ 108.6
- fenêtre [92.38, 130.1] : 5212 observés pour 4318.9 attendus, z local = 13.2, p globale = 2.4e-36 (2877 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 2.4e-36 (2877 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ➖ Tient dans chaque moitié du run : fond non estimable sur une moitié (trop peu d'événements)
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 35 % (résonance attendue ≤ 12 %)
- verdict : excès large et solide : structure du spectre (seuil, cinématique, acceptance) plutôt qu'une résonance

### 🟡 structure — `Dimuon_DoubleMu.csv` : M ≈ 2.228
- fenêtre [1.901, 2.586] : 3468 observés pour 2889.2 attendus, z local = 10.4, p globale = 3.7e-23 (416 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 3.7e-23 (416 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 1943 observés / 1745.2 attendus, p = 1.7e-06 ; 2de moitié : 1525 / 1329.4, p = 8.4e-08
- ✅ Tient avec un autre découpage : avec 120 classes : 4304 observés / 3410.1 attendus, p = 3.3e-49
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 31 % (résonance attendue ≤ 12 %)
- verdict : excès large et solide : structure du spectre (seuil, cinématique, acceptance) plutôt qu'une résonance

### 🟡 structure — `Dimuon_SingleMu.csv` : M ≈ 1.685
- fenêtre [1.347, 1.995] : 7862 observés pour 6992.2 attendus, z local = 10.2, p globale = 5.4e-22 (500 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 5.4e-22 (500 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ➖ Tient dans chaque moitié du run : fond non estimable sur une moitié (trop peu d'événements)
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 38 % (résonance attendue ≤ 12 %)
- verdict : excès large et solide : structure du spectre (seuil, cinématique, acceptance) plutôt qu'une résonance

### 🟡 structure — `Wmunu.csv` : chiSq ≈ 0.9262
- fenêtre [0.8602, 0.9994] : 16162 observés pour 15013.1 attendus, z local = 9.3, p globale = 3.4e-17 (3312 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 3.4e-17 (3312 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ➖ Tient dans chaque moitié du run : fond non estimable sur une moitié (trop peu d'événements)
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 15 % (résonance attendue ≤ 12 %)
- verdict : excès large et solide : structure du spectre (seuil, cinématique, acceptance) plutôt qu'une résonance

### 🟡 structure — `Wenu.csv` : pt ≈ 38.05
- fenêtre [36.33, 39.88] : 12969 observés pour 11950.2 attendus, z local = 9.2, p globale = 5.7e-17 (2877 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 5.7e-17 (2877 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ➖ Tient dans chaque moitié du run : fond non estimable sur une moitié (trop peu d'événements)
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 9 % (résonance attendue ≤ 12 %)
- verdict : excès solide sur pt, qui n'est pas une masse : structure cinématique ou instrumentale à interpréter, pas une résonance

### 🟡 structure — `Wenu.csv` : pt ≈ 4.664
- fenêtre [4.116, 5.279] : 1194 observés pour 913.8 attendus, z local = 8.8, p globale = 1.4e-15 (2877 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 1.4e-15 (2877 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 559 observés / 433.7 attendus, p = 4.7e-09 ; 2de moitié : 635 / 459.1, p = 5e-15
- ✅ Tient avec un autre découpage : avec 120 classes : 1440 observés / 1176.8 attendus, p = 6.8e-14
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 25 % (résonance attendue ≤ 12 %)
- verdict : excès large et solide : structure du spectre (seuil, cinématique, acceptance) plutôt qu'une résonance

### 🟡 structure — `Wenu.csv` : pt ≈ 55.3
- fenêtre [52.77, 57.93] : 5560 observés pour 5004.9 attendus, z local = 7.7, p globale = 1.9e-11 (2877 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 1.9e-11 (2877 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ➖ Tient dans chaque moitié du run : fond non estimable sur une moitié (trop peu d'événements)
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 9 % (résonance attendue ≤ 12 %)
- verdict : excès solide sur pt, qui n'est pas une masse : structure cinématique ou instrumentale à interpréter, pas une résonance

### 🟡 structure — `Dimuon_SingleMu.csv` : M ≈ 36.15
- fenêtre [31.22, 42.75] : 2719 observés pour 2370.8 attendus, z local = 7.0, p globale = 7.4e-10 (500 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 7.4e-10 (500 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 1184 observés / 983.0 attendus, p = 2.8e-10 ; 2de moitié : 1535 / 1346.4, p = 2.6e-07
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 32 % (résonance attendue ≤ 12 %)
- verdict : excès large et solide : structure du spectre (seuil, cinématique, acceptance) plutôt qu'une résonance

### 🟡 structure — `Dimuon_DoubleMu.csv` : M ≈ 15.1
- fenêtre [12.52, 18.39] : 22046 observés pour 21056.2 attendus, z local = 6.8, p globale = 2.7e-09 (416 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 2.7e-09 (416 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ➖ Tient dans chaque moitié du run : fond non estimable sur une moitié (trop peu d'événements)
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 39 % (résonance attendue ≤ 12 %)
- verdict : excès large et solide : structure du spectre (seuil, cinématique, acceptance) plutôt qu'une résonance

### 🟡 structure — `Dimuon_SingleMu.csv` : M ≈ 4.908
- fenêtre [4.208, 5.763] : 5514 observés pour 5043.9 attendus, z local = 6.5, p globale = 1.8e-08 (500 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 1.8e-08 (500 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 2974 observés / 2654.9 attendus, p = 6.5e-10 ; 2de moitié : 2540 / 2324.6, p = 5.5e-06
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 32 % (résonance attendue ≤ 12 %)
- verdict : excès large et solide : structure du spectre (seuil, cinématique, acceptance) plutôt qu'une résonance

### 🟡 structure — `Wmunu.csv` : dxy ≈ 0.006591
- fenêtre [-0.007331, 0.02082] : 10885 observés pour 10206.6 attendus, z local = 6.6, p globale = 4.2e-08 (2676 fenêtres testées)
- ✅ Fluctuation statistique (5 σ après correction) : p globale 4.2e-08 (2676 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 5469 observés / 5182.9 attendus, p = 4.2e-05 ; 2de moitié : 5416 / 5076.9, p = 1.3e-06
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 427 % (résonance attendue ≤ 12 %)
- verdict : excès large et solide : structure du spectre (seuil, cinématique, acceptance) plutôt qu'une résonance

### ⚪ écartée — `Wenu.csv` : HoverE ≈ 0.01075
- fenêtre [0.00978, 0.01174] : 2682 observés pour 2369.5 attendus, z local = 6.3, p globale = 6.8e-07 (3983 fenêtres testées)
- ❌ Fluctuation statistique (5 σ après correction) : p globale 6.8e-07 (3983 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ❌ Tient dans chaque moitié du run : 1re moitié : 1398 observés / 1132.8 attendus, p = 1.6e-14 ; 2de moitié : 1284 / 1275.9, p = 0.41
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 18 % (résonance attendue ≤ 12 %)
- verdict : fluctuation : p globale 6.8e-07 (3983 fenêtres testées) ; seuil 5 σ = 2.9e-07; deux_moities : 1re moitié : 1398 observés / 1132.8 attendus, p = 1.6e-14 ; 2de moitié : 1284 / 1275.9, p = 0.41; etroitesse : largeur relative 18 % (résonance attendue ≤ 12 %)

### ⚪ écartée — `Dimuon_SingleMu.csv` : M ≈ 1.025
- fenêtre [0.9455, 1.106] : 1180 observés pour 997.0 attendus, z local = 5.6, p globale = 4.7e-06 (500 fenêtres testées)
- ❌ Fluctuation statistique (5 σ après correction) : p globale 4.7e-06 (500 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ✅ Tient dans chaque moitié du run : 1re moitié : 590 observés / 515.0 attendus, p = 0.00065 ; 2de moitié : 590 / 482.2, p = 1.1e-06
- ✅ Tient avec un autre découpage : avec 120 classes : 1387 observés / 1263.6 attendus, p = 0.00033
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 16 % (résonance attendue ≤ 12 %)
- coïncidence : φ(1020) (1.01946 GeV, PDG)
- verdict : fluctuation : p globale 4.7e-06 (500 fenêtres testées) ; seuil 5 σ = 2.9e-07; etroitesse : largeur relative 16 % (résonance attendue ≤ 12 %)

### ⚪ écartée — `Dimuon_DoubleMu.csv` : M ≈ 4.993
- fenêtre [4.432, 5.582] : 1273 observés pour 1089.1 attendus, z local = 5.4, p globale = 1.3e-05 (416 fenêtres testées)
- ❌ Fluctuation statistique (5 σ après correction) : p globale 1.3e-05 (416 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ❌ Tient dans chaque moitié du run : 1re moitié : 727 observés / 667.8 attendus, p = 0.012 ; 2de moitié : 546 / 441.6, p = 9e-07
- ➖ Tient avec un autre découpage : fond non estimable avec 120 classes
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 23 % (résonance attendue ≤ 12 %)
- verdict : fluctuation : p globale 1.3e-05 (416 fenêtres testées) ; seuil 5 σ = 2.9e-07; deux_moities : 1re moitié : 727 observés / 667.8 attendus, p = 0.012 ; 2de moitié : 546 / 441.6, p = 9e-07; etroitesse : largeur relative 23 % (résonance attendue ≤ 12 %)

### ⚪ écartée — `Dimuon_SingleMu.csv` : M ≈ 0.7488
- fenêtre [0.6905, 0.808] : 708 observés pour 582.4 attendus, z local = 5.0, p globale = 0.00013 (500 fenêtres testées)
- ❌ Fluctuation statistique (5 σ après correction) : p globale 0.00013 (500 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ❌ Tient dans chaque moitié du run : 1re moitié : 341 observés / 299.3 attendus, p = 0.0097 ; 2de moitié : 367 / 285.1, p = 1.9e-06
- ✅ Tient avec un autre découpage : avec 120 classes : 848 observés / 753.3 attendus, p = 0.00038
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ❌ Étroite comme une résonance : largeur relative 16 % (résonance attendue ≤ 12 %)
- coïncidence : ω(782) (0.78266 GeV, PDG)
- verdict : fluctuation : p globale 0.00013 (500 fenêtres testées) ; seuil 5 σ = 2.9e-07; deux_moities : 1re moitié : 341 observés / 299.3 attendus, p = 0.0097 ; 2de moitié : 367 / 285.1, p = 1.9e-06; etroitesse : largeur relative 16 % (résonance attendue ≤ 12 %)

### ⚪ écartée — `Wenu.csv` : isoTrack ≈ 57.47
- fenêtre [56.7, 58.19] : 58 observés pour 26.2 attendus, z local = 5.3, p globale = 0.00026 (4452 fenêtres testées)
- ❌ Fluctuation statistique (5 σ après correction) : p globale 0.00026 (4452 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ❌ Tient dans chaque moitié du run : 1re moitié : 25 observés / 14.3 attendus, p = 0.0067 ; 2de moitié : 33 / 11.6, p = 2.1e-07
- ✅ Tient avec un autre découpage : avec 120 classes : 64 observés / 37.6 attendus, p = 5.7e-05
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 3 % (résonance attendue ≤ 12 %)
- verdict : fluctuation : p globale 0.00026 (4452 fenêtres testées) ; seuil 5 σ = 2.9e-07; deux_moities : 1re moitié : 25 observés / 14.3 attendus, p = 0.0067 ; 2de moitié : 33 / 11.6, p = 2.1e-07

### ⚪ écartée — `Wenu.csv` : HoverE ≈ 0.01956
- fenêtre [0.01858, 0.02054] : 2047 observés pour 1822.1 attendus, z local = 5.2, p globale = 0.0005 (3983 fenêtres testées)
- ❌ Fluctuation statistique (5 σ après correction) : p globale 0.0005 (3983 fenêtres testées) ; seuil 5 σ = 2.9e-07
- ➖ Tient dans chaque moitié du run : fond non estimable sur une moitié (trop peu d'événements)
- ❌ Tient avec un autre découpage : avec 120 classes : 2466 observés / 2562.6 attendus, p = 0.97
- ✅ Loin des bords et seuils : loin des bords
- ➖ Absente du run de référence : aucun run de référence fourni
- ✅ Étroite comme une résonance : largeur relative 10 % (résonance attendue ≤ 12 %)
- verdict : fluctuation : p globale 0.0005 (3983 fenêtres testées) ; seuil 5 σ = 2.9e-07; decoupage : avec 120 classes : 2466 observés / 2562.6 attendus, p = 0.97

## À faire par le physicien

- Fournir un run de référence (calibration, fond connu) : l'épreuve « référence » n'a pas pu être menée.
- Les coïncidences avec des résonances connues sont établies sur la masse seule (±2,5 %) : à confirmer par le physicien.
- Rien ici n'est une conclusion physique : c'est un dossier de calculs à valider.

## Reproductibilité

anemone 0.8.0, python 3.11.15, numpy 2.4.6, pandas 3.0.5, scipy 1.17.1, scikit-learn 1.9.0
