# CPSS GPL Reports - Module de Rapports & Certificats

Module centralisé pour la génération de tous les rapports et certificats nécessaires à la gestion d'un centre GPL professionnel.

## 🎯 Vue d'ensemble

Le module CPSS GPL Reports fait partie de la suite complète CPSS GPL pour Odoo 17. Il centralise tous les rapports et certificats requis pour :
- La conformité réglementaire
- Le suivi administratif
- L'analyse de performance
- La documentation client

## 📋 Fonctionnalités

### Certificats Officiels
- **Certificat de Montage GPL** : Document attestant l'installation conforme
- **Certificat de Contrôle Triennal** : Validation périodique obligatoire
- **Autorisation d'Utilisation GPL** : Document réglementaire pour circulation
- **Certificat de Contrôle Technique** : Attestation de conformité

### Documents Administratifs
- **Bordereau d'Envoi** : Pour transmission des dossiers aux autorités
- **Factures Personnalisées GPL** : Avec mentions légales spécifiques
- **Ordres de Réparation** : Documentation des interventions
- **Rapports d'Inspection** : Détail des contrôles effectués

### Rapports Analytiques
- **État des Réservoirs** : Suivi des dates d'expiration et réépreuves
- **Planning Mensuel** : Vue d'ensemble des activités
- **Statistiques d'Activité** : Indicateurs de performance
- **Historique Client** : Traçabilité complète par client

## 🔧 Installation

### Prérequis
- Odoo 17.0 ou supérieur
- Modules CPSS GPL installés :
  - `cpss_gpl_base`
  - `cpss_gpl_reservoir`
  - `cpss_gpl_garage`
  - `cpss_gpl_operations`
- Module `report_xlsx` (OCA) pour l'export Excel

### Étapes d'installation
1. Copier le dossier `cpss_gpl_reports` dans le répertoire des addons Odoo
2. Mettre à jour la liste des applications
3. Installer le module "CPSS GPL - Rapports & Certificats"

## 📊 Utilisation

### Accès aux rapports

#### Via le menu principal
- **Rapports GPL** → Accès à tous les rapports organisés par catégorie

#### Depuis les formulaires
- Boutons d'impression directement accessibles sur :
  - Installations GPL
  - Inspections
  - Réparations
  - Factures

#### Actions groupées
- Sélectionner plusieurs enregistrements
- Action → Imprimer le rapport souhaité

### Configuration

#### Formats de papier
Trois formats prédéfinis :
- **Format Certificat** : Marges réduites pour certificats officiels
- **Format Bordereau** : Optimisé pour listes et tableaux
- **Format Rapport** : Marges standards pour rapports détaillés

#### Personnalisation
Les templates peuvent être modifiés via :
- Configuration → Technique → Actions → Rapports
- Rechercher les rapports commençant par "cpss_gpl_reports."

## 🎨 Structure des rapports

### En-tête personnalisé
- Logo de l'entreprise
- Informations de contact
- Numéro d'agrément GPL

### Corps du document
- Mise en page professionnelle
- Tableaux structurés
- Codes couleur pour la lisibilité

### Pied de page
- Pagination automatique
- Mentions légales si nécessaire

## 📁 Structure du module

```
cpss_gpl_reports/
├── __init__.py
├── __manifest__.py
├── security/
│   └── ir.model.access.csv
├── data/
│   └── report_paperformat_data.xml
├── reports/
│   ├── gpl_report_templates.xml      # Templates de base
│   ├── gpl_montage_certificate.xml   # Certificat de montage
│   ├── gpl_triennial_certificate.xml # Contrôle triennal
│   ├── gpl_authorization_report.xml  # Autorisation GPL
│   ├── gpl_bordereau_envoi.xml      # Bordereau d'envoi
│   ├── gpl_custom_invoice.xml       # Facture personnalisée
│   ├── gpl_inspection_report.xml    # Rapport d'inspection
│   ├── gpl_repair_report.xml        # Ordre de réparation
│   └── gpl_reservoir_report.xml     # État des réservoirs
├── views/
│   └── gpl_reports_menus.xml        # Structure des menus
└── static/
    └── description/
        ├── icon.png
        └── index.html
```

## 🔄 Intégration avec les autres modules

Le module s'intègre automatiquement avec :
- **cpss_gpl_operations** : Rapports d'installations et réparations
- **cpss_gpl_garage** : Informations véhicules et clients
- **cpss_gpl_reservoir** : Données des réservoirs GPL
- **account** : Factures personnalisées

## 📝 Formats d'export

- **PDF** : Format par défaut pour tous les rapports
- **Excel** : Disponible pour les rapports analytiques
- **HTML** : Prévisualisation dans le navigateur

## 🚨 Points d'attention

1. **Numérotation** : Les certificats utilisent une numérotation automatique
2. **Archivage** : Les rapports générés sont automatiquement attachés aux enregistrements
3. **Sécurité** : Les accès sont contrôlés par les groupes GPL définis dans `cpss_gpl_base`
4. **Performance** : Pour les rapports volumineux, utiliser la génération en arrière-plan

## 🐛 Dépannage

### Erreur de génération PDF
- Vérifier l'installation de wkhtmltopdf
- Contrôler les permissions sur le dossier temporaire

### Données manquantes
- S'assurer que tous les champs requis sont remplis
- Vérifier les relations entre les modules

### Format incorrect
- Recharger les formats de papier par défaut
- Vérifier la configuration de l'imprimante système

## 📞 Support

Pour toute question ou assistance :
- **Email** : support@cedarpss.com
- **Documentation** : Incluse dans le module
- **Tickets** : Via le portail client CPSS

## 📜 Licence

Ce module fait partie de la suite CPSS GPL et est distribué sous licence LGPL-3.

---

*Cedar Peak Systems & Solutions - Solutions GPL professionnelles pour l'automobile*
