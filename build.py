#!/usr/bin/env python3
"""
Plurielles Magazine Website Builder
Generates a complete static website from the magazine's PDF archives.
"""

import os
import re
import shutil
import json
import zipfile
import datetime
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF not installed. Run: pip install pymupdf")
    exit(1)

# ─── Paths ───────────────────────────────────────────────────────────────────
SOURCE_BASE = Path("/Users/david/ClaudeCode/plurielles/PLURIELLES")
ARTICLES_BY_ISSUE = Path("/Users/david/ClaudeCode/plurielles/Articles Plurielles 7-23") / "Plurielles de 7 à 23 "
ARTICLES_PL23 = SOURCE_BASE / "Articles de PL23"
ARTICLES_PL24_DIR = SOURCE_BASE / "PL24 corr 10:9:23"
ARTICLES_PL24_ALT = SOURCE_BASE / "Derniers documents PL24"
PDF_ISSUES = SOURCE_BASE / "matériel pour site revueplurielles" / "Plurielles en PDF"
SCANNED_PDFS = SOURCE_BASE / "Materiel p site PL p DDR"
OUTPUT = Path("/Users/david/ClaudeCode/plurielles-site")

# ─── Issue 23 article metadata (from the official Sommaire) ──────────────────
PL23_ARTICLES = {
    0:  ("La rédaction", "Sommaire du numéro 23"),
    1:  ("Izio Rosenman et Anny Dayan Rosenman", "Éditorial — Les Juifs dans la modernité"),
    2:  ("Alessandro Guetta", "L'Italie et la « voie juive vers la modernité »"),
    3:  ("Ariane Bendavid", "Adopter et adapter, l'appel de la modernité chez les Juifs"),
    4:  ("Simon Wuhl", "De Simon Dubnov à Michael Walzer — des penseurs juifs face au modèle français de laïcité"),
    5:  ("Ilan Greilsammer", "Israël et modernité"),
    6:  ("Léa Veinstein", "Une impossible métamorphose : réflexions sur Kafka et la modernité juive"),
    7:  ("Itzhak Goldberg", "L'École de Paris, une avant-garde juive ?"),
    8:  ("Yolande Zauberman", "À propos du film M — entretien avec Monique Halpern et Jean-Charles Szurek"),
    9:  ("Anny Dayan Rosenman", "Moi Ivan, toi Abraham de Yolande Zauberman"),
    10: ("Izio Rosenman", "Pour un judaïsme éthique — Entretien avec Brigitte Stora"),
    11: ("David Biale", "Héritage"),
    13: ("Rachel Ertel", "Les vies, les morts, les résurrections d'Avrom Sutzkever"),
    14: ("Carole Ksiazenicer-Matheron", "Témoigner par la poésie : modernités chromatiques chez Avrom Sutzkever"),
    15: ("Claude Mouchard", "Avrom Sutzkever témoin"),
    16: ("Guillaume Métayer", "La poésie d'Avrom Sutzkever ou le temple du souffle"),
    17: ("Martin Rueff", "Éblouissant, dans le règne de la nuit"),
    18: ("Anny Dayan Rosenman", "Notre ami Rolland Doukhan"),
    19: ("Rolland Doukhan", "Le contre-sens (nouvelle)"),
    20: ("Norbert Czarny", "Choisir le costume — introduction à l'œuvre d'Eduardo Halfon"),
    21: ("Les auteurs", "Les auteurs du numéro 23 de PLURIELLES"),
    22: ("La rédaction", "Sommaires des numéros précédents"),
}


# ─── Issue metadata ───────────────────────────────────────────────────────────
ISSUES = {
    1: {
        "title": "Les Juifs dans le monde contemporain",
        "year": "1993",
        "dossier": "Premier numéro",
        "articles": [
            ("Rolland Doukhan", "Quand les eaux mêlées se trouvent être toutes juives"),
            ("Albert Memmi", "Humanisme"),
            ("Maurice Politi", "Les élections israéliennes"),
            ("Rolland Doukhan, Izio Rosenman, Violette Attal-Lefi", "L'œil et la dent"),
            ("Kurt Niedermeier", "Lexique de la vie politique israélienne"),
            ("Izio Rosenman", "Les Juifs et l'Europe"),
            ("Anne Rabinovitch", "Retour en Lituanie"),
            ("Daniel Farhi", "Le Bebeth-Dine"),
            ("Violette Attal-Lefi", "Juifs laïques, un mouvement en marche"),
            ("Rolland Doukhan", "L'Unité de Valeur"),
            ("Evelyne Dorra-Botbol", "Monsieur Mani, de A.B. Yehoshua"),
        ],
    },
    2: {
        "title": "Notre devoir d'ingérence / Le Ghetto de Varsovie",
        "year": "1993",
        "dossier": "Le cinquantenaire de la révolte du ghetto de Varsovie",
        "articles": [
            ("Me Théo Klein", "Quel avenir pour les Juifs de France ?"),
            ("Alexandre Adler", "Immigration et intégration des Juifs en France"),
            ("Annette Wieviorka", "Le Ghetto de Varsovie, la Révolte"),
            ("Anny Dayan-Rosenman", "Romain Gary, une judéité ventriloque"),
            ("Hubert Hannoun", "Maïmonide fils et père de l'Histoire"),
        ],
    },
    3: {
        "title": "Un horizon de paix / Le nouveau dialogue judéo-arabe",
        "year": "1994",
        "dossier": "Le nouveau dialogue judéo-arabe",
        "articles": [
            ("Théo Klein", "Le judaïsme français, déclin ou renaissance"),
            ("Itzhak Rabin", "Un discours humaniste"),
            ("André Azoulay", "Les vertus du dialogue"),
            ("Violette Attal-Lefi", "La Tunisie au miroir de sa communauté juive"),
            ("Lucette Valensi", "Tunisie – Espaces publics, espaces communautaires"),
            ("Annie Goldmann", "La fascination de la femme non-juive dans l'œuvre d'Albert Cohen"),
        ],
    },
    4: {
        "title": "Mémoire, violence et vigilance / Lire la Bible",
        "year": "1995",
        "dossier": "Lire la Bible",
        "articles": [
            ("Erich Fromm", "Une vision humaniste radicale de la Bible"),
            ("Yaakov Malkin", "Qui est Dieu ? Approche séculière de la littérature de la Bible"),
            ("Jacques Hassoun", "Joseph ou les infortunes de la vertu"),
            ("Henri Raczymow", "Le dit du prophète Jonas"),
            ("Annie Goldmann", "La Bible au cinéma"),
            ("Claude Klein", "Une constitution pour Israël ?"),
            ("Anny Dayan-Rosenman", "Albert Memmi, un judaïsme à contre courant"),
        ],
    },
    5: {
        "title": "Terrorisme et paix / Identités juives et modernité",
        "year": "1996",
        "dossier": "Identités juives et modernité",
        "articles": [
            ("Albert Memmi", "Sortir du Moyen-Age"),
            ("Egon Friedler", "L'expérience des Lumières – la Haskala"),
            ("Francis Grimberg", "Identités juives et citoyenneté française"),
            ("Hubert Hannoun", "Lévinas, un homme responsable"),
            ("Itzhak Goldberg", "L'admirable légèreté de l'être – Marc Chagall"),
        ],
    },
    6: {
        "title": "Inquiétudes / Juifs parmi les nations",
        "year": "1997",
        "dossier": "Juifs parmi les nations",
        "articles": [
            ("Julien Dray", "Exclusion et racisme en France"),
            ("Michel Zaoui", "Négationnisme et loi Gayssot"),
            ("Yaakov Malkin", "Juifs parmi les nations"),
            ("Élisabeth Badinter", "Les dangers qui nous guettent"),
            ("Simone Veil", "Française, juive et laïque"),
            ("Dominique Schnapper", "Société laïque, société multiculturelle, mariages mixtes"),
            ("Martine Leibovici", "La justice et la pluralité des peuples"),
            ("Yehuda Bauer", "La Shoah est-elle comparable aux autres génocides ?"),
        ],
    },
    7: {
        "title": "Langues juives de la diaspora",
        "year": "1998-1999",
        "dossier": "Langues juives de la diaspora",
        "articles": [
            # Order matches Python string-sort of PDF filenames (pl7-NNN.pdf)
            ("Henri Raczymow", "Retrouver la langue perdue"),                                                           # pl7-102-106
            ("Jacques Burko", "Les emprunts au yiddish dans la langue polonaise familiale"),                             # pl7-107-111
            ("Jacques Hassoun", "Les Juifs d'Alexandrie et le multiculturalisme"),                                       # pl7-11-17
            ("Marcel Cohen", "Lettres à Antonio Saura"),                                                                 # pl7-112-114
            ("Marc-Henri Klein", "La Tour de Babel : l'origine des langues"),                                            # pl7-117-121
            ("Franz Kafka", "Extrait (texte sur le yiddish)"),                                                           # pl7-122
            ("Rolland Doukhan", "Ma diglossie, au loin, ma disparue…"),                                                 # pl7-123-130
            ("Haïm Zafrani", "Traditions poétiques et musicales juives au Maroc"),                                      # pl7-131-137
            ("Albert Memmi", "Document"),                                                                                # pl7-139-141
            ("M. Zalc", "Expérience vécue au Japon"),                                                                   # pl7-142-143
            ("Shlomo Ben Ami", "Après les accords de Wye Plantation"),                                                  # pl7-144-149
            ("Lucie Bollens-Beckouche", "Histoire et mythe du couple"),                                                  # pl7-150-154
            ("Dominique Bourel", "Moses Mendelssohn, fondateur d'un judaïsme moderne"),                                 # pl7-155-157
            ("Anny Dayan Rosenman", "Entendre la voix du témoin"),                                                      # pl7-158-164
            ("Egon Friedler", "L'Intégration des Juifs en Argentine"),                                                  # pl7-165-167
            ("Michael Löwy", "Romantisme, messianisme et marxisme dans la philosophie de Walter Benjamin"),              # pl7-168-179
            ("", "D'après l'Encyclopedia Judaïca"),                                                                      # pl7-18-19
            ("Olivier Revault d'Allonnes", "La loi de quel droit ? A propos d'Arnold Schoenberg"),                      # pl7-180-187
            ("Nahma Sandrow", "Isaac Gordin, un maskil créateur du théâtre yiddish"),                                   # pl7-188-191
            ("Berthe Burko-Falcman", "Le chien du train"),                                                              # pl7-192-196
            ("", "Deux romances judéo-espagnoles"),                                                                      # pl7-197-201
            ("", "Déclaration du 7e Congrès de la Fédération"),                                                         # pl7-202-205
            ("Mireille Hadas-Lebel", "La renaissance de l'hébreu"),                                                     # pl7-21-26
            ("Delphine Bechtel", "La guerre des langues entre l'hébreu et le yiddish"),                                 # pl7-27-47,49
            ("Izio Rosenman", "Éditorial : Langue, culture et identité"),                                               # pl7-4-5
            ("Joseph Chetrit", "Les langues juives d'Afrique du Nord"),                                                 # pl7-50-57
            ("Itzhok Niborski", "Le Yiddish, un passé, un présent et un futur ?"),                                      # pl7-59-71
            ("Claude Mossé", "Judaïsme et hellénisme"),                                                                 # pl7-7-10
            ("Haïm-Vidal Sephiha", "Langue et littérature judéo-espagnoles"),                                           # pl7-72-79
            ("Charles Dobzynski", "Langues juives de diaspora"),                                                         # pl7-80-84
            ("Régine Robin", "La nostalgie du yiddish chez Kafka"),                                                      # pl7-88-97
            ("Franz Kafka", "Discours sur la langue yiddish"),                                                           # pl7-99-101
        ],
        # Printing order: indices into string-sorted PDF list above, by page number
        "order": [24, 27, 2, 16, 22, 23, 25, 26, 28, 29, 30, 31, 0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 18, 19, 20, 21],
    },
    8: {
        "title": "Un engagement vers les autres / Les Juifs et l'engagement politique",
        "year": "2000",
        "dossier": "Les Juifs et l'engagement politique",
        "articles": [
            # Order matches Python string-sort of PDF filenames (pl8-NNN.pdf)
            ("Jacques Burko", "Les Juifs dans les combats pour l'indépendance polonaise au XIXe siècle"),               # pl8-10-22
            ("Lazare Bitoun", "Juifs et Noirs au miroir de la littérature"),                                             # pl8-103-107
            ("", "Question à David Grossman"),                                                                           # pl8-108
            ("Allan Levine", "Un rabbin avec Martin Luther King dans la lutte pour les droits civiques"),                # pl8-110-116
            ("Eveline Amoursky", "Mandelstam : l'identité assumée"),                                                    # pl8-117-122
            ("Huguette Ivanier", "Une éthique pour notre temps : Lévinas ou l'humanisme de l'Autre"),                  # pl8-123-127
            ("Charles Dobzynski", "Dialogue à Jérusalem"),                                                              # pl8-128
            ("Rachid Aous", "Le Matrouz de Simon Elbaz"),                                                               # pl8-129-132
            ("Annie Goldmann", "La deuxième guerre mondiale sur les écrans français"),                                   # pl8-133-138
            ("Rolland Doukhan", "Le fil du temps (Éphémérides)"),                                                       # pl8-140-158
            ("Henri Minczeles", "Engagement universaliste et identité nationale : le Bund"),                             # pl8-23-27
            ("Alain Dieckhoff", "Le sionisme : la réussite d'un projet national"),                                      # pl8-28-32
            ("Henry Bulawko", "Bernard Lazare, le lutteur"),                                                             # pl8-33
            ("Jean-Jacques Marie", "Les Juifs dans la Révolution russe"),                                               # pl8-34-39
            ("Izio Rosenman", "Éditorial : Un engagement vers les autres"),                                              # pl8-4-5
            ("Jean-Charles Szurek", "En Espagne… et ailleurs"),                                                         # pl8-40
            ("Arno Lustiger", "Les Juifs dans la guerre d'Espagne"),                                                    # pl8-41-46
            ("", "La France, centre de l'aide internationale à l'Espagne républicaine"),                                 # pl8-47-50
            ("G. E. Sichon", "Frantisek Kriegel, l'insoumis"),                                                          # pl8-51-59
            ("Anny Dayan Rosenman", "Albert Cohen, un Valeureux militant"),                                              # pl8-60-61
            ("Lucien Lazare", "La résistance juive dans sa spécificité"),                                               # pl8-62-65
            ("Anny Dayan Rosenman", "Des terroristes à la retraite"),                                                   # pl8-66-69
            ("Hubert Hannoun", "Barukh Spinoza, rebelle politique"),                                                    # pl8-7-9
            ("Gérard Israël", "René Cassin, l'homme des droits de l'homme"),                                            # pl8-70-71
            ("Jean-Marc Izrine", "Le Mouvement libertaire juif"),                                                        # pl8-72-77
            ("Charles Dobzynski", "On ne saurait juger sa vie"),                                                        # pl8-78
            ("Rolland Doukhan", "Daniel Timsit, entretien"),                                                             # pl8-79-82
            ("Astrid Starck", "Lionel Rogosin, un cinéaste contre l'apartheid"),                                        # pl8-83-93
            ("Rolland Doukhan", "Daniel Timsit, Suite baroque"),                                                        # pl8-94-102
        ],
        "order": [14, 22, 0, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20, 21, 23, 24, 25, 26, 27, 28, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    },
    9: {
        "title": "Les Juifs et l'Europe",
        "year": "2001",
        "dossier": "Les Juifs et l'Europe",
        "articles": [
            # Order matches Python string-sort of PDF filenames (pl9-NNN.pdf)
            ("Hugo Samuel", "Poèmes"),                                                                                   # pl9-101-105
            ("Rolland Doukhan", "L'Autre moitié du vent (extrait)"),                                                    # pl9-107-113
            ("Eveline Amoursky", "Marina Tsvetaeva – Ossip Mandelstam. Écho"),                                          # pl9-115-121
            ("Mikael Elbaz", "Paria et rebelle : Abraham Serfaty et le judaïsme marocain"),                             # pl9-122-130
            ("Rolland Doukhan", "Les rêveries de la femme sauvage (compte rendu)"),                                     # pl9-131
            ("Yves Plasseraud", "État-nation et minorités en Europe"),                                                   # pl9-18-27
            ("Alain Touraine", "Nous sommes tous des Juifs européens"),                                                  # pl9-28-31
            ("Élie Barnavi", "Le Musée de l'Europe à Bruxelles"),                                                       # pl9-32-36
            ("Michael Löwy", "La culture juive allemande entre assimilation et catastrophe"),                            # pl9-37-44
            ("Izio Rosenman", "Éditorial"),                                                                              # pl9-4-6
            ("Michel Abitbol", "Entre Orient et Occident"),                                                              # pl9-45-51
            ("Diana Pinto", "Vers une identité juive européenne"),                                                       # pl9-52-63
            ("Henri Minczeles", "Le concept de l'extraterritorialité juive"),                                            # pl9-64-72
            ("Jean-Charles Szurek", "Jedwabne et la mémoire polonaise"),                                                # pl9-73-75
            ("Joanna Tokarska-Bakir", "L'obsession de l'innocence"),                                                    # pl9-76-83
            ("Daniel Oppenheim", "Dans l'après-coup de l'événement"),                                                   # pl9-84-91
            ("Daniel Lindenberg", "Europa Judaïca ?"),                                                                   # pl9-9-17
            ("Nicole Eizner", "Juifs d'Europe. Un témoignage"),                                                         # pl9-92-98
        ],
        "order": [9, 16, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 17, 0, 1, 2, 3, 4],
    },
    10: {
        "title": "Kaléidoscope / Israël-diasporas – interrogations",
        "year": "2002",
        "dossier": "Israël-diasporas – interrogations",
        "articles": [
            # Order matches Python string-sort of PDF filenames (pl10-NNN.pdf)
            ("Françoise Carasso", "Primo Levi, le malentendu"),                                                          # pl10-100-106
            ("Michèle Tauber", "Aharon Appelfeld, ou la mémoire des langues"),                                          # pl10-107-117
            ("Itzhak Goldberg", "Le petit Chagall illustré"),                                                            # pl10-118-123
            ("Cyrille Fleischman", "Quarante-sept moins quatre"),                                                        # pl10-124-127
            ("Daniel Oppenheim", "Trois jours et un enfant"),                                                            # pl10-128-130
            ("Chantal Steinberg", "Gilda Stambouli souffre… Paula Jacques ne la plaint pas"),                           # pl10-131-132
            ("", "Yaakov Malkin, La foi athée des Juifs laïques"),                                                       # pl10-133-134
            ("", "L'Europe ashkénaze. Écriture de l'Histoire et identité juive"),                                        # pl10-135
            ("Amos Oz et David Grossman", "Débat sur Israël, la situation de la gauche, et du monde"),                  # pl10-14-21
            ("Daniel Oppenheim", "Passé et présent, idéal et réalité"),                                                 # pl10-22-28
            ("Ilan Greilsammer", "Gauche française, gauche israélienne : regards croisés"),                              # pl10-29-33
            ("", "Cinéma israélien/Cinéma Juif : la quête d'une identité"),                                              # pl10-34-41
            ("Izio Rosenman", "Éditorial : Kaléidoscope"),                                                               # pl10-4-5
            ("Mihal Friedman et Corrine Levitt", "Juifs et Américains : une communauté intégrée"),                      # pl10-42-46
            ("Denise Goitein-Galpérin", "Albert Cohen et l'Histoire : son action politique et diplomatique"),            # pl10-47-56
            ("Jean-Charles Szurek", "Le duo Eyal Sivan et Rony Brauman"),                                               # pl10-57-60
            ("Olivier Revault d'Allonnes", "Être Goy en diaspora"),                                                     # pl10-61-64
            ("", "Nahum Goldmann"),                                                                                      # pl10-65-66
            ("", "Léon Blum, un républicain juif sioniste"),                                                             # pl10-67-69
            ("Jacques Burko", "Je suis un Juif diasporiste"),                                                            # pl10-7-13
            ("", "Pierre Mendès France"),                                                                                 # pl10-70-72
            ("", "Raymond Aron, le 'peuple juif', Israël"),                                                              # pl10-73-75
            ("Liliane Atlan", "Interview : vous et Israël"),                                                             # pl10-78-79
            ("Robert Bober", "Interview : vous et Israël"),                                                              # pl10-80-83
            ("Bianca Lechevalier-Haïm", "Interview : vous et Israël"),                                                  # pl10-84
            ("Henri Raczymow", "Interview : vous et Israël"),                                                            # pl10-85
            ("Régine Robin", "Interview : vous et Israël"),                                                              # pl10-86-87
            ("Rachid Aous", "Laïcité et démocratie en terre d'Islam : une nécessité vitale"),                           # pl10-88-99
        ],
        "order": [12, 19, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23, 24, 25, 26, 27, 0, 1, 2, 3, 4, 5, 6, 7],
    },
    11: {
        "title": "Voyages imaginaires, voyages réels",
        "year": "2003",
        "dossier": "Voyages",
        "articles": [
            # Order matches Python string-sort of PDF filenames (pl11-NNN.pdf)
            ("Carole Ksiazenicer-Matheron", "America, America – Récits juifs du Nouveau Monde"),                        # pl11-15-25
            ("Rolland Doukhan", "L'Amérique"),                                                                           # pl11-26-29
            ("Catherine Dana", "En attendant l'Amérique (extrait)"),                                                    # pl11-30-31
            ("Marie-France Rouart", "Le Juif errant vu lui-même"),                                                      # pl11-32-42
            ("Izio Rosenman", "Éditorial : Voyages imaginaires, voyages réels"),                                         # pl11-4-5
            ("Albert Cohen", "Les Valeureux (extrait)"),                                                                 # pl11-43-44
            ("Jacques Burko", "L'histoire des voyages des trois Benjamin"),                                              # pl11-45-52
            ("Haim Zafrani", "Les lettrés-voyageurs"),                                                                   # pl11-53-55
            ("J. Béhar-Druais et C. Steinberg", "Joseph Halévy, un savant voyageur (1827-1917)"),                       # pl11-56-59
            ("Régine Azria", "Prédicateurs, cochers et colporteurs…"),                                                  # pl11-60-63
            ("Henriette Asséo", "Tsiganes d'Europe – Les impasses de l'extra-territorialité mentale"),                  # pl11-64-71
            ("Philippe Zard", "L'Europe et les Juifs. Les généalogies spécieuses de Jean-Claude Milner"),               # pl11-74-88
            ("Daniel Oppenheim", "Éthique du voyage. Rêver, partir, retrouver l'Autre, se retrouver"),                 # pl11-8-14
            ("Olivier Revault d'Allonnes", "Un voyage manqué dans la littérature"),                                     # pl11-89-91
            ("Nicole Eizner", "Voyage immobile en Israël"),                                                              # pl11-92-93
            ("Hélène Oppenheim-Gluckman", "Être Juif en Chine"),                                                       # pl11-94-96
            ("Chantal Steinberg", "Amos Oz, Ni exil, ni royaume"),                                                      # pl11-97-99
        ],
        "order": [4, 12, 0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16],
    },
    12: {
        "title": "Interroger, transmettre, être fidèle ou infidèle ?",
        "year": "2004",
        "dossier": "Fidélité-infidélité",
        "articles": [
            # Order matches Python string-sort of PDF filenames (pl12-NNN.pdf)
            ("Daniel Lindenberg", "Le franco-judaïsme entre fidélité et infidélité"),                                    # pl12-11-23
            ("Marc-Henri Klein", "Sabbataï Tsvi, Messie Marrane"),                                                       # pl12-111-114
            ("Jacques Burko", "Traduire les poètes ?"),                                                                  # pl12-115-124
            ("Nathalie Debrauwère", "L'infidèle chez Edmond Jabès"),                                                    # pl12-125-140
            ("Philippe Zard", "Le Commandeur aux enfers. Libres variations sur Don Juan"),                               # pl12-141-158
            ("Carole Ksiazenicer-Matheron", "Isaac Bashevis Singer, la fiction de l'infidélité"),                       # pl12-159-174
            ("Daniel Oppenheim", "Entre tradition et subversion, la contradiction du roi des schnorrers"),               # pl12-175-187
            ("Rolland Doukhan", "Extraits littéraires"),                                                                 # pl12-191-199
            ("Daniel Dayan", "Information et télévision"),                                                               # pl12-202-215
            ("Rolland Doukhan", "Va, vis et deviens (film)"),                                                            # pl12-217-218
            ("Jean-Charles Szurek", "Alexandra Laignel-Lavastine – Esprits d'Europe"),                                  # pl12-219-222
            ("Chantal Steinberg", "Aharon Appelfeld : Histoire d'une vie"),                                              # pl12-223-226
            ("Henry Méchoulan", "Fidélité et infidélité au judaïsme chez les juifs d'Espagne"),                         # pl12-25-38
            ("Ariane Bendavid", "Spinoza face à sa judéité, le défi de la laïcité"),                                   # pl12-40-50
            ("Martine Leibovici", "Mendelssohn ou la fidélité au-delà de la rationalité"),                              # pl12-51-66
            ("Izio Rosenman", "Éditorial : interroger, transmettre, être fidèle ou infidèle ?"),                        # pl12-6-8
            ("Edwige Encaoua", "Entre fidélité et infidélité, réflexions pour une mouvance juive laïque"),              # pl12-67-75
            ("Hélène Oppenheim-Gluckman", "Fidélité vivante ou figée"),                                                 # pl12-77-92
            ("Henri Meschonnic", "Fidèle, infidèle, c'est tout comme, merci mon signe"),                                # pl12-93-109
        ],
        "order": [15, 0, 12, 13, 14, 16, 17, 18, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    },
    13: {
        "title": "Sortir du ressentiment ?",
        "year": "2005",
        "dossier": "Le ressentiment",
        "articles": [
            # Order matches Python string-sort of PDF filenames (pl13.NNN.pdf — dots not dashes)
            ("Jacques Burko", "Une histoire marrane (et pas très marrante)"),                                            # pl13.108-109
            ("Rivon Krygier", "Entretien sur le ressentiment dans le judaïsme"),                                        # pl13.11-21
            ("Daniel Lindenberg", "Giflés par la réalité : en France aussi ?"),                                         # pl13.110-116
            ("Gilberte Finkel", "Ressentiments et désarroi d'une Israélienne"),                                         # pl13.117-118
            ("Jacques Burko", "Une histoire édifiante"),                                                                 # pl13.122
            ("Jean-Charles Szurek", "Jerzy Ficowski, poète et écrivain polonais"),                                      # pl13.123-126
            ("Jean-Charles Szurek", "Danielle Rozenberg, L'Espagne contemporaine et la question juive"),                # pl13.127-129
            ("Anny Dayan Rosenman", "Berthe Burko-Falcman, Un prénom républicain"),                                     # pl13.130
            ("Rita Thalmann", "La culture du ressentiment dans l'Allemagne du IIe au IIIe Reich"),                      # pl13.22-31
            ("Paul Zawadski", "Temps et ressentiment"),                                                                  # pl13.32-40
            ("Izio Rosenman", "Éditorial : Sortir du ressentiment ?"),                                                   # pl13.4-5
            ("Janine Altounian", "Ni ressentiment, ni pardon"),                                                          # pl13.41-49
            ("Seloua Luste Boulbina", "L'ascétisme, une maladie érigée en idéal"),                                     # pl13.50-57
            ("Andrzej Szczypiorski", "Le ressentiment du Goy contre le Juif"),                                          # pl13.58-59
            ("Catherine Chalier", "Le ressentiment de Caïn"),                                                           # pl13.6-10
            ("Jean Beckouche", "Le travail humanitaire et le conflit israélo-palestinien"),                              # pl13.60-67
            ("Physicians for Human Rights-Israel", "PHR-Israel"),                                                        # pl13.68-69
            ("Daniel Oppenheim", "Le sentiment de voir ses droits non reconnus"),                                        # pl13.70-77
            ("Michel Zaoui", "Réflexions sur l'affaire Lipietz"),                                                       # pl13.78-81
            ("Michèle Fellous", "Conflits de mémoire, conflits de victimes"),                                            # pl13.82-87
            ("Philippe Zard", "Un étrange apôtre. Réflexions sur la question Badiou"),                                  # pl13.90-97
            ("Régine Azria", "Les juifs et l'interdit de l'image"),                                                     # pl13.98-107
        ],
        "order": [10, 14, 1, 8, 9, 11, 12, 13, 15, 16, 17, 18, 19, 20, 21, 0, 2, 3, 4, 5, 6, 7],
    },
    14: {
        "title": "Frontières",
        "year": "2007",
        "dossier": "Frontières",
        "articles": [
            # Order matches Python string-sort of PDF filenames (pl14-NNN.pdf)
            ("Philippe Zard", "De quelques enjeux éthiques de La Métamorphose"),                                        # pl14-106-114
            ("Daniel Oppenheim", "Variations sur la frontière, avec Iouri Olecha et Georges Orwell"),                   # pl14-115-125
            ("Anny Dayan Rosenman", "Aux frontières de l'identité et de l'Histoire – Monsieur Klein"),                 # pl14-126-134
            ("Ilan Greilsammer", "Réflexions sur les futures frontières israélo-palestiniennes"),                       # pl14-135-139
            ("Denis Charbit", "La gauche aux prises avec le sionisme"),                                                 # pl14-143-149
            ("Catherine Witol de Wenden", "Les frontières de l'Europe"),                                                # pl14-15-28
            ("Philippe Velilla", "Les Juifs de France et l'élection présidentielle de 2007"),                           # pl14-150-159
            ("Rolland Doukhan", "La faute de la mariée"),                                                               # pl14-160-171
            ("Chams Eddine Hadef-Benfatima", "Dibbouk et Dom Juan"),                                                   # pl14-172-175
            ("Jean-Charles Szurek", "Jan Gross, conscience juive de la Pologne"),                                       # pl14-176-179
            ("Izio Rosenman et Jean-Charles Szurek", "Hommage à Jacques Burko"),                                       # pl14-183-184
            ("Jean-Charles Szurek", "Histoire d'une traduction, histoire d'une amitié"),                                # pl14-185
            ("Jacques Burko", "Place des Abbesses (poème)"),                                                            # pl14-186
            ("Chantal Steinberg", "Alaa El Aswany, Chicago"),                                                           # pl14-189-191
            ("Chantal Steinberg", "Orly Castel-Bloom, Textile"),                                                        # pl14-192
            ("Carole Ksiazenicer-Matheron", "Royaumes juifs. Trésors de la littérature yiddish"),                      # pl14-193-194
            ("Carole Ksiazenicer-Matheron", "Frontières ashkénazes"),                                                   # pl14-29-40
            ("Izio Rosenman", "Éditorial"),                                                                              # pl14-3-4
            ("Riccardo Calimani", "Le ghetto – paradigme des paradoxes de l'histoire juive"),                           # pl14-41-47
            ("Zygmunt Bauman", "Juifs et Européens. Les anciens et les nouveaux"),                                      # pl14-48-58
            ("Emilia Ndiaye", "Frontières entre le barbare et le civilisé dans l'Antiquité"),                           # pl14-5-14
            ("Henry Méchoulan", "Les statuts de pureté de sang"),                                                       # pl14-59-66
            ("Sophie Hirel-Wouts", "Traces marranes dans La Célestine de Fernando de Rojas"),                          # pl14-67-75
            ("Régine Azria", "Communauté et communautarisme"),                                                           # pl14-76-82
            ("Philippe Zard et Nathalie Azoulai", "La frontière invisible (entretien)"),                                # pl14-83-91
            ("Marita Keilson-Lauritz", "Entre Amsterdam et Jérusalem – Jacob Israël de Haan"),                         # pl14-92-105
        ],
        "order": [17, 20, 5, 16, 18, 19, 21, 22, 23, 24, 25, 0, 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    },
    15: {
        "title": "Les Pères Juifs",
        "year": "2009",
        "dossier": "Les Pères Juifs",
        "articles": [
            # Order matches Python string-sort of PDF filenames (pl15-NNN.pdf)
            ("Philippe Velilla", "Barack Obama, les Juifs et Israël"),                                                   # pl15-109-118
            ("", "Les sionismes et la paix (table ronde)"),                                                              # pl15-119-131
            ("Chantal Steinberg", "Le village de l'Allemand de Boualem Sansal"),                                        # pl15-133-134
            ("Michel Grojnowski", "Je me souviens"),                                                                     # pl15-15-20
            ("Carole Ksiazenicer-Matheron", "En quête du père – devenirs de la disparition"),                           # pl15-21-30
            ("Izio Rosenman", "Éditorial : Les pères juifs, pas assez ou trop présents ?"),                              # pl15-3-4
            ("Anny Dayan Rosenman", "Romain Gary – au nom du père"),                                                    # pl15-31-40
            ("Pierre Pachet", "Le père juif selon Bruno Schulz"),                                                        # pl15-41-42
            ("Daniel Oppenheim", "Être fils, être père dans la Shoah et après"),                                        # pl15-43-50
            ("Sophie Nizard", "Les pères juifs adoptifs sont-ils des mères juives ?"),                                  # pl15-51-61
            ("Jean-Claude Grumberg", "Entretien : À propos de Mon père. Inventaire"),                                   # pl15-6-8
            ("Sylvie Sesé-Léger", "Sigmund Freud, un père"),                                                            # pl15-63-70
            ("Hélène Oppenheim-Gluckman", "Le meurtre du père"),                                                        # pl15-71-75
            ("Mireille Hadas-Lebel", "Mariages mixtes – matrilinéarité ou patrilinéarité"),                             # pl15-77-80
            ("Théo Klein", "Conversation imaginaire avec Isaac"),                                                        # pl15-81-89
            ("Jean-Charles Szurek", "La Guerre d'Espagne, mon père et moi"),                                            # pl15-9-14
            ("Jean-Yves Potel", "Anna Langfus et son double"),                                                           # pl15-91-96
            ("Anna Langfus", "De la difficulté pour un écrivain de traduire en fiction la tragédie juive"),             # pl15-97-98
            ("Samuel Ghiles-Meilhac", "Une diplomatie de la mémoire ?"),                                                # pl15-99-108
        ],
        "order": [5, 10, 15, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14, 16, 17, 18, 0, 1, 2],
    },
    16: {
        "title": "Il était une fois l'Amérique – Juifs aux États-Unis",
        "year": "2010",
        "dossier": "Juifs aux États-Unis",
        "articles": [
            # Order matches Python string-sort of PDF filenames (pl16-NNN.pdf)
            ("Rachel Ertel", "Le vif saisi le mort : sur Cynthia Ozick"),                                               # pl16-102-110
            ("Guido Furci", "Fictions d'Amérique – Goodbye, Columbus"),                                                 # pl16-112-118
            ("Anissia Bouillot", "« The other kind » : à propos de l'œuvre de James Gray"),                             # pl16-120-131
            ("Nathalie Azoulai", "La question juive dans Mad Men"),                                                      # pl16-132-136
            ("Mathias Dreyfuss et Raphaël Sigal", "Radical Jewish Culture"),                                             # pl16-138-150
            ("Henri Lewi", "Incertitudes américaines"),                                                                  # pl16-152-161
            ("Nadine Vasseur", "Alan Sandomir, Détective dans la NYPD"),                                                # pl16-162-165
            ("Nadine Vasseur", "Marc Marder, Un Américain à Paris"),                                                    # pl16-166-168
            ("Philippe Velilla", "L'internationale conservatrice et Israël"),                                            # pl16-170-178
            ("Rachel Ertel", "Sutzkever – Lumière et ombre"),                                                            # pl16-180-187
            ("Chantal Steinberg", "L'horizon de Patrick Modiano"),                                                      # pl16-188
            ("Jean-Charles Szurek", "Henri Minczeles, Le mouvement ouvrier juif"),                                      # pl16-189
            ("", "Appel à la raison"),                                                                                   # pl16-190
            ("Carole Ksiazenicer-Matheron", "Abe Cahan, une vie en Amérique"),                                          # pl16-24-36
            ("Hélène Oppenheim-Gluckman", "Freud et l'Amérique"),                                                       # pl16-38-45
            ("Izio Rosenman", "Éditorial : Les Juifs d'Amérique d'hier à demain"),                                      # pl16-4-5
            ("Jacques Solé", "L'apogée de la prostitution juive aux États-Unis vers 1900"),                             # pl16-46-50
            ("Rabbin Stephen Berkovitz", "Le mouvement reconstructionniste du judaïsme américain"),                      # pl16-52-61
            ("Françoise S. Ouzan", "Le judaïsme américain en question – transformations identitaires"),                  # pl16-6-23
            ("Nicole Lapierre", "L'histoire de Julius Lester"),                                                          # pl16-62-73
            ("Lewis R. Gordon", "Réflexions sur la question afro-juive"),                                               # pl16-74-81
            ("Célia Belin", "J Street face à l'AIPAC : quand David s'attaque à Goliath"),                              # pl16-82-87
            ("Daniel Oppenheim", "Lamed Shapiro, de Kichinev 1903 à New-York 1930"),                                   # pl16-88-95
            ("Alan Astro", "Deux écrivains yiddish au Texas"),                                                           # pl16-96-101
        ],
        "order": [15, 18, 13, 14, 16, 17, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    },
    17: {
        "title": "Figures du retour – retrouver, réparer, renouer",
        "year": "2012",
        "dossier": "Figures du retour",
        "articles": [
            # Order matches Python string-sort of PDF filenames (pl17-NNN.pdf)
            ("Daniel Oppenheim et Hélène Oppenheim-Gluckman", "Les Disparus de Daniel Mendelsohn"),                     # pl17-105-114
            ("Alain Kleinberger", "Welcome in Vienna : retour sans exil ?"),                                             # pl17-115-116
            ("Michal Gans", "Survivre ou revivre dans l'après Hurban ?"),                                               # pl17-117-124
            ("Sandra Lustig", "Revenir vivre en Allemagne après la Shoah"),                                              # pl17-125-130
            ("Hélène Oppenheim-Gluckman", "Entretien avec Jean-Claude, un Juif polonais"),                              # pl17-131-140
            ("Jean-Charles Szurek", "Le retour de Yaël Bartana en Pologne"),                                            # pl17-141-144
            ("Céline Masson", "Les changements de nom dans la France d'après-guerre"),                                  # pl17-145-148
            ("Marius Schattner", "Vu d'Israël : entre la place Tahrir et l'avenue Rothschild"),                         # pl17-149-155
            ("Philippe Velilla", "L'internationale progressiste et Israël"),                                             # pl17-159-163
            ("Philippe Velilla", "L'isolement diplomatique d'Israël"),                                                   # pl17-164-171
            ("Henri Minczeles", "Souvenirs"),                                                                            # pl17-172-174
            ("Chantal Wolezyk-Steinberg", "Ce que le jour doit à la nuit"),                                             # pl17-175-176
            ("Jean-Charles Szurek", "L'heure d'exactitude : Annette Wieviorka"),                                        # pl17-177-178
            ("Alain Medam", "Retours sans retours"),                                                                     # pl17-29-32
            ("Rabbin Yeshaya Dalsace", "Entretien"),                                                                     # pl17-33-38
            ("Philippe Zard", "De Révolution en Révélation : impasse Benny Lévy"),                                      # pl17-39-49
            ("Izio Rosenman", "Éditorial : À la recherche d'un monde perdu"),                                           # pl17-5-6
            ("Gérard Haddad", "Ben Yehouda et la renaissance de l'hébreu"),                                             # pl17-50-55
            ("Carole Ksiazenicer-Matheron", "À l'est d'Éden : nouvelles du retour et de l'oubli chez I. J. Singer"),   # pl17-56-66
            ("Fleur Kuhn", "Melnitz de Charles Lewinsky ou les revenances du roman historique"),                        # pl17-67-75
            ("George Packer", "David Grossman, l'inconsolé"),                                                            # pl17-7-25
            ("Catherine Fhima", "Trajectoires de retour ou ré-affiliation ? Edmond Fleg et André Spire"),              # pl17-76-86
            ("Martine Leibovici", "Quelques aller-retour au cœur de l'œuvre autobiographique d'Assia Djebar"),         # pl17-87-94
            ("Anny Dayan Rosenman", "Primo Levi : La Trêve, un impossible retour ?"),                                  # pl17-97-104
        ],
        "order": [16, 20, 13, 14, 15, 17, 18, 19, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    },
    18: {
        "title": "Que faisons-nous de notre histoire ?",
        "year": "2013",
        "dossier": "Histoire et mémoire",
        "articles": [
            # Order matches Python string-sort of PDF filenames (pl18-NNN.pdf)
            ("Françoise Blum et al.", "Génocides et politiques mémorielles"),                                            # pl18-109-115
            ("Ewa Maczka-Tartakowsky", "La littérature à défaut d'histoire ?"),                                         # pl18-11-21
            ("Alain Medam", "Figures en fugue"),                                                                         # pl18-119-125
            ("Berthe Burko-Falcman", "Un cheval pour pleurer"),                                                          # pl18-126-130
            ("Jean-Charles Szurek", "En lisant Ivan Jablonka"),                                                          # pl18-131-134
            ("Lucette Valensi", "Mes langues maternelles, plus d'autres"),                                               # pl18-135-142
            ("Carole Ksiazenicer-Matheron", "Traduire"),                                                                 # pl18-143-151
            ("Marc Sagnol", "Évocations de Galicie"),                                                                   # pl18-153-162
            ("Anne Geisler-Szmulewicz", "Un combattant pour la Liberté, Jacquot Szmulewicz"),                           # pl18-163-176
            ("Henri Cohen-Solal et Dominique Rividi", "Jeunes à risques"),                                              # pl18-177-183
            ("Izio Rosenman et Hélène Oppenheim-Gluckman", "Entretiens avec Élie Wajeman"),                             # pl18-184-194
            ("Claude Aziza", "Rencontres judéo-chrétiennes dans le péplum"),                                             # pl18-197-201
            ("Guido Furci", "Le livre de la grammaire intérieure au prisme du cinéma"),                                 # pl18-202-207
            ("Martine Leibovici", "Une critique radicale du sionisme à partir de l'histoire juive diasporique ?"),      # pl18-211-224
            ("Nadja Djurić", "Psaume 44 de Danilo Kiš"),                                                               # pl18-22-30
            ("Eva Illouz", "Le prix de Judith Butler"),                                                                  # pl18-225-227
            ("Philippe Velilla", "Les Juifs de France et l'élection présidentielle de 2012"),                           # pl18-231-237
            ("Chantal Wolezyk", "Le Club des incorrigibles optimistes (comptes rendus)"),                               # pl18-238-239
            ("Fleur Kuhn", "D'un Je à l'autre, les langages d'André Schwarz-Bart"),                                     # pl18-31-41
            ("Barbara Agnese", "Sur Marlene Streeruwitz"),                                                               # pl18-42-49
            ("Izio Rosenman", "Éditorial : Que faisons-nous de notre histoire ?"),                                       # pl18-5-6
            ("", "Le mythe de Massada"),                                                                                 # pl18-53-61
            ("Aryeh Barnea", "Les dangers du paradigme de Massada"),                                                    # pl18-62-63
            ("Anny Bloch-Raymond", "L'occultation de l'esclavage"),                                                     # pl18-65-69
            ("Frédéric Abecassis", "Les Juifs dans l'islam méditerranéen"),                                             # pl18-70-81
            ("Guideon Meron et Oded Chalom", "Moche Shapira"),                                                          # pl18-82-90
            ("Daniel Oppenheim", "Écrire pour transmettre l'expérience de la barbarie"),                                # pl18-91-98
            ("Alain Blum et Marta Craveri", "Passés nationaux ou histoire européenne"),                                 # pl18-99-108
        ],
        "order": [20, 1, 14, 18, 19, 21, 22, 23, 24, 25, 26, 27, 0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17],
    },
    19: {
        "title": "Intellectuels juifs – Itinéraires, engagements, écritures",
        "year": "2015",
        "dossier": "Intellectuels juifs",
        "articles": [
            # Order matches Python string-sort of PDF filenames (pl19-NNN-NNN.pdf)
            ("Pierre Pachet", "Intellectuels juifs soviétiques"),                                                  # pl19-109-110
            ("Boris Czerny", "Une identité de papier : être juif en URSS"),                                        # pl19-111-123
            ("Jean-Yves Potel", "Un intellectuel juif en Pologne — entretien avec Konstanty Gebert"),              # pl19-124-133
            ("Constance Paris de Bollardière", "La collection Dos poylishe yidntum (1946-1966)"),                  # pl19-134-139
            ("Fleur Kuhn Kennedy", "Mark Turkov et sa « communauté imaginée »"),                                   # pl19-140-150
            ("Charles Malamud", "Pierre Vidal-Naquet"),                                                            # pl19-15-16
            ("Dominique Bourel", "Martin Buber et la politique"),                                                   # pl19-151-156
            ("Denis Charbit", "Avraham B. Yehoshua — un penseur sur la corde raide"),                             # pl19-157-166
            ("Philippe Zard", "Meddeb le sage : l'honneur d'un intellectuel"),                                     # pl19-169-179
            ("Richard Marienstras", "Moïse et l'Égyptien"),                                                        # pl19-17-19
            ("Daniella Pinkstein", "Le temps des miens — de Moriah à Budapest"),                                   # pl19-180-187
            ("Philippe Velilla", "En attendant Marine Le Pen"),                                                    # pl19-188-193
            ("Rachel Ertel", "Khurbn : l'homme chaos"),                                                            # pl19-194-197
            ("Marie-Brunette Spire", "André Spire (1868-1966)"),                                                   # pl19-20-24
            ("Antoine Coppolani", "Albert Cohen et la Revue Juive"),                                               # pl19-25-34
            ("Sandrine Szwarc", "Les colloques des intellectuels juifs"),                                          # pl19-35-41
            ("Héloïse Hermant", "Refus des Lumières : les penseurs du retour"),                                    # pl19-42-51
            ("Izio Rosenman", "Éditorial — Intellectuels juifs"),                                                  # pl19-5-6
            ("Jean-Claude Poizat", "Les intellectuels juifs français contemporains et l'ambivalence"),             # pl19-52-64
            ("Jean-Charles Szurek", "Enzo Traverso et Alain Finkielkraut, intellectuels nostalgiques"),            # pl19-65-71
            ("Izio Rosenman", "Rabi, un intellectuel juif engagé"),                                                # pl19-7-14
            ("Carole Matheron", "Abe Cahan (1860-1951) : un intellectuel juif dans le melting-pot américain"),     # pl19-72-79
            ("Martine Leibovici", "Hannah Arendt, ni Juive d'exception, ni femme d'exception"),                    # pl19-80-90
            ("Daniel Oppenheim", "L'expérience de la barbarie par l'intellectuel et l'éthique du témoignage selon Jean Améry"),  # pl19-91-97
            ("Michaël Löwy", "De quelques intellectuels juifs radicaux aux USA et en Europe"),                     # pl19-98-108
        ],
        "order": [17, 20, 5, 9, 13, 14, 15, 16, 18, 19, 21, 22, 23, 24, 0, 1, 2, 3, 4, 6, 7, 8, 10, 11, 12],
    },
    20: {
        "title": "Dialogue",
        "year": "2016",
        "dossier": "Dialogue des religions et des cultures",
        "articles": [
            # Order matches Python string-sort of PDF filenames (pl20-NNN.pdf)
            ("Rahel Wasserfall", "Le CEDAR – une méthodologie pour un vécu dans la différence"),                         # pl20-105-117
            ("Martine Leibovici", "Philosophie et révélation biblique selon Leo Strauss : un dialogue limité"),          # pl20-11-22
            ("Daniel Oppenheim", "Dialoguer avec les adolescents au sujet du terrorisme"),                               # pl20-118-124
            ("Brigitte Stora et Philippe Zard", "Le sujet qui fâche (entretien)"),                                      # pl20-125-133
            ("Gérard Haddad", "Les critères du dialogue et leur application à la psychanalyse"),                         # pl20-134-138
            ("Hélène Oppenheim-Gluckman", "Dialogue entre cinq générations"),                                            # pl20-139-144
            ("Philippe Velilla", "Menaces contre la démocratie israélienne"),                                            # pl20-145-150
            ("Anny Dayan Rosenman", "Laurent Munnich (entretien) : Akadem"),                                             # pl20-23-31
            ("Joël Hubrecht", "Après un crime de masse, comment la justice peut-elle relancer le dialogue ?"),           # pl20-32-41
            ("Cécile Rousselet", "Dialogue entre bourreau et victime dans Vie et destin de Vassili Grossman"),          # pl20-42-56
            ("Izio Rosenman", "Éditorial : Dialogue"),                                                                   # pl20-5-6
            ("Hélène Oppenheim-Gluckman", "Grand-père n'était pas un nazi"),                                            # pl20-57-59
            ("Monique Halpern et Jean-Charles Szurek", "Un étrange dialogue"),                                           # pl20-60-62
            ("Fleur Kuhn-Kennedy", "« Écoute, mon ami, ce qui se passe ici »"),                                         # pl20-63-70
            ("Franklin Rausky", "Le dialogue judéo-chrétien. Une mutation révolutionnaire"),                             # pl20-7-10
            ("Anny Dayan Rosenman", "Répondre à la puissante voix des morts. Le dialogue dans l'œuvre d'Elie Wiesel"), # pl20-71-82
            ("Guido Furci et Fleur Kuhn-Kennedy", "Dialogues en résistance dans See You Soon Again"),                   # pl20-83-89
            ("Daniel Oppenheim", "Construire et habiter l'espace du dialogue et de l'hospitalité"),                     # pl20-90-97
            ("Julien Cann", "Givat Haviva, un lieu de dialogue"),                                                        # pl20-98-104
        ],
        "order": [10, 14, 1, 7, 8, 9, 11, 12, 13, 15, 16, 17, 18, 0, 2, 3, 4, 5, 6],
    },
    21: {
        "title": "La peur, hier et aujourd'hui",
        "year": "2018",
        "dossier": "La peur",
        "articles": [
            # Order matches Python string-sort of PDF filenames (pl21-NNN.pdf)
            ("Guila Clara Kessous", "Qui a peur du Grand méchant Dieu ?"),                                              # pl21-101-111
            ("Russell Jacoby", "Peur et violence"),                                                                      # pl21-11-18
            ("Yaël Pachet", "Mon père n'avait pas peur d'être juif"),                                                   # pl21-112-115
            ("Philippe Velilla", "Contrainte religieuse et contrainte politique en Israël"),                             # pl21-116-124
            ("Gilberte Finkel", "Kaléidoscope"),                                                                         # pl21-125-132
            ("Sylvie Halpern", "Talmud à la sauce sud-coréenne"),                                                       # pl21-133-136
            ("Martine Leibovici", "Peur et sentiment d'invulnérabilité dans Masse et puissance d'Elias Canetti"),       # pl21-19-34
            ("Delphine Horvilleur", "La peur dans la tradition juive"),                                                  # pl21-35-47
            ("Hélène Oppenheim-Gluckman", "Trauma et destructivité ?"),                                                 # pl21-48-55
            ("Daniel Oppenheim", "Peurs et terreurs. Leurs causes et leurs conséquences"),                              # pl21-56-65
            ("Brigitte Stora", "Même pas peur !"),                                                                       # pl21-66-71
            ("Izio Rosenman", "Éditorial"),                                                                              # pl21-7-10
            ("Jean-Charles Szurek", "Le retour de la peur en Pologne"),                                                 # pl21-72-76
            ("Lydie Decobert", "Les ressorts de la peur dans le cinéma d'Alfred Hitchcock"),                            # pl21-77-90
            ("Guido Furci", "La peur dans Badenheim 1939 d'Aharon Appelfeld"),                                          # pl21-91-100
        ],
        "order": [11, 1, 6, 7, 8, 9, 10, 12, 13, 14, 0, 2, 3, 4, 5],
    },
    22: {
        "title": "Le Juif et l'Autre",
        "year": "2020",
        "dossier": "Le Juif et l'Autre",
        "articles": [
            # Order matches Python string-sort of PDF filenames (pl22-NNN.pdf)
            ("Francine Kaufmann", "L'Autre dans la vie et l'œuvre d'André Schwarz-Bart"),                               # pl22-105-116
            ("Guido Furci", "Retour sur Philip Roth : « Eli le fanatique » et son autre"),                              # pl22-117-129
            ("François Ardeven", "Blaise Pascal rencontre les Juifs"),                                                   # pl22-130-138
            ("Gérard Haddad", "Lacan et « ses » Juifs"),                                                                # pl22-139-147
            ("Simon Wuhl", "Les foyers de la haine antisémite en France"),                                               # pl22-148-181
            ("Danny Trom", "L'État-gardien, État de l'Autre"),                                                          # pl22-15-21
            ("Daniel Oppenheim", "Le regard sur les hommes et sur le monde d'Isaac Babel"),                             # pl22-182-188
            ("François Rachline", "Juif, ou l'autre en soi"),                                                           # pl22-22-27
            ("Emmanuel Levinas", "Le judaïsme et l'Autre (extrait de Difficile Liberté)"),                              # pl22-28-29
            ("Brigitte Stora", "L'antisémitisme et le refus de l'Autre"),                                               # pl22-30-39
            ("Izio Rosenman", "Éditorial : L'Autre devant nous et l'Autre en nous"),                                    # pl22-4-7
            ("Gérard Israël", "René Cassin, l'homme des droits de l'Homme"),                                            # pl22-40-42
            ("Nadine Vasseur", "Les nôtres et les autres"),                                                              # pl22-43-48
            ("Yann Boissière", "Se reconnaître dans l'Autre : devenir rabbin"),                                         # pl22-49-56
            ("Martine Leibovici", "Entre autres. Quelques déclinaisons juives de la relation insider/outsider"),         # pl22-57-72
            ("Michèle Tauber", "L'« autre » dans la littérature israélienne moderne"),                                  # pl22-73-86
            ("Mireille Hadas-Lebel", "Les juifs dans le monde hellénistique romain"),                                   # pl22-8-14
            ("Philippe Zard", "Anatomie d'un embarras. En lisant la poésie politique de Mahmoud Darwich"),              # pl22-87-104
        ],
        "order": [10, 16, 5, 7, 8, 9, 11, 12, 13, 14, 15, 17, 0, 1, 2, 3, 4, 6],
    },
    23: {
        "title": "Les Juifs dans la modernité",
        "year": "2022",
        "dossier": "Les Juifs dans la modernité / Avrom Sutzkever, poète yiddish",
        "articles": [],  # Will be populated from PDFs
    },
    24: {
        "title": "Juif visible / Juif invisible",
        "year": "2024",
        "dossier": "Juif visible / Juif invisible",
        "articles": [
            ("Izio Rosenman", "Éditorial"),
            ("Livia Parnes", "Le sens (impré)visible de l'invisible : le cas du marranisme portugais"),
            ("Chantal Meyer-Plantureux", "Le Juif au théâtre au XIXe s. La Belle époque de l'antisémitisme"),
            ("Sylvie Lindeperg", "Vie et destin des « images de la Shoah »"),
            ("Paul Salmona", "Invisibilité des Juifs dans l'histoire de France"),
            ("Lola Lafon", "L'ineffaçable. Sur l'invisibilisation d'Anne Frank. Entretien avec Brigitte Stora"),
            ("Evelyn Torton Beck", "La politique d'invisibilisation des femmes juives dans le féminisme américain"),
            ("Emmanuel Levine", "Levinas et les formes de l'invisibilité juive"),
            ("Rivon Krygier", "Visibilités juives : entretien avec Philippe Zard"),
            ("Léa Veinstein", "Un regard sans paupière. L'invisibilité chez Kafka"),
            ("Cécile Rousselet", "L'invisibilité de l'esclave et du Juif chez André Schwarz-Bart"),
            ("Anny Dayan Rosenman", "Judéités gariennes"),
            ("Itzhak Goldberg", "On n'y voit rien – L'invisible abstrait : Kandinsky et les autres"),
            ("Céline Masson", "Retrouver le nom caché"),
            ("Nadine Vasseur", "Changement de nom"),
            ("Carole Ksiazenicer-Matheron", "Un questionnaire au temps de Vichy. Juifs visibles, juifs invisibles : une histoire de famille"),
            ("Jean-Charles Szurek", "Romuald Jakub Weksler-Waszkinel"),
            ("Simon Wuhl", "Universalisme juif et singularité"),
            ("Philippe Vellila", "Israël en crise"),
        ],
        # Sections from official sommaire: (header or None, slice indices)
        "sections": [
            (None,                      (0, 1)),   # Éditorial
            ("Histoire",                (1, 6)),   # Parnes, Meyer-Plantureux, Lindeperg, Salmona, Lafon
            ("Philosophie et actualité",(6, 9)),   # Beck, Levine, Krygier
            ("Littérature et art",      (9, 13)),  # Veinstein, Rousselet, Dayan Rosenman, Goldberg
            ("Témoignages",             (13, 17)), # Masson, Vasseur, Ksiazenicer-Matheron, Szurek
            ("Hors dossier",            (17, 19)), # Wuhl, Vellila
        ],
    },
}

# ─── PDF Issue file mapping ────────────────────────────────────────────────────
PDF_FILES = {
    6: PDF_ISSUES / "PL6.PDF",
    7: PDF_ISSUES / "PL7.PDF",
    8: PDF_ISSUES / "PL8.PDF",
    9: PDF_ISSUES / "PL9.PDF",
    10: PDF_ISSUES / "PL10.PDF",
    11: PDF_ISSUES / "PL11.PDF",
    13: PDF_ISSUES / "PL13.PDF",
    14: PDF_ISSUES / "PL14 +Couv.PDF",
    15: PDF_ISSUES / "PL15.PDF",
    16: PDF_ISSUES / "PL16.PDF",
    17: PDF_ISSUES / "PL17.PDF",
    18: PDF_ISSUES / "PL18 +Couv.pdf",
    19: PDF_ISSUES / "PL19.PDF",
    20: PDF_ISSUES / "PL20.PDF",
    21: PDF_ISSUES / "PL21  avec couv.pdf",
    22: PDF_ISSUES / "PL22.PDF",
    23: PDF_ISSUES / "PL23 avec couv.PDF",
    24: SOURCE_BASE / "PLURIELLES24.pdf",
}

# ─── Extract text from PDF ─────────────────────────────────────────────────────
def extract_pdf_text(pdf_path, fix_char_spacing=False, clip_bottom=0.86):
    """Extract clean text from a PDF, clipping away headers and footers.

    fix_char_spacing: only enable for older PDFs (issues 9, 10, 12, 22) where
    each letter was typeset as a separate text object, e.g. "i n c a r n e".
    The regex is restricted to runs of SINGLE letters to avoid merging normal
    short French words like "et le XXe siècle" into "etleXXesiècle".

    clip_bottom: fraction of page height to clip at bottom (default 0.86).
    Use 0.92 for issues 12, 16, 22 whose content reaches closer to the footer.
    """
    _LIGATURES = str.maketrans({
        '\ufb00': 'ff', '\ufb01': 'fi', '\ufb02': 'fl',
        '\ufb03': 'ffi', '\ufb04': 'ffl', '\ufb05': 'st', '\ufb06': 'st',
    })
    # C0 control characters \x00-\x04 must be stripped from raw PDF text:
    # PDFs with broken font encoding sometimes produce these as garbage; they would
    # conflict with our inline-marker bytes (\x01\x02 = footnote, \x03\x04 = italic).
    _STRIP_CTRL = str.maketrans({i: None for i in range(0x05)})

    try:
        doc = fitz.open(str(pdf_path))
        pages = []
        for page in doc:
            ph = page.rect.height
            pw = page.rect.width
            # Clip away the top 11% (running headers) and bottom (footers/page numbers)
            clip = fitz.Rect(0, ph * 0.11, pw, ph * clip_bottom)

            if fix_char_spacing:
                # Older PDFs (issues 9, 10, 12, 22): italic font metadata unreliable;
                # use plain text mode so the char-spacing collapse regex works cleanly.
                text = page.get_text("text", clip=clip)
                text = text.translate(_LIGATURES).translate(_STRIP_CTRL)
                # Fix soft hyphenation: word- + newline + lowercase → join
                text = re.sub(r'-\n([a-zàâäéèêëîïôùûüœ])', r'\1', text)
                # Collapse runs of single letters separated by spaces into one word.
                # Only matches single-char groups (not 2-3 char tokens) to avoid
                # accidentally joining distinct short words like "et le XXe".
                # Requires ≥ 5 consecutive single letters to trigger (avoids false positives).
                text = re.sub(
                    r'(?<!\S)([A-Za-zÀ-ÿ])( [A-Za-zÀ-ÿ]){4,}',
                    lambda m: m.group(0).replace(' ', ''),
                    text
                )
            else:
                # Modern PDFs: use dict mode to get span-level font info so italic
                # spans (book titles etc.) can be wrapped in \x03...\x04 markers,
                # which are later converted to <em>...</em> in the HTML output.
                page_dict = page.get_text("dict", clip=clip)
                span_parts = []
                for block in page_dict.get("blocks", []):
                    if block.get("type") != 0:   # skip image blocks
                        continue
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            # translate(_STRIP_CTRL) removes \x00-\x04 garbage chars
                            # that some PDFs with broken font encoding produce —
                            # they would otherwise conflict with our marker bytes.
                            s = span.get("text", "").translate(_LIGATURES).translate(_STRIP_CTRL)
                            flags = span.get("flags", 0)
                            font  = span.get("font", "")
                            is_italic = bool(flags & 2) or \
                                        "Italic" in font or "Oblique" in font
                            # Don't wrap standalone 1-2 digit spans: these are
                            # almost certainly footnote-reference superscripts
                            # (or page numbers) typeset in an oblique/italic cut.
                            # Wrapping them would produce \x03N\x04 which blocks
                            # the _INLINE_REF lookbehind and breaks ref detection.
                            if is_italic and s.strip() and \
                                    not re.match(r'^\d{1,2}$', s.strip()):
                                s = f'\x03{s}\x04'
                            span_parts.append(s)
                        span_parts.append('\n')   # newline at end of every line
                text = ''.join(span_parts)
                # Fix soft hyphenation across spans.
                # Case 1: both sides same italic state → works normally.
                # Case 2: continuation starts with \x03 → handle separately.
                text = re.sub(r'-\n\x03([a-zàâäéèêëîïôùûüœ])',
                              lambda m: '\x03' + m.group(1), text)
                text = re.sub(r'-\n([a-zàâäéèêëîïôùûüœ])', r'\1', text)

            pages.append(text)
        doc.close()
        return pages
    except Exception as e:
        print(f"  Error reading {pdf_path}: {e}")
        return []


def extract_docx_text(docx_path):
    """Extract paragraph texts and footnotes from a DOCX file.

    Returns (paras, footnotes_dict) where:
      paras: list of paragraph strings; body paragraphs contain \\x01N\\x02
        markers at the positions of footnote references.
      footnotes_dict: {int -> str} mapping footnote number to footnote text,
        read from word/footnotes.xml.  Empty dict if no footnotes.xml found.
    """
    _W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    try:
        with zipfile.ZipFile(str(docx_path)) as z:
            with z.open('word/document.xml') as f:
                doc_tree = ET.parse(f)

            # ── Read footnotes.xml with italic detection ─────────────────────
            footnote_texts = {}
            if 'word/footnotes.xml' in z.namelist():
                with z.open('word/footnotes.xml') as f:
                    fn_tree = ET.parse(f)
                for fn in fn_tree.findall(f'.//{{{_W}}}footnote'):
                    fn_type = fn.get(f'{{{_W}}}type', '')
                    if fn_type in ('separator', 'continuationSeparator', 'continuationNotice'):
                        continue
                    fn_id_str = fn.get(f'{{{_W}}}id', '')
                    try:
                        fn_id = int(fn_id_str)
                    except ValueError:
                        continue
                    if fn_id <= 0:
                        continue
                    # Iterate by runs to preserve italic spans
                    fn_parts = []
                    for r in fn.findall(f'.//{{{_W}}}r'):
                        rpr = r.find(f'{{{_W}}}rPr')
                        is_italic = False
                        if rpr is not None:
                            i_tag = rpr.find(f'{{{_W}}}i')
                            if i_tag is not None:
                                val = i_tag.get(f'{{{_W}}}val', 'true')
                                is_italic = val not in ('0', 'false')
                        run_text = ''.join(
                            child.text or '' for child in r
                            if child.tag == f'{{{_W}}}t'
                        ).replace('\x03', '').replace('\x04', '')  # strip conflict chars
                        if is_italic and run_text.strip():
                            run_text = f'\x03{run_text}\x04'
                        fn_parts.append(run_text)
                    text = ''.join(fn_parts).strip()
                    if text:
                        footnote_texts[fn_id] = text

        # ── Read body paragraphs, inserting \x01N\x02 at fn-ref positions ───
        # Iterate by runs (w:r) so we can detect italic spans via w:rPr/w:i.
        paras = []
        for p in doc_tree.findall(f'.//{{{_W}}}p'):
            parts = []
            for r in p.findall(f'.//{{{_W}}}r'):
                rpr = r.find(f'{{{_W}}}rPr')
                is_italic = False
                if rpr is not None:
                    i_tag = rpr.find(f'{{{_W}}}i')
                    if i_tag is not None:
                        val = i_tag.get(f'{{{_W}}}val', 'true')
                        is_italic = val not in ('0', 'false')
                run_parts = []
                for child in r:
                    if child.tag == f'{{{_W}}}t':
                        run_parts.append(child.text or '')
                    elif child.tag == f'{{{_W}}}footnoteReference':
                        fn_id_str = child.get(f'{{{_W}}}id', '')
                        try:
                            fn_id = int(fn_id_str)
                            if fn_id > 0:
                                run_parts.append(f'\x01{fn_id}\x02')
                        except ValueError:
                            pass
                run_text = ''.join(run_parts).replace('\x03', '').replace('\x04', '')
                # Only wrap in italic markers if there is actual visible text
                # (don't wrap footnote-marker-only runs)
                visible = re.sub(r'\x01\d+\x02', '', run_text).strip()
                if is_italic and visible:
                    run_text = f'\x03{run_text}\x04'
                parts.append(run_text)
            paras.append(''.join(parts))

        return paras, footnote_texts

    except Exception as e:
        print(f"  Error reading {docx_path}: {e}")
        return [], {}


def docx_paras_to_html(raw_paras, title="", author="", footnotes=None):
    """Convert DOCX paragraph list to HTML, filtering boilerplate.

    footnotes: pre-extracted {int->str} dict from extract_docx_text.  When
    provided, the pipeline uses this dict directly (bypassing detect_footnotes)
    so DOCX markers (\\x01N\\x02) are rendered as inline <sup> links without
    mis-parsing body text as footnote text.
    """
    # Pattern for editorial annotations like "(+anny)", "(-david)", "(ADR)" etc.
    # These are reviewer/editor notes sometimes left in DOCX files.
    _EDITORIAL_ANNOT = re.compile(r'^\([+\-]?\w{1,20}\)$')

    paragraphs = []
    for p in raw_paras:
        s = p.strip()
        if not s:
            continue
        # Skip very short lines (page numbers etc.) but keep paragraphs that
        # contain footnote markers even if otherwise short.
        if len(s) < 4 and not _FN_TOK.search(s):
            continue
        # Skip editorial annotation paragraphs (e.g. "(+anny)", "(ADR)")
        if _EDITORIAL_ANNOT.match(s):
            continue
        paragraphs.append(s)
    paragraphs = strip_article_header(paragraphs, title, author)
    return paragraphs_to_html(paragraphs, prebuilt_footnotes=footnotes)


def strip_article_header(paragraphs, title, author):
    """Remove title/author prefix from the start of extracted article body.

    PDF extraction often captures the article title and author name at the
    top of the first page; text_to_paragraphs() then joins them with the
    first sentence into paragraph 0.  DOCX files may have them as separate
    leading paragraphs.

    Strategy:
      1. DOCX style – skip leading paragraphs that match the title or author.
      2. PDF style – find the author name inside paragraph 0-2 (within the
         first 200 chars) and strip everything up to and including it.
    """
    if not paragraphs:
        return paragraphs

    # Build lowercase search tokens from author and title
    author_tokens = []
    if author and author.strip():
        a = author.strip()
        author_tokens.append(a.lower())
        parts = a.split()
        if len(parts) > 1:
            author_tokens.append(parts[-1].lower())   # last name alone

    title_tokens = []
    if title and title.strip():
        t = title.strip()
        # Add first 40 chars of the full title as primary token
        prefix = t[:40].lower()
        if len(prefix) > 10:
            title_tokens.append(prefix)
        # Also add each ' — '- or ' : '-separated part as its own token, so that
        # multi-line DOCX titles (split by em-dash or French colon) are stripped.
        # E.g. "…invisible : le cas du marranisme" → "le cas du marranisme" token.
        seen_parts = set(title_tokens)
        for sep in (' — ', ' : '):
            for part in t.split(sep):
                part_lower = part.strip().lower()
                tok = part_lower[:40]
                if len(part_lower) > 10 and tok not in seen_parts:
                    title_tokens.append(tok)
                    seen_parts.add(tok)

    all_tokens = author_tokens + title_tokens

    def _norm(s):
        """Normalize whitespace/quote variants and strip formatting markers for comparison."""
        # Whitespace variants → ASCII space
        s = s.replace('\xa0', ' ').replace('\u202f', ' ').replace('\u2009', ' ')
        # Curly/smart apostrophes/quotes → ASCII equivalents
        s = s.replace('\u2019', "'").replace('\u2018', "'")
        s = s.replace('\u201c', '"').replace('\u201d', '"')
        # Strip inline footnote markers (\x01N\x02) and italic markers (\x03, \x04)
        s = re.sub(r'\x01\d+\x02', '', s)
        s = s.replace('\x03', '').replace('\x04', '')
        return s

    # Leading prefixes that indicate "author byline" in DOCX (e.g. "Par Auteur", "Entretien avec Auteur")
    _BYLINE_PREFIXES = ('par ', 'entretien avec ', 'by ', 'propos recueillis par ')

    def _matches_any_token(p_lower):
        """Return True if p_lower (already _norm'd) matches any title/author token.

        A match means the paragraph IS the title/author, not merely a sentence
        that starts with the author's name.  The startswith check is therefore
        guarded by a length constraint: the paragraph must not be much longer
        than the token itself (otherwise it is article content, not a header).
        """
        for tok in all_tokens:
            if not tok:
                continue
            tok_n = _norm(tok)
            tok_len = len(tok_n)
            # 1. Exact match
            if p_lower == tok_n:
                return True
            # 2. Para starts with the token — but only if para is short enough
            #    (guards against "Author wrote something interesting…" false positive)
            if p_lower.startswith(tok_n[:30]) and len(p_lower) <= tok_len + 25:
                return True
            # 3. Token starts with the para — para is a short fragment of the title
            if len(p_lower) >= 10 and tok_n.startswith(p_lower[:30]):
                return True
            # Try stripping leading byline prefix ("par auteur" → "auteur")
            stripped = p_lower
            for pfx in _BYLINE_PREFIXES:
                if stripped.startswith(pfx):
                    stripped = stripped[len(pfx):]
                    break
            if stripped != p_lower:
                if (stripped == tok_n
                        or (stripped.startswith(tok_n[:30]) and len(stripped) <= tok_len + 25)
                        or (len(stripped) >= 10 and tok_n.startswith(stripped[:30]))):
                    return True
        return False

    def _docx_strip(paras, max_scan=6):
        """Strip leading paras that are title/author tokens. Returns (n_stripped, remaining)."""
        j = 0
        while j < min(max_scan, len(paras)):
            p_lower = _norm(paras[j].strip().lower())
            if _matches_any_token(p_lower):
                j += 1
            else:
                break
        return j, paras[j:]

    # --- DOCX style: strip leading paragraphs that ARE the title / author ---
    n, paragraphs = _docx_strip(paragraphs, max_scan=6)
    if n > 0:
        # One more pass to catch any further header lines exposed after first strip
        _, paragraphs = _docx_strip(paragraphs, max_scan=3)
        return paragraphs

    # --- PDF style: author name embedded early in paragraph 0-2 ---
    for i, para in enumerate(paragraphs[:3]):
        para_lower = _norm(para.lower())
        for token in author_tokens:
            if len(token) < 4:
                continue
            pos = para_lower.find(_norm(token))
            if pos < 0 or pos > 200:
                # Not found, or found deep in text (not a header)
                continue
            after = para[pos + len(token):].lstrip(' ,.:;—–-\n')
            result = []
            if len(after) > 25:
                result.append(after)
            result.extend(paragraphs[i + 1:])
            result = result if result else paragraphs[i + 1:]
            # One DOCX-style cleanup pass on the result
            _, result = _docx_strip(result, max_scan=3)
            return result

    return paragraphs


def text_to_paragraphs(text):
    """Convert raw extracted text to clean paragraphs.

    Strategy: blank lines are paragraph breaks; single-newline-wrapped lines
    within a paragraph are joined. Short lines that are part of a split word
    or incomplete sentence are merged with the next line.
    """
    # Normalise line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Split into raw lines
    lines = text.split('\n')

    paragraphs = []
    current_words = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            # Blank line → end of paragraph only if the current text actually
            # ends a sentence. Otherwise it's a page-break mid-sentence: skip it.
            if current_words:
                last_word = current_words[-1].rstrip()
                if last_word and last_word[-1] in '.!?»"\'':
                    paragraphs.append(' '.join(current_words))
                    current_words = []
            continue

        # 2-4 digit isolated numbers are page numbers → skip
        if re.match(r'^\d{2,4}$', stripped):
            continue
        # Single isolated digit (1-9): potential footnote marker → preserve as token
        if re.match(r'^\d$', stripped):
            current_words.append(f'\x01{stripped}\x02')
            continue
        # Skip running header fragments (journal name + issue number anywhere in line)
        if re.search(r'Plurielles\s+(n[°o]?\s*\d|num[eé]ro)', stripped, re.I):
            continue
        # Skip lines that are just a dossier title + page number (e.g. "Les Juifs dans la modernité 15")
        if re.match(r'^[A-ZÀ-Ü].{10,60}\s\d{1,3}$', stripped) and len(stripped) < 80:
            # Only if it looks like a header (short, ends with page number, title case)
            words = stripped.split()
            if len(words) <= 8 and words[-1].isdigit():
                continue

        # Decide whether this line starts a new paragraph:
        # A new paragraph starts when the PREVIOUS line ended with sentence-ending
        # punctuation AND the current line starts with a capital or special char.
        # Skip over footnote tokens to find the actual last meaningful word.
        # stripped_lead strips a leading italic-start marker (\x03) so that a
        # line beginning with an italic span is still seen as starting with its
        # first real character for the uppercase check.
        stripped_lead = stripped[1:] if stripped and stripped[0] == '\x03' else stripped
        starts_new = False
        if current_words:
            actual_last = ''
            for w in reversed(current_words):
                if not (w.startswith('\x01') and w.endswith('\x02')):
                    actual_last = w
                    break
            if actual_last and actual_last[-1] in '.!?:':
                if stripped_lead and (stripped_lead[0].isupper() or
                                      re.match(r'^[A-ZÀ-Ö]\.?\s', stripped_lead)):
                    starts_new = True

        if starts_new:
            if current_words:
                paragraphs.append(' '.join(current_words))
                current_words = []

        current_words.append(stripped)

    if current_words:
        paragraphs.append(' '.join(current_words))

    # Remove very short spurious paragraphs (footnote artefacts, isolated chars)
    paragraphs = [p for p in paragraphs if len(p) > 15]
    return paragraphs


# ── Footnote token regex (matches \x01N\x02 markers inserted by text_to_paragraphs)
_FN_TOK = re.compile(r'\x01(\d{1,2})\x02')

# ── Inline footnote ref regex ────────────────────────────────────────────────
# Matches 1- or 2-digit number directly attached to a word character, closing
# punctuation, guillemet, quote, or NBSP — followed by whitespace / punct / end.
# Used in render_para to detect superscript references in extracted PDF text.
_INLINE_REF = re.compile(
    # lookbehind: must follow a letter, French letter, guillemet, quote, bracket,
    # NBSP, italic-start \x03 or italic-end \x04 markers.
    # \x04: catches "word\x04N" (ref digit right after italic span closes).
    # \x03: catches "\x03N" (ref digit at start of its own italic span).
    r'(?<=[a-zA-ZàâäéèêëîïôùûüœÀ-ÿ»\xbb\xab\"\'\)\]\xa0\x03\x04])'
    # group 1: 1 or 2 digit footnote number (directly attached to preceding char)
    r'([1-9][0-9]?)'
    r'(?=[\s\u00a0,;:.!?»\'\"\)\]\n]|$)'
)

# Separate pattern for "word.N" style refs (period between word and footnote number).
# Uses a 2-character lookbehind so that single-letter abbreviations like "p.", "n."
# do NOT match (preventing false positives for page references like "p.1", "p.2").
# Example: "renouvellement.2" → matches; "p.2" → does NOT match.
_INLINE_REF_PERIOD = re.compile(
    r'(?<=[a-zA-ZàâäéèêëîïôùûüœÀ-ÿ\xa0][a-zA-ZàâäéèêëîïôùûüœÀ-ÿ\xa0])'
    r'\.([1-9][0-9]?)'
    r'(?=[\s\u00a0,;:.!?»\'\"\)\]\n]|$)'
)

# Footnote number prefix at start of string.
# Two alternatives:
#   "N." (with dot) + optional whitespace + any non-whitespace char — allows
#     URLs and lowercase text (used in DOCX-sourced footnotes like "1. https://...")
#   "N " (no dot) + 1-3 spaces + uppercase or opening punct — PDF style, requires
#     uppercase to avoid false positives like "3 mois plus tard".
_FN_NUM_PREFIX = re.compile(
    r'^(\d{1,2})'
    r'(?:'
    r'\.\s*(?=\S)'                   # "N." followed by any non-whitespace
    r'|'
    r'\s{1,3}(?=[A-ZÀ-Û«\"\'\(\[])' # "N " followed by uppercase / opening punct
    r'|'
    r'(?=[A-ZÀ-Û][a-záàâäéèêëîïôùûüœ.,])'  # "NW.Benjamin" compact (uppercase+lowercase/punct)
    r')'
)

# A paragraph IS a footnote block if it starts with a footnote number prefix
# and is at least 10 chars (to avoid matching isolated page numbers or short artefacts)
def _is_fn_para(para):
    return bool(_FN_NUM_PREFIX.match(para)) and len(para) >= 10

# A "NOTES" header line — strip it, don't emit to body
_NOTES_HEADER = re.compile(r'^NOTES?\s*$', re.I)

# Split a multi-footnote block into individual footnotes.
# Mirrors _FN_NUM_PREFIX: split after sentence-ending punct before a footnote-number.
_FN_SPLIT = re.compile(
    r'(?<=[.!?»\'\"\)\]])\s+'
    r'(?=\d{1,2}(?:\.\s*\S|\s{1,3}[A-ZÀ-Û«\"\'\(\[]|[A-ZÀ-Û][a-záàâäéèêëîïôùûüœ.,]))'
)

# Pattern to detect body-text continuation accidentally merged into the last footnote.
# Sentence-ending punct + whitespace + digit + space + lowercase word:
# e.g. "...p. 118). 40 dizaines de millions de fidèles…" where "40 dizaines…"
# is body text that continued after the footnote column in the PDF.
# This pattern does NOT match footnote-start prefixes (those require uppercase
# or a dot, handled by _FN_SPLIT / _FN_NUM_PREFIX).
_FN_BODY_OVERFLOW = re.compile(
    r'(?<=[.!?»\'\"\)\]])\s+(?=\d{1,3}\s+[a-záàâäéèêëîïôùûüœ])'
)


def _split_fn_block(text):
    """Parse a string of one or more footnotes into ({num: text}, overflow) tuple.

    overflow is any trailing text that looks like body prose accidentally merged
    into the last footnote (e.g., body-column continuation after a footnote
    that ends with a page number rather than a sentence-ending period).
    Callers should append overflow back to the body paragraph list.
    """
    parts = _FN_SPLIT.split(text)
    result = {}
    for part in parts:
        part = part.strip()
        m = _FN_NUM_PREFIX.match(part)
        if m:
            num = int(m.group(1))
            content = part[m.end():].strip()
            if content:
                result[num] = content

    # Detect body-text overflow in the last footnote's content.
    # If sentence-end is followed by a number + lowercase word, the text
    # after that boundary was likely body prose, not footnote text.
    overflow = ''
    if result:
        last_num = max(result.keys())
        content = result[last_num]
        m_ov = _FN_BODY_OVERFLOW.search(content)
        if m_ov:
            overflow_text = content[m_ov.end():].strip()
            if len(overflow_text) > 50:
                # Keep only the text up to (but not including) the overflow space
                result[last_num] = content[:m_ov.start()].strip()
                overflow = overflow_text

    return result, overflow

# Inline footnote ref in body text: word/punct followed by a superscript-style digit.
# Matches: "word1" "»1" "pays1." "texte1," etc.
# Limited to digits 1-9 only (two-digit inline refs are rare and risky to auto-detect).
_FN_REF = re.compile(
    r'(?<=[a-zA-ZàâäéèêëîïôùûüœÀ-ÿ»\"\'\)\]])([1-9])'
    r'(?=[\s,;.!?»\'\")\]\n]|$)'
)

# Case C split pattern: body text with footnote appended after sentence-ending punct.
# Mirrors _FN_NUM_PREFIX alternatives.
# NOTE: \s+ (not \s*) — we require at least one space before the footnote number to
# avoid falsely matching inline refs like "mot.2 Phrase suivante" where the period is
# part of the word and there is no typographic space before the superscript digit.
_FN_CASE_C = re.compile(
    r'(?<=[.!?»\'\"\)\]])\s+'
    r'(\d{1,2})'
    r'(?:\.\s*(?=\S)|\s{1,3}(?=[A-ZÀ-Û«\"\'\(\[])|(?=[A-ZÀ-Û][a-záàâäéèêëîïôùûüœ.,]))'
)


def detect_footnotes(paragraphs):
    """
    Scan paragraphs for footnote text and inline reference markers.

    Strategy:
      1. Strip any "NOTES" header paragraphs.
      2. Paragraphs that begin with "N." or "N " (footnote number prefix) are
         footnote blocks — extract them into footnotes dict.
      3. Paragraphs containing body text that ends with an inline ref digit
         (e.g. "…word1") have the ref extracted and replaced with a \x01N\x02 token.
      4. Paragraphs that contain \x01N\x02 tokens (isolated digit lines) are
         split: the token marks the boundary between body and footnote text if
         what follows starts with an uppercase letter.
      5. Multi-footnote blocks (several footnotes in one paragraph) are split
         by _split_fn_block().

    Footnotes that reset to 1 on each page (per-page numbering) are handled by
    renumbering: if footnote number N already exists in the dict with different
    text, we assign a new sequential number (continuing from the last used).

    Returns (body_paragraphs, footnotes_dict) where body paragraphs still contain
    \x01N\x02 tokens at inline-ref positions, and footnotes_dict maps int→str.
    """
    body = []
    footnotes = {}         # final merged dict: sequential int → text
    _next_fn = [0]         # mutable counter for renumbering per-page footnotes

    def _add_footnotes(new_fns):
        """Merge new_fns into footnotes, renumbering on collision."""
        for num, text in sorted(new_fns.items()):
            if num not in footnotes:
                footnotes[num] = text
                if num > _next_fn[0]:
                    _next_fn[0] = num
            elif footnotes[num].rstrip('.').strip() != text.rstrip('.').strip():
                # Same number, different text → per-page reset, renumber
                _next_fn[0] += 1
                footnotes[_next_fn[0]] = text

    # ── Collect body paragraphs ───────────────────────────────────────────────
    raw_body = []

    for para in paragraphs:
        # Drop "NOTES" / "NOTE" header lines
        if _NOTES_HEADER.match(para):
            continue

        # Case A: paragraph IS a footnote block (starts with "N." or "N ")
        if _is_fn_para(para):
            new_fns, fn_overflow = _split_fn_block(para)
            _add_footnotes(new_fns)
            if fn_overflow:
                raw_body.append(fn_overflow)
            continue

        # Case B: paragraph contains \x01N\x02 tokens inserted by text_to_paragraphs
        if _FN_TOK.search(para):
            chunks = _FN_TOK.split(para)
            body_buf = chunks[0]
            i = 1
            while i < len(chunks):
                fn_num = int(chunks[i])
                after = chunks[i + 1] if i + 1 < len(chunks) else ''
                after_s = after.lstrip()
                # Is what follows uppercase and substantial? → footnote text
                if after_s and (after_s[0].isupper() or after_s[0] in '«\"\'(') and len(after_s) > 15:
                    body_buf = body_buf.rstrip() + f'\x01{fn_num}\x02'
                    fn_raw = str(fn_num) + '. ' + after_s
                    fn_dict, _ = _split_fn_block(fn_raw)
                    _add_footnotes(fn_dict)
                    i += 2
                    # Absorb any additional fn tokens in same paragraph
                    while i < len(chunks):
                        fn_num2 = int(chunks[i])
                        after2 = (chunks[i + 1] if i + 1 < len(chunks) else '').lstrip()
                        fn_raw2 = str(fn_num2) + '. ' + after2
                        fn_dict2, _ = _split_fn_block(fn_raw2)
                        _add_footnotes(fn_dict2)
                        i += 2
                    break
                else:
                    # Inline reference only — keep token in body
                    body_buf += f'\x01{fn_num}\x02' + after
                    i += 2
            if body_buf.strip():
                raw_body.append(body_buf.strip())
            continue

        # Case C: body text has footnote text appended after a sentence end
        # Pattern: "…body sentence. 1. Footnote text…" or "…body. 1 Footnote…"
        m = _FN_CASE_C.search(para)
        if m:
            fn_start_num = int(m.group(1))
            if fn_start_num <= 25:
                body_part = para[:m.start()].strip()
                fn_part = para[m.start():].strip()
                new_fns, fn_overflow = _split_fn_block(fn_part)
                if new_fns:
                    if body_part:
                        raw_body.append(body_part)
                    _add_footnotes(new_fns)
                    if fn_overflow:
                        raw_body.append(fn_overflow)
                    continue

        # Case D: body text ends with an inline ref digit but no footnote text follows
        # e.g. "…pays1." or "»1" at end — keep in body for later ref-linking
        raw_body.append(para)

    # ── Pass 2: render body paragraphs, converting inline digit refs ──────────
    # Now we know which numbers are in footnotes; use that to decide whether
    # a trailing digit is a ref marker.
    body = raw_body  # keep as-is; paragraphs_to_html will handle inline ref sub

    return body, footnotes


def pdf_pages_to_html(pages, title="", author=""):
    """Convert a list of per-page PDF text strings to article HTML.

    Unlike the simple `paragraphs_to_html(text_to_paragraphs('\n\n'.join(pages)))`,
    this function processes each page **separately** so that per-page footnote
    numbering (footnotes that reset to 1 on each new page) is handled correctly.

    Algorithm:
      1. For each page, run text_to_paragraphs + detect_footnotes independently.
      2. Build a local→global ID mapping by merging per-page footnotes into a
         single global dict using the same collision-detection logic as
         _add_footnotes (same ID + same text → same global ID; same ID + different
         text → assign next sequential global ID).
      3. Renumber \\x01N\\x02 markers in that page's body paragraphs.
      4. Render each body paragraph using _INLINE_REF with the per-page mapping,
         so `»1.` on page 3 links to the correct global footnote, not page 1's fn-1.
      5. Strip the article header only from the first page's paragraphs.
    """
    global_fns = {}      # global_id → text
    _next_fn = [0]       # mutable sequential counter

    def _add_page_fns(page_fns):
        """Merge page_fns into global_fns; return local→global ID mapping."""
        mapping = {}
        for num, text in sorted(page_fns.items()):
            norm = text.rstrip('.').strip()
            if num not in global_fns:
                global_fns[num] = text
                if num > _next_fn[0]:
                    _next_fn[0] = num
                mapping[num] = num
            elif global_fns[num].rstrip('.').strip() != norm:
                # Per-page reset: same local number, different text → new global ID
                _next_fn[0] += 1
                global_fns[_next_fn[0]] = text
                mapping[num] = _next_fn[0]
            else:
                mapping[num] = num  # same text, same global ID
        return mapping

    # ── Phase 1: detect footnotes per page, build mappings ───────────────────
    page_data = []   # list of (body_paras, local→global mapping)
    first_page = True
    for page_text in pages:
        page_paras = text_to_paragraphs(page_text)
        if not page_paras:
            continue
        if first_page:
            page_paras = strip_article_header(page_paras, title, author)
            first_page = False
        page_body, page_fns = detect_footnotes(page_paras)
        mapping = _add_page_fns(page_fns)
        page_data.append((page_body, mapping))

    # ── Phase 2: render body paragraphs with per-page ref mapping ─────────────
    used_ref_ids = set()

    def make_sup(global_n):
        if global_n not in global_fns:
            return ''
        ref_id = f'ref-{global_n}'
        id_attr = f' id="{ref_id}"' if ref_id not in used_ref_ids else ''
        used_ref_ids.add(ref_id)
        return f'<sup class="fn-ref"{id_attr}><a href="#fn-{global_n}">{global_n}</a></sup>'

    html_parts = []
    for page_body, mapping in page_data:
        for p in page_body:
            if not p:
                continue
            # Renumber \x01local\x02 markers → \x01global\x02
            p = re.sub(
                r'\x01(\d+)\x02',
                lambda m, mp=mapping: f'\x01{mp.get(int(m.group(1)), int(m.group(1)))}\x02',
                p
            )
            # HTML escape
            p_html = p.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            # Render \x01global\x02 markers as <sup> links
            p_html = _FN_TOK.sub(lambda m: make_sup(int(m.group(1))), p_html)
            # Apply inline-ref detection with per-page local→global mapping.
            # First handle "word.N" (period-style), then "wordN" (direct-attach).
            def sub_ref(m, mp=mapping):
                """For _INLINE_REF: group(1) = digit(s) directly after letter/quote."""
                local_n = int(m.group(1))
                global_n = mp.get(local_n)
                if global_n is None:
                    if local_n in global_fns:
                        return make_sup(local_n)
                    return m.group(0)
                return make_sup(global_n)
            def sub_ref_period(m, mp=mapping):
                """For _INLINE_REF_PERIOD: group(1) = digit; match includes '.' prefix."""
                local_n = int(m.group(1))
                global_n = mp.get(local_n)
                if global_n is None:
                    if local_n in global_fns:
                        return '.' + make_sup(local_n)
                    return m.group(0)
                return '.' + make_sup(global_n)
            p_html = _INLINE_REF_PERIOD.sub(sub_ref_period, p_html)
            p_html = _INLINE_REF.sub(sub_ref, p_html)
            # Expand italic markers → <em>…</em>  (must come last so the
            # lookbehind patterns above can still see the raw \x03/\x04 chars)
            p_html = p_html.replace('\x03', '<em>').replace('\x04', '</em>')
            html_parts.append(f'<p>{p_html}</p>')

    # ── Footnote list ─────────────────────────────────────────────────────────
    if global_fns:
        html_parts.append('<hr class="fn-rule">')
        html_parts.append('<ol class="footnotes">')
        for n in sorted(global_fns.keys()):
            text = (global_fns[n]
                    .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    .replace('\x03', '<em>').replace('\x04', '</em>'))
            html_parts.append(
                f'<li id="fn-{n}" class="footnote">'
                f'<a href="#ref-{n}" class="fn-back" title="Retour au texte">↩</a> '
                f'{text}</li>'
            )
        html_parts.append('</ol>')

    return '\n'.join(html_parts)


def paragraphs_to_html(paragraphs, prebuilt_footnotes=None):
    """Convert list of paragraphs to HTML, extracting and linking footnotes.

    prebuilt_footnotes: when provided (DOCX path), use this dict directly and
    skip detect_footnotes.  Body paragraphs may still contain \\x01N\\x02
    markers which render_para converts to <sup> links.
    """
    if prebuilt_footnotes is not None:
        # DOCX mode: footnotes pre-extracted from XML; body may have \x01N\x02 markers.
        # Just strip NOTES headers; don't run heuristic footnote detection.
        body_paras = [p for p in paragraphs if p and not _NOTES_HEADER.match(p)]
        footnotes = prebuilt_footnotes
    else:
        body_paras, footnotes = detect_footnotes(paragraphs)

    # Track which ref IDs have been used (first occurrence gets the anchor, rest are plain links)
    used_ref_ids = set()

    def make_sup(n):
        if n not in footnotes:
            return ''   # No footnote text for this ref — skip to avoid broken link
        ref_id = f'ref-{n}'
        id_attr = f' id="{ref_id}"' if ref_id not in used_ref_ids else ''
        used_ref_ids.add(ref_id)
        return f'<sup class="fn-ref"{id_attr}><a href="#fn-{n}">{n}</a></sup>'

    def render_para(p):
        # Escape HTML first (tokens are not HTML-special chars)
        p = p.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        # Replace \x01N\x02 tokens with <sup> links
        p = _FN_TOK.sub(lambda m: make_sup(int(m.group(1))), p)
        # Replace inline ref digits when they are known footnotes.
        # First handle "word.N" (period-style), then "wordN" (direct-attach).
        def sub_ref_period(m):
            n = int(m.group(1))
            if n in footnotes:
                return '.' + make_sup(n)
            return m.group(0)
        def sub_ref(m):
            n = int(m.group(1))
            if n in footnotes:
                return make_sup(n)
            return m.group(0)
        p = _INLINE_REF_PERIOD.sub(sub_ref_period, p)
        p = _INLINE_REF.sub(sub_ref, p)
        # Expand italic markers → <em>…</em>  (must come last)
        p = p.replace('\x03', '<em>').replace('\x04', '</em>')
        return f'<p>{p}</p>'

    html_parts = [render_para(p) for p in body_paras if p]

    if footnotes:
        html_parts.append('<hr class="fn-rule">')
        html_parts.append('<ol class="footnotes">')
        for n in sorted(footnotes.keys()):
            text = (footnotes[n]
                    .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    .replace('\x03', '<em>').replace('\x04', '</em>'))
            html_parts.append(
                f'<li id="fn-{n}" class="footnote">'
                f'<a href="#ref-{n}" class="fn-back" title="Retour au texte">↩</a> '
                f'{text}</li>'
            )
        html_parts.append('</ol>')

    return '\n'.join(html_parts)


def extract_article_title_from_pdf(pdf_path):
    """Try to extract article title/author from first page of PDF."""
    pages = extract_pdf_text(pdf_path)
    if not pages:
        return None, None
    first_page = pages[0]
    lines = [l.strip() for l in first_page.split('\n') if l.strip()]
    # Skip page numbers and issue headers
    content_lines = []
    for line in lines:
        if re.match(r'^\d+$', line):
            continue
        if 'Plurielles' in line and ('numéro' in line.lower() or 'n°' in line.lower()):
            continue
        content_lines.append(line)
    if len(content_lines) >= 2:
        return content_lines[0], content_lines[1] if len(content_lines) > 1 else ""
    elif content_lines:
        return content_lines[0], ""
    return None, None


# ─── CSS ──────────────────────────────────────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400;1,600&family=Source+Serif+4:ital,opsz,wght@0,8..60,300;0,8..60,400;0,8..60,600;1,8..60,300;1,8..60,400&family=Inter:wght@300;400;500&display=swap');

:root {
  --clr-bg: #faf8f4;
  --clr-paper: #f4f0e8;
  --clr-dark: #1a1208;
  --clr-primary: #8b1a1a;
  --clr-accent: #c8922a;
  --clr-muted: #6b5f4e;
  --clr-border: #d4c9b5;
  --clr-white: #ffffff;
  --font-serif: 'Playfair Display', 'Georgia', serif;
  --font-body: 'Source Serif 4', 'Georgia', serif;
  --font-ui: 'Inter', system-ui, sans-serif;
  --max-w: 1100px;
  --article-w: 720px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { scroll-behavior: smooth; }

body {
  font-family: var(--font-body);
  font-size: 1.05rem;
  line-height: 1.75;
  color: var(--clr-dark);
  background: var(--clr-bg);
}

/* ── Navigation ─────────────────────────────────────────────────────────────── */
.site-header {
  background: var(--clr-dark);
  border-bottom: 3px solid var(--clr-primary);
}

.site-header__inner {
  max-width: var(--max-w);
  margin: 0 auto;
  padding: 0 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
}

.site-logo {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 0.85rem;
  padding: 1rem 0;
  text-decoration: none;
}

.site-logo__icon {
  color: var(--clr-accent);
  flex-shrink: 0;
  opacity: 0.92;
}

.site-logo__text {
  display: flex;
  flex-direction: column;
}

.site-logo__name {
  font-family: var(--font-serif);
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--clr-white);
  letter-spacing: 0.04em;
  line-height: 1;
}

.site-logo__subtitle {
  font-family: var(--font-ui);
  font-size: 0.68rem;
  color: var(--clr-accent);
  letter-spacing: 0.15em;
  text-transform: uppercase;
  margin-top: 0.25rem;
}

.site-nav {
  display: flex;
  gap: 0.25rem;
  align-items: center;
}

.site-nav a {
  font-family: var(--font-ui);
  font-size: 0.85rem;
  font-weight: 500;
  color: #ccc;
  text-decoration: none;
  padding: 0.5rem 0.85rem;
  border-radius: 3px;
  letter-spacing: 0.04em;
  transition: color 0.2s, background 0.2s;
}

.site-nav a:hover,
.site-nav a.active {
  color: var(--clr-white);
  background: rgba(255,255,255,0.08);
}

/* ── Hero ────────────────────────────────────────────────────────────────────── */
.hero {
  background: var(--clr-dark);
  color: var(--clr-white);
  padding: 5rem 1.5rem 4rem;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 50% 0%, rgba(139,26,26,0.35) 0%, transparent 70%);
}

.hero__inner { position: relative; max-width: var(--max-w); margin: 0 auto; }

.hero__overline {
  font-family: var(--font-ui);
  font-size: 0.72rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--clr-accent);
  margin-bottom: 1.5rem;
}

.hero__title {
  font-family: var(--font-serif);
  font-size: clamp(2.5rem, 6vw, 4.5rem);
  font-weight: 700;
  line-height: 1.1;
  margin-bottom: 1.5rem;
}

.hero__desc {
  font-size: 1.1rem;
  color: rgba(255,255,255,0.75);
  max-width: 600px;
  margin: 0 auto 2.5rem;
  font-weight: 300;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.85rem 2rem;
  border-radius: 3px;
  font-family: var(--font-ui);
  font-size: 0.9rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-decoration: none;
  transition: all 0.2s;
  cursor: pointer;
  border: none;
}

.btn--primary {
  background: var(--clr-primary);
  color: var(--clr-white);
}

.btn--primary:hover { background: #a02020; }

.btn--outline {
  background: transparent;
  color: var(--clr-white);
  border: 1.5px solid rgba(255,255,255,0.4);
  margin-left: 0.75rem;
}

.btn--outline:hover { border-color: var(--clr-white); background: rgba(255,255,255,0.07); }

/* ── Section ─────────────────────────────────────────────────────────────────── */
.section {
  padding: 4rem 1.5rem;
}

.section--alt { background: var(--clr-paper); }

.section__inner { max-width: var(--max-w); margin: 0 auto; }

.section-label {
  font-family: var(--font-ui);
  font-size: 0.7rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--clr-primary);
  margin-bottom: 0.75rem;
}

.section-title {
  font-family: var(--font-serif);
  font-size: clamp(1.6rem, 3vw, 2.2rem);
  font-weight: 700;
  color: var(--clr-dark);
  margin-bottom: 0.5rem;
}

.section-desc {
  color: var(--clr-muted);
  max-width: 60ch;
  margin-bottom: 2.5rem;
}

/* ── Issue Grid ─────────────────────────────────────────────────────────────── */
.issues-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}

.issue-card {
  background: var(--clr-white);
  border: 1px solid var(--clr-border);
  border-radius: 4px;
  overflow: hidden;
  transition: box-shadow 0.2s, transform 0.2s;
  text-decoration: none;
  color: inherit;
  display: flex;
  flex-direction: column;
}

.issue-card:hover {
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
  transform: translateY(-2px);
}

.issue-card__num {
  background: var(--clr-primary);
  color: var(--clr-white);
  font-family: var(--font-ui);
  font-size: 0.72rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  padding: 0.6rem 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.issue-card__year {
  opacity: 0.7;
}

.issue-card__body {
  padding: 1.25rem;
  flex: 1;
}

.issue-card__title {
  font-family: var(--font-serif);
  font-size: 1.1rem;
  font-weight: 600;
  line-height: 1.35;
  margin-bottom: 0.5rem;
  color: var(--clr-dark);
}

.issue-card__dossier {
  font-family: var(--font-ui);
  font-size: 0.78rem;
  color: var(--clr-muted);
  margin-bottom: 0.75rem;
}

.issue-card__footer {
  padding: 0.75rem 1.25rem;
  border-top: 1px solid var(--clr-border);
  font-family: var(--font-ui);
  font-size: 0.78rem;
  color: var(--clr-accent);
  font-weight: 500;
}

/* ── Article List ────────────────────────────────────────────────────────────── */
.article-list {
  list-style: none;
}

.article-list__item {
  border-bottom: 1px solid var(--clr-border);
}

.article-list__item:last-child { border-bottom: none; }

/* Clickable article rows (<a> tag) */
a.article-list__link {
  display: flex;
  gap: 1rem;
  padding: 1rem 1rem 1rem 0;
  text-decoration: none;
  color: inherit;
  transition: background 0.15s, color 0.15s;
  align-items: flex-start;
  border-radius: 4px;
  margin: 0 -0.5rem;
  padding-left: 0.5rem;
}

a.article-list__link:hover {
  background: #f8f2e8;
}

a.article-list__link:hover .article-list__title {
  color: var(--clr-primary);
}

a.article-list__link:hover .article-list__arrow {
  opacity: 1;
  transform: translateX(3px);
}

/* Non-clickable rows (<div> tag) */
div.article-list__link {
  display: flex;
  gap: 1rem;
  padding: 0.75rem 0;
  align-items: flex-start;
}

.article-list__num {
  font-family: var(--font-ui);
  font-size: 0.72rem;
  color: var(--clr-muted);
  min-width: 2rem;
  padding-top: 0.25rem;
}

.article-list__info { flex: 1; }

.article-list__title {
  font-family: var(--font-serif);
  font-size: 1.05rem;
  font-weight: 600;
  line-height: 1.35;
  color: var(--clr-dark);
  transition: color 0.15s;
}

div.article-list__link .article-list__title {
  color: var(--clr-muted);
  font-weight: 400;
  font-size: 0.95rem;
}

.article-list__author {
  font-family: var(--font-ui);
  font-size: 0.8rem;
  color: var(--clr-muted);
  margin-top: 0.2rem;
}

div.article-list__link .article-list__author {
  font-size: 0.75rem;
}

.article-list__arrow {
  font-size: 0.9rem;
  color: var(--clr-primary);
  opacity: 0;
  transition: opacity 0.15s, transform 0.15s;
  padding-top: 0.25rem;
  flex-shrink: 0;
}

.article-list__badge {
  font-family: var(--font-ui);
  font-size: 0.68rem;
  padding: 0.2rem 0.5rem;
  border-radius: 2px;
  background: #e8f5e9;
  color: #2e7d32;
  white-space: nowrap;
  margin-top: 0.3rem;
}

/* Section headers inside lists */
.article-list__section-header {
  padding: 1.25rem 0 0.4rem;
  font-family: var(--font-ui);
  font-size: 0.7rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--clr-primary);
  border-bottom: 2px solid var(--clr-primary);
  margin-bottom: 0.25rem;
}

/* ── Article Page ────────────────────────────────────────────────────────────── */
.article-header {
  background: var(--clr-dark);
  color: var(--clr-white);
  padding: 4rem 1.5rem 3rem;
}

.article-header__inner { max-width: var(--article-w); margin: 0 auto; }

.article-header__issue {
  font-family: var(--font-ui);
  font-size: 0.72rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--clr-accent);
  margin-bottom: 1rem;
  text-decoration: none;
}

.article-header__issue:hover { text-decoration: underline; }

.article-header__title {
  font-family: var(--font-serif);
  font-size: clamp(1.6rem, 4vw, 2.5rem);
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 1rem;
}

.article-header__author {
  font-family: var(--font-ui);
  font-size: 1rem;
  color: rgba(255,255,255,0.7);
}

.article-header__pdf {
  display: inline-flex;
  align-items: center;
  gap: 0.45em;
  margin-top: 1.25rem;
  padding: 0.38rem 0.85rem;
  border: 1px solid rgba(255,255,255,0.35);
  border-radius: 4px;
  color: rgba(255,255,255,0.8);
  font-family: var(--font-ui);
  font-size: 0.78rem;
  letter-spacing: 0.02em;
  text-decoration: none;
  transition: background 0.18s, border-color 0.18s, color 0.18s;
}
.article-header__pdf:hover {
  background: rgba(255,255,255,0.12);
  border-color: rgba(255,255,255,0.7);
  color: #fff;
}

.article-body {
  max-width: var(--article-w);
  margin: 0 auto;
  padding: 3rem 1.5rem 5rem;
}

.article-body p {
  margin-bottom: 1.4em;
  text-align: justify;
  hyphens: auto;
}

.article-body p:first-child::first-letter {
  font-family: var(--font-serif);
  font-size: 3.5em;
  font-weight: 700;
  float: left;
  line-height: 0.8;
  margin: 0.05em 0.12em 0 0;
  color: var(--clr-primary);
}

.article-nav {
  display: flex;
  gap: 1rem;
  padding: 1.5rem 0;
  border-top: 1px solid var(--clr-border);
  margin-top: 2rem;
  font-family: var(--font-ui);
  font-size: 0.85rem;
}

.article-nav a {
  color: var(--clr-primary);
  text-decoration: none;
}

.article-nav a:hover { text-decoration: underline; }

.article-nav__sep { color: var(--clr-muted); }

/* ── Issue Page ──────────────────────────────────────────────────────────────── */
.issue-header {
  background: var(--clr-dark);
  color: var(--clr-white);
  padding: 4rem 1.5rem 3rem;
}

.issue-header__inner { max-width: var(--max-w); margin: 0 auto; }

.issue-header__num {
  font-family: var(--font-ui);
  font-size: 0.72rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--clr-accent);
  margin-bottom: 0.75rem;
}

.issue-header__title {
  font-family: var(--font-serif);
  font-size: clamp(1.8rem, 4vw, 3rem);
  font-weight: 700;
  line-height: 1.15;
  margin-bottom: 0.75rem;
}

.issue-header__dossier {
  font-family: var(--font-ui);
  font-size: 0.9rem;
  color: rgba(255,255,255,0.6);
}

.issue-header__actions {
  margin-top: 1.5rem;
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  align-items: center;
}

/* ── Comité ──────────────────────────────────────────────────────────────────── */
.team-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 2rem;
}

.team-card {
  background: var(--clr-white);
  border: 1px solid var(--clr-border);
  border-radius: 4px;
  overflow: hidden;
}

.team-card__avatar {
  height: 6px;
  background: linear-gradient(90deg, var(--clr-primary) 0%, var(--clr-accent) 100%);
}

.team-card__photo {
  width: 100%;
  height: 220px;
  object-fit: cover;
  object-position: top center;
  display: block;
}

.team-card__body { padding: 1.5rem; }

.team-card__name {
  font-family: var(--font-serif);
  font-size: 1.2rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.team-card__role {
  font-family: var(--font-ui);
  font-size: 0.75rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--clr-primary);
  margin-bottom: 1rem;
  font-weight: 500;
}

.team-card__bio {
  font-size: 0.9rem;
  color: var(--clr-muted);
  line-height: 1.65;
}

/* ── About ───────────────────────────────────────────────────────────────────── */
.about-content {
  max-width: 720px;
  margin: 0 auto;
}

.about-content h2 {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  font-weight: 700;
  margin: 2rem 0 0.75rem;
  color: var(--clr-dark);
}

.about-content p {
  color: var(--clr-muted);
  margin-bottom: 1rem;
  line-height: 1.75;
}

.about-content a:not(.btn) { color: var(--clr-primary); }

.bookstore-list {
  list-style: none;
  padding: 0;
  margin: 1rem 0 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.bookstore-list li {
  padding: 0.9rem 1.1rem;
  background: var(--clr-bg-alt, #f8f7f4);
  border-left: 3px solid var(--clr-primary);
  border-radius: 0 4px 4px 0;
  color: var(--clr-muted);
  line-height: 1.6;
}
.bookstore-list strong a { color: var(--clr-dark); text-decoration: none; }
.bookstore-list strong a:hover { color: var(--clr-primary); }
.bookstore-list a { color: var(--clr-primary); }

/* ── Footnotes ───────────────────────────────────────────────────────────────── */
sup.fn-ref { font-size: 0.7em; line-height: 1; vertical-align: super; }
sup.fn-ref a { color: var(--clr-primary); text-decoration: none; font-weight: 600; }
sup.fn-ref a:hover { text-decoration: underline; }
hr.fn-rule { border: none; border-top: 1px solid var(--clr-border); margin: 3rem 0 1.5rem; }
.footnotes {
  font-size: 0.83rem;
  color: var(--clr-muted);
  padding-left: 1.5rem;
  line-height: 1.65;
}
.footnotes li { margin-bottom: 0.75rem; }
a.fn-back { color: var(--clr-muted); text-decoration: none; margin-right: 0.4em; }
a.fn-back:hover { color: var(--clr-primary); }

/* ── Breadcrumb ──────────────────────────────────────────────────────────────── */
.breadcrumb {
  background: var(--clr-paper);
  border-bottom: 1px solid var(--clr-border);
  padding: 0.6rem 1.5rem;
}

.breadcrumb__inner {
  max-width: var(--max-w);
  margin: 0 auto;
  display: flex;
  gap: 0.5rem;
  align-items: center;
  font-family: var(--font-ui);
  font-size: 0.78rem;
  color: var(--clr-muted);
  flex-wrap: wrap;
}

.breadcrumb a {
  color: var(--clr-primary);
  text-decoration: none;
}

.breadcrumb a:hover { text-decoration: underline; }

.breadcrumb__sep { opacity: 0.4; }

/* ── Pill ────────────────────────────────────────────────────────────────────── */
.pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.8rem;
  border-radius: 2rem;
  font-family: var(--font-ui);
  font-size: 0.75rem;
  font-weight: 500;
}

.pill--green { background: #e8f5e9; color: #2e7d32; }
.pill--blue  { background: #e3f2fd; color: #1565c0; }
.pill--gold  { background: #fff8e1; color: #f57f17; }

/* ── Divider ─────────────────────────────────────────────────────────────────── */
.ornament {
  text-align: center;
  margin: 2rem 0;
  color: var(--clr-accent);
  font-size: 1.2rem;
  letter-spacing: 0.5em;
}

/* ── Footer ──────────────────────────────────────────────────────────────────── */
.site-footer {
  background: var(--clr-dark);
  color: rgba(255,255,255,0.5);
  padding: 3rem 1.5rem;
  font-family: var(--font-ui);
  font-size: 0.82rem;
}

.site-footer__inner {
  max-width: var(--max-w);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 2rem;
}

.site-footer__logo {
  font-family: var(--font-serif);
  font-size: 1.3rem;
  color: var(--clr-white);
  margin-bottom: 0.5rem;
}

.site-footer__copy {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255,255,255,0.1);
  text-align: center;
  grid-column: 1 / -1;
}

.site-footer h4 {
  color: var(--clr-white);
  margin-bottom: 0.75rem;
  font-size: 0.82rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.site-footer a {
  display: block;
  color: rgba(255,255,255,0.5);
  text-decoration: none;
  padding: 0.2rem 0;
  transition: color 0.2s;
}

.site-footer a:hover { color: var(--clr-white); }

/* ── Responsive ─────────────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .site-header__inner { flex-wrap: wrap; padding: 0 1rem; }
  .site-nav { gap: 0; flex-wrap: wrap; }
  .site-nav a { padding: 0.4rem 0.6rem; font-size: 0.8rem; }
  .issues-grid { grid-template-columns: 1fr; }
  .team-grid { grid-template-columns: 1fr; }
  .site-footer__inner { grid-template-columns: 1fr; }
  .hero { padding: 3rem 1rem 2.5rem; }
}

@media (max-width: 480px) {
  .site-logo__name { font-size: 1.3rem; }
  .site-logo__icon { width: 26px; height: 32px; }
  .btn--outline { margin-left: 0; margin-top: 0.5rem; }
  .issue-header__actions { flex-direction: column; align-items: flex-start; }
}
"""


# ─── HTML Helpers ─────────────────────────────────────────────────────────────
_SITE_BASE_URL = "https://www.revueplurielles.fr"
_SITE_DEFAULT_DESC = ("Plurielles est une revue semestrielle de culture juive "
                      "laïque et humaniste, publiée par l'AJHL depuis 1993.")


def html_page(title, content, depth=0, active_nav="", description="", extra_head=""):
    # Keep title short for browser tab
    title = title[:80] if len(title) > 80 else title
    desc = description or _SITE_DEFAULT_DESC
    prefix = "../" * depth
    nav_links = [
        ("Accueil", f"{prefix}index.html", ""),
        ("Numéros", f"{prefix}numeros/index.html", "numeros"),
        ("Comité de rédaction", f"{prefix}comite.html", "comite"),
        ("À propos", f"{prefix}about.html", "about"),
    ]
    nav_html = "\n".join(
        f'<a href="{url}" class="{"active" if key == active_nav else ""}">{label}</a>'
        for label, url, key in nav_links
    )

    footer_links_numeros = "".join(
        f'<a href="{prefix}numeros/pl{n:02d}/index.html">Numéro {n}</a>'
        for n in [23, 22, 21, 20, 19, 18]
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Plurielles</title>
  <link rel="stylesheet" href="{prefix}css/style.css">
  <meta name="description" content="{desc}">
  <meta property="og:title" content="{title} — Plurielles">
  <meta property="og:description" content="{desc}">
  <meta property="og:site_name" content="Plurielles">
  <meta property="og:locale" content="fr_FR">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{title} — Plurielles">
  <meta name="twitter:description" content="{desc}">{extra_head}
</head>
<body>

<header class="site-header">
  <div class="site-header__inner">
    <a href="{prefix}index.html" class="site-logo">
      <svg class="site-logo__icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 62" width="34" height="42" aria-hidden="true" fill="currentColor">
        <!-- Base -->
        <rect x="6" y="56" width="38" height="5" rx="2.5"/>
        <rect x="18" y="50" width="14" height="7" rx="1.5"/>
        <!-- Central stem -->
        <rect x="22.5" y="10" width="5" height="42" rx="2.5"/>
        <!-- Left arms (quadratic bezier: goes sideways then curves up) -->
        <path d="M22.5,38 Q4,38 4,12" stroke="currentColor" stroke-width="3.2" fill="none" stroke-linecap="round"/>
        <path d="M22.5,33 Q13,33 13,12" stroke="currentColor" stroke-width="3.2" fill="none" stroke-linecap="round"/>
        <path d="M22.5,28 Q19,28 19,12" stroke="currentColor" stroke-width="3.2" fill="none" stroke-linecap="round"/>
        <!-- Right arms -->
        <path d="M27.5,28 Q31,28 31,12" stroke="currentColor" stroke-width="3.2" fill="none" stroke-linecap="round"/>
        <path d="M27.5,33 Q37,33 37,12" stroke="currentColor" stroke-width="3.2" fill="none" stroke-linecap="round"/>
        <path d="M27.5,38 Q46,38 46,12" stroke="currentColor" stroke-width="3.2" fill="none" stroke-linecap="round"/>
        <!-- Flames (7) -->
        <ellipse cx="4"  cy="8" rx="2.8" ry="3.8"/>
        <ellipse cx="13" cy="8" rx="2.8" ry="3.8"/>
        <ellipse cx="19" cy="8" rx="2.8" ry="3.8"/>
        <ellipse cx="25" cy="8" rx="2.8" ry="3.8"/>
        <ellipse cx="31" cy="8" rx="2.8" ry="3.8"/>
        <ellipse cx="37" cy="8" rx="2.8" ry="3.8"/>
        <ellipse cx="46" cy="8" rx="2.8" ry="3.8"/>
      </svg>
      <span class="site-logo__text">
        <span class="site-logo__name">Plurielles</span>
        <span class="site-logo__subtitle">Revue de culture juive laïque</span>
      </span>
    </a>
    <nav class="site-nav">
      {nav_html}
    </nav>
  </div>
</header>

{content}

<footer class="site-footer">
  <div class="site-footer__inner">
    <div>
      <div class="site-footer__logo">Plurielles</div>
      <p>Revue semestrielle de culture juive laïque et humaniste, publiée par l'Association pour un Judaïsme Humaniste et Laïque (AJHL).</p>
      <p style="margin-top:1rem">Contact : <a href="mailto:izio.rosenman@gmail.com">izio.rosenman@gmail.com</a></p>
    </div>
    <div>
      <h4>Derniers numéros</h4>
      {footer_links_numeros}
    </div>
    <div>
      <h4>Navigation</h4>
      <a href="{prefix}numeros/index.html">Tous les numéros</a>
      <a href="{prefix}comite.html">Comité de rédaction</a>
      <a href="{prefix}about.html">À propos de la revue</a>
    </div>
    <div class="site-footer__copy">
      © Plurielles — Association pour un Judaïsme Humaniste et Laïque (AJHL) — 83, avenue d'Italie, 75013 Paris
    </div>
  </div>
</footer>

</body>
</html>"""


def breadcrumb(*crumbs):
    parts = []
    for i, (label, url) in enumerate(crumbs):
        if i > 0:
            parts.append('<span class="breadcrumb__sep">›</span>')
        if url:
            parts.append(f'<a href="{url}">{label}</a>')
        else:
            parts.append(f'<span>{label}</span>')
    return f"""<div class="breadcrumb"><div class="breadcrumb__inner">{''.join(parts)}</div></div>"""


# ─── Page Generators ──────────────────────────────────────────────────────────
def generate_homepage(all_issues):
    latest = max(all_issues)
    latest_data = ISSUES[latest]

    recent_cards = ""
    for n in sorted(all_issues, reverse=True)[:6]:
        info = ISSUES[n]
        recent_cards += f"""
    <a href="numeros/pl{n:02d}/index.html" class="issue-card">
      <div class="issue-card__num">
        <span>N° {n}</span>
        <span class="issue-card__year">{info['year']}</span>
      </div>
      <div class="issue-card__body">
        <div class="issue-card__title">{info['title']}</div>
        <div class="issue-card__dossier">Dossier : {info['dossier']}</div>
      </div>
      <div class="issue-card__footer">Lire ce numéro →</div>
    </a>"""

    content = f"""
<section class="hero">
  <div class="hero__inner">
    <p class="hero__overline">Revue semestrielle · Depuis 1993</p>
    <h1 class="hero__title">Plurielles</h1>
    <p class="hero__desc">Une revue de culture juive laïque et humaniste, espace de réflexion sur le judaïsme dans sa diversité, son histoire et sa modernité.</p>
    <div>
      <a href="numeros/pl{latest:02d}/index.html" class="btn btn--primary">Dernier numéro (N° {latest})</a>
      <a href="numeros/index.html" class="btn btn--outline">Tous les numéros</a>
    </div>
  </div>
</section>

<section class="section section--alt">
  <div class="section__inner">
    <div class="about-content">
      <p class="section-label">La revue</p>
      <h2 class="section-title">Une voix pour le judaïsme laïque</h2>
      <p>Plurielles est une revue semestrielle fondée en 1993 par l'Association pour un Judaïsme Humaniste et Laïque (AJHL). Elle rassemble des contributions d'universitaires, d'écrivains, de philosophes et de journalistes autour de questions qui touchent à l'identité juive, à l'histoire, à la culture et à l'actualité.</p>
      <p>Chaque numéro est organisé autour d'un dossier thématique — langues de la diaspora, frontières, la peur, le dialogue, la modernité — et propose des essais, des recensions, des textes littéraires et des entretiens.</p>
      <p style="margin-top:1.5rem">
        <a href="about.html" class="btn btn--primary">En savoir plus</a>
        <a href="comite.html" class="btn btn--outline" style="margin-left:0.75rem; color: var(--clr-dark); border-color: var(--clr-border);">Comité de rédaction</a>
      </p>
    </div>
  </div>
</section>

<section class="section">
  <div class="section__inner">
    <p class="section-label">Dernières parutions</p>
    <h2 class="section-title">Numéros récents</h2>
    <p class="section-desc">Découvrez les articles de Plurielles, accessibles en ligne dans leur intégralité.</p>
    <div class="issues-grid">
      {recent_cards}
    </div>
  </div>
</section>
"""
    return html_page(
        "Accueil", content, depth=0, active_nav="",
        description=("Plurielles — revue semestrielle de culture juive laïque et humaniste depuis 1993. "
                     "Essais, entretiens, textes littéraires sur le judaïsme, la diaspora et la modernité."),
        extra_head=f'\n  <link rel="canonical" href="{_SITE_BASE_URL}/">'
    )


def generate_issues_index(all_issues):
    cards = ""
    for n in sorted(all_issues, reverse=True):
        info = ISSUES[n]
        has_articles = info.get('articles') or info.get('_has_pdfs')
        badge = '<span class="pill pill--green">Articles en ligne</span>' if has_articles else '<span class="pill pill--gold">PDF disponible</span>'
        cards += f"""
    <a href="pl{n:02d}/index.html" class="issue-card">
      <div class="issue-card__num">
        <span>N° {n}</span>
        <span class="issue-card__year">{info['year']}</span>
      </div>
      <div class="issue-card__body">
        <div class="issue-card__title">{info['title']}</div>
        <div class="issue-card__dossier">Dossier : {info['dossier']}</div>
        {badge}
      </div>
      <div class="issue-card__footer">Voir le sommaire →</div>
    </a>"""

    content = f"""
{breadcrumb(("Accueil", "../index.html"), ("Tous les numéros", None))}

<section class="issue-header">
  <div class="issue-header__inner">
    <div class="issue-header__num">Archive complète · {len(all_issues)} numéros</div>
    <h1 class="issue-header__title">Tous les numéros de Plurielles</h1>
    <p class="issue-header__dossier">De 1993 à aujourd'hui — numéros accessibles en ligne</p>
  </div>
</section>

<section class="section">
  <div class="section__inner">
    <div class="issues-grid">
      {cards}
    </div>
  </div>
</section>
"""
    return html_page(
        "Tous les numéros", content, depth=1, active_nav="numeros",
        description=(f"Tous les numéros de Plurielles (N\u00b0\u00a01 à {max(all_issues)}), "
                     "revue de culture juive laïque et humaniste publiée depuis 1993."),
        extra_head=f'\n  <link rel="canonical" href="{_SITE_BASE_URL}/numeros/index.html">'
    )


def generate_issue_page(n, info, articles_html, pdf_path=None, depth=2):
    has_pdf = pdf_path is not None and Path(pdf_path).exists()
    pdf_link = f'<a href="../../assets/pdfs/pl{n:02d}.pdf" class="btn btn--outline">Télécharger le PDF</a>' if has_pdf else ""

    content = f"""
{breadcrumb(("Accueil", "../../index.html"), ("Numéros", "../index.html"), (f"N° {n}", None))}

<section class="issue-header">
  <div class="issue-header__inner">
    <div class="issue-header__num">Plurielles · Numéro {n} · {info['year']}</div>
    <h1 class="issue-header__title">{info['title']}</h1>
    <p class="issue-header__dossier">Dossier : {info['dossier']}</p>
    <div class="issue-header__actions">
      {pdf_link}
    </div>
  </div>
</section>

<section class="section">
  <div class="section__inner">
    <h2 class="section-title">Sommaire</h2>
    <p class="section-desc" style="margin-bottom:1.5rem">
      {len(info.get('articles', [])) or ''} articles
    </p>
    {articles_html}
  </div>
</section>
"""
    issue_desc = (f"Plurielles N\u00b0\u00a0{n} ({info['year']}) — {info['title']}. "
                  f"Dossier\u00a0: {info.get('dossier', '')}.")
    return html_page(
        f"N° {n} — {info['title']}", content, depth=2, active_nav="numeros",
        description=issue_desc[:160],
        extra_head=f'\n  <link rel="canonical" href="{_SITE_BASE_URL}/numeros/pl{n:02d}/index.html">'
    )


def generate_article_page(n, issue_info, title, author, body_html, prev_link="", next_link="", pdf_url="", article_slug=""):
    nav = ""
    if prev_link or next_link:
        nav = f"""<div class="article-nav">
    {'<a href="' + prev_link + '">← Article précédent</a>' if prev_link else ''}
    {'<span class="article-nav__sep">·</span>' if prev_link and next_link else ''}
    {'<a href="' + next_link + '">Article suivant →</a>' if next_link else ''}
    <span style="flex:1"></span>
    <a href="../index.html">Retour au numéro {n}</a>
  </div>"""

    pdf_btn = ""
    if pdf_url:
        pdf_btn = f"""
    <a href="{pdf_url}" class="article-header__pdf" download>
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
      Télécharger le PDF
    </a>"""

    content = f"""
{breadcrumb(("Accueil", "../../../index.html"), ("Numéros", "../../index.html"), (f"N° {n}", "../index.html"), (title[:50], None))}

<div class="article-header">
  <div class="article-header__inner">
    <a href="../index.html" class="article-header__issue">← Plurielles N° {n} — {issue_info['year']}</a>
    <h1 class="article-header__title">{title}</h1>
    <p class="article-header__author">{author}</p>{pdf_btn}
  </div>
</div>

<div class="article-body">
  {body_html}
  {nav}
</div>
"""
    # ── SEO metadata for article pages ─────────────────────────────────────────
    # Unescape HTML entities for clean description / JSON-LD
    raw_title = (title.replace('&amp;', '&').replace('&lt;', '<')
                      .replace('&gt;', '>').replace('&#39;', "'")
                      .replace('&quot;', '"'))
    raw_author = (author.replace('&amp;', '&').replace('&lt;', '<')
                        .replace('&gt;', '>').replace('&#39;', "'"))
    if raw_author:
        desc = f"{raw_title[:95]} — {raw_author}. Plurielles N° {n} ({issue_info['year']})."
    else:
        desc = f"{raw_title[:110]}. Plurielles N° {n} ({issue_info['year']})."
    desc = desc[:160]

    canonical = f"{_SITE_BASE_URL}/numeros/pl{n:02d}/articles/{article_slug}.html"
    ld_data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": raw_title[:110],
        "datePublished": str(issue_info.get('year', '')),
        "publisher": {
            "@type": "Organization",
            "name": "Plurielles",
            "url": _SITE_BASE_URL + "/"
        },
        "isPartOf": {
            "@type": "Periodical",
            "name": "Plurielles",
            "issueNumber": str(n)
        },
        "inLanguage": "fr",
        "url": canonical,
    }
    if raw_author:
        ld_data["author"] = {"@type": "Person", "name": raw_author}
    extra_head = (
        f'\n  <link rel="canonical" href="{canonical}">'
        f'\n  <meta property="og:type" content="article">'
        f'\n  <meta property="og:url" content="{canonical}">'
        f'\n  <script type="application/ld+json">{json.dumps(ld_data, ensure_ascii=False, separators=(",", ":"))}</script>'
    )

    return html_page(f"{title} — N° {n}", content, depth=3, active_nav="numeros",
                     description=desc, extra_head=extra_head)


# ─── Comité de Rédaction ──────────────────────────────────────────────────────
COMMITTEE = [
    {
        "name": "Izio Rosenman",
        "role": "Rédacteur en chef",
        "photo": "assets/images/comite/izio-rosenman.jpg",
        "bio": "Directeur de recherche au CNRS en physique et psychanalyste, Izio Rosenman est le fondateur et rédacteur en chef de la revue Plurielles. Il a fait du psychodrame psychanalytique au CMPP de l'OSE. Président de l'Association pour un Judaïsme humaniste et laïque (AJHL) et de l'Association pour l'enseignement du Judaïsme comme culture (AEJC), il a organisé les rencontres littéraires Livres des Mondes juifs et Diasporas en dialogue (2008-2016). Il a traduit de l'hébreu La foi athée des Juifs laïques de Yaakov Malkin (éd. El-Ouns, 2002) et a coordonné le numéro de la revue Panoramiques, Juifs laïques. Du religieux vers le culturel (éd. Arléa-Corlet, 2002).",
    },
    {
        "name": "Anny Dayan Rosenman",
        "role": "Membre du comité de rédaction",
        "photo": "assets/images/comite/anny-dayan-rosenman.jpg",
        "bio": "Maître de conférences de littérature et de cinéma à l'Université Paris-Diderot, Anny Dayan Rosenman travaille sur les écrivains juifs de langue française. Elle a publié notamment : Le survivant un écrivain du XXe siècle (avec Carine Trevisan, Textuel, 2003) ; La guerre d'Algérie dans la mémoire et l'imaginaire (avec Lucette Valensi, éd. Bouchène, 2003) ; Les Alphabets de la Shoah, Survivre, témoigner, écrire (CNRS éditions, 2007 ; poche Biblis, 2013) ; Piotr Rawicz et la solitude du témoin (avec Fransisca Louwagie, éd. Kimé, 2013).",
    },
    {
        "name": "Martine Leibovici",
        "role": "Membre du comité de rédaction",
        "photo": "assets/images/comite/martine-leibovici.jpg",
        "bio": "Maître de conférences émérite en philosophie à l'Université Paris-Diderot, Martine Leibovici a publié notamment : Hannah Arendt, une Juive. Expérience, politique et histoire (Desclée de Brouwer, 2008) ; Autobiographie de transfuges. Karl-Philipp Moritz, Richard Wright, Assia Djebar (éd. Le Manuscrit, 2013) ; et avec Anne-Marie Roviello, Le pervertissement totalitaire. La banalité du mal selon Hannah Arendt (Kimé, 2017). Elle a récemment coordonné, avec Aurore Mréjen, un Cahier de l'Herne consacré à Hannah Arendt (2021).",
    },
    {
        "name": "Carole Ksiazenicer-Matheron",
        "role": "Membre du comité de rédaction",
        "photo": "assets/images/comite/carole-ksiazenicer-matheron.jpg",
        "photo_position": "center center",
        "bio": "Maître de conférences en littérature comparée à l'Université Paris 3, Carole Ksiazenicer-Matheron a traduit plusieurs classiques de la littérature yiddish en français, notamment Argile et autres récits d'Israël Joshua Singer et La Danse des démons d'Esther Kreitman. Elle a publié : Les temps de la fin : Roth, Singer, Boulgakov (Honoré Champion, 2006) ; Déplier le temps : Israël Joshua Singer. Un écrivain yiddish dans l'histoire (Classiques Garnier, 2012) ; Le Sacrifice de la beauté (Éditions Sorbonne Nouvelle, 2000).",
    },
    {
        "name": "Jean-Charles Szurek",
        "role": "Membre du comité de rédaction",
        "photo": "assets/images/comite/jean-charles-szurek.webp",
        "bio": "Directeur de recherche émérite au CNRS, Jean-Charles Szurek est spécialiste des questions judéo-polonaises et de la mémoire de la Shoah en Pologne. Il a notamment publié La Pologne, les Juifs et le communisme (Michel Houdiard éd., 2012) et codirigé Les Polonais et la Shoah. Une nouvelle école historique (CNRS éditions, 2019).",
    },
    {
        "name": "Philippe Zard",
        "role": "Membre du comité de rédaction",
        "photo": "assets/images/comite/philippe-zard.jpg",
        "photo_position": "center center",
        "bio": "Professeur de littérature comparée à l'Université Paris-Nanterre, Philippe Zard mène des recherches sur l'imaginaire politique et religieux dans la littérature européenne. Il a publié notamment La Fiction de l'Occident. Thomas Mann, Franz Kafka, Albert Cohen (PUF, 1999) et De Shylock à Cinoc. Essai sur les judaïsmes apocryphes (Garnier, 2018). Il a assuré l'édition critique de la tétralogie romanesque d'Albert Cohen : Solal et les Solal, aux éditions Gallimard (collection Quarto, 2018).",
    },
    {
        "name": "Brigitte Stora",
        "role": "Membre du comité de rédaction",
        "photo": "assets/images/comite/brigitte-stora.jpg",
        "bio": "Journaliste, Brigitte Stora est auteure de documentaires et de fictions radiophoniques pour France Culture et France Inter. Sociologue de formation, elle a soutenu en 2021 à l'Université Denis-Diderot-Paris 7 une thèse intitulée : L'antisémitisme : un meurtre du sujet et un barrage à l'émancipation ? Elle a publié un essai : Que sont mes amis devenus : les juifs, Charlie puis tous les nôtres (éd. Le Bord de L'eau, 2016).",
    },
    {
        "name": "Simon Wuhl",
        "role": "Membre du comité de rédaction",
        "photo": "assets/images/comite/simon-wuhl.jpg",
        "bio": "Sociologue et universitaire spécialisé dans la sociologie du travail et la sociologie politique, Simon Wuhl a été professeur associé à l'université de Marne-la-Vallée et au CNAM. Il a publié plusieurs ouvrages sur les questions de justice sociale, notamment L'Égalité. Nouveaux débats (PUF, 2002) et Discrimination positive et justice sociale (PUF, 2007). Il est également auteur de plusieurs livres sur le judaïsme, notamment Michael Walzer et l'empreinte du judaïsme (Le Bord de l'eau, 2017).",
    },
    {
        "name": "Nadine Vasseur",
        "role": "Membre du comité de rédaction",
        "photo": "assets/images/comite/nadine-vasseur.png",
        "photo_position": "center center",
        "bio": "Longtemps productrice à France Culture, Nadine Vasseur est l'auteure d'une dizaine de livres, parmi lesquels Simone Veil, vie publique archives privées (Tohu-Bohu, 2019), Je ne lui ai pas dit que j'écrivais ce livre (Liana Levi, 2008) et 36 rue du Caire, une histoire de la confection (Librairie Petite Égypte, 2019). Elle dirige depuis 2014 le festival Vino Voce de Saint-Émilion.",
    },
    {
        "name": "Daniel Oppenheim",
        "role": "Membre du comité de rédaction",
        "bio": "Psychiatre et psychanalyste, Daniel Oppenheim a été chef de service à l'Institut Gustave Roussy. Spécialiste de la relation soignant-soigné et de l'éthique médicale, il s'est consacré à l'accompagnement psychologique des patients atteints de cancer, notamment des enfants et adolescents. Il réfléchit également aux questions d'identité juive à travers ses contributions à Plurielles.",
    },
    {
        "name": "Hélène Oppenheim-Gluckman",
        "role": "Membre du comité de rédaction",
        "bio": "Psychiatre et psychanalyste, Hélène Oppenheim-Gluckman est spécialiste de la psychopathologie et de la clinique psychanalytique. Elle a publié des travaux sur la mémoire familiale, la transmission et les problématiques identitaires juives, contribuant régulièrement à Plurielles sur les questions de mémoire, de trauma et d'héritage culturel.",
    },
    {
        "name": "Meir Waintrater",
        "role": "Membre du comité de rédaction",
        "bio": "Journaliste et essayiste, Meir Waintrater est rédacteur en chef de L'Arche, mensuel de la communauté juive de France. Spécialiste des questions de la vie juive contemporaine, de la culture israélienne et des relations judéo-arabes, il contribue régulièrement à des réflexions sur l'identité juive et le sionisme dans le contexte français et international.",
    },
]


def generate_comite_page():
    cards = ""
    for member in COMMITTEE:
        photo = member.get('photo', '')
        if photo:
            pos = member.get('photo_position', 'top center')
            photo_html = f'<img src="{photo}" alt="{member["name"]}" class="team-card__photo" style="object-position:{pos}">'
        else:
            photo_html = '<div class="team-card__avatar"></div>'
        cards += f"""
    <div class="team-card">
      {photo_html}
      <div class="team-card__body">
        <h3 class="team-card__name">{member['name']}</h3>
        <p class="team-card__role">{member['role']}</p>
        <p class="team-card__bio">{member['bio']}</p>
      </div>
    </div>"""

    content = f"""
{breadcrumb(("Accueil", "index.html"), ("Comité de rédaction", None))}

<section class="issue-header">
  <div class="issue-header__inner">
    <div class="issue-header__num">La revue</div>
    <h1 class="issue-header__title">Comité de rédaction</h1>
    <p class="issue-header__dossier">Les femmes et hommes qui font Plurielles depuis 1993</p>
  </div>
</section>

<section class="section">
  <div class="section__inner">
    <p class="section-desc">Le comité de rédaction de Plurielles réunit des universitaires, des écrivains, des journalistes et des intellectuels engagés dans la réflexion sur le judaïsme laïque et humaniste.</p>
    <div class="team-grid" style="margin-top:2rem">
      {cards}
    </div>
  </div>
</section>
"""
    return html_page(
        "Comité de rédaction", content, depth=0, active_nav="comite",
        description=("Le comité de rédaction de Plurielles — universitaires, écrivains, "
                     "journalistes et intellectuels engagés dans la réflexion sur le judaïsme laïque."),
        extra_head=f'\n  <link rel="canonical" href="{_SITE_BASE_URL}/comite.html">'
    )


def generate_about_page():
    content = f"""
{breadcrumb(("Accueil", "index.html"), ("À propos", None))}

<section class="issue-header">
  <div class="issue-header__inner">
    <div class="issue-header__num">Présentation</div>
    <h1 class="issue-header__title">À propos de Plurielles</h1>
    <p class="issue-header__dossier">Une revue de culture juive laïque et humaniste depuis 1993</p>
  </div>
</section>

<section class="section">
  <div class="section__inner">
    <div class="about-content">

      <h2>La revue</h2>
      <p>Plurielles est une revue semestrielle fondée en 1993 par l'Association pour un Judaïsme Humaniste et Laïque (AJHL). Elle publie des contributions d'universitaires, d'écrivains, de philosophes et de journalistes qui s'interrogent sur le judaïsme dans sa diversité, son histoire et sa contemporanéité.</p>
      <p>Chaque numéro s'articule autour d'un dossier thématique — langues de la diaspora, frontières, la peur, le dialogue, la modernité, le rapport à l'Autre — et propose des essais, des recensions critiques, des textes littéraires, des entretiens et des documents.</p>
      <p>La revue se veut un espace de réflexion laïque et ouverte sur le judaïsme, en dialogue avec les grandes questions de la philosophie, de la littérature et de l'histoire contemporaine.</p>

      <h2>L'AJHL</h2>
      <p>L'Association pour un Judaïsme Humaniste et Laïque (AJHL) est une association loi 1901 fondée à Paris. Elle œuvre pour la promotion d'une vision laïque et humaniste du judaïsme, ancrée dans l'héritage culturel, philosophique et littéraire du peuple juif, indépendante de toute orthodoxie religieuse.</p>
      <p>L'AJHL a organisé de nombreuses rencontres culturelles, colloques et manifestations, dont les rencontres Livres des Mondes juifs et Diasporas en dialogue (2008-2016).</p>

      <h2>Se procurer la revue</h2>
      <p>Les numéros récents de Plurielles sont disponibles en librairie à Paris et sur commande. Les anciens numéros peuvent être commandés directement auprès de l'association.</p>
      <ul style="margin: 1rem 0 1rem 1.5rem; color: var(--clr-muted);">
        <li>Numéros récents : 18 €</li>
        <li>Anciens numéros : 13 €</li>
      </ul>

      <h2>Librairies à Paris</h2>
      <p>Vous pouvez trouver Plurielles dans les librairies suivantes :</p>
      <ul class="bookstore-list">
        <li>
          <strong><a href="https://www.mahj.org/fr" target="_blank" rel="noopener">Librairie du Musée d'art et d'histoire du Judaïsme (mahJ)</a></strong><br>
          71 rue du Temple, 75003 Paris —
          <a href="https://maps.google.com/?q=71+rue+du+Temple,+75003+Paris" target="_blank" rel="noopener">Plan</a>
        </li>
        <li>
          <strong><a href="https://www.librairie-compagnie.fr/" target="_blank" rel="noopener">Librairie Compagnie</a></strong><br>
          58 rue des Écoles, 75005 Paris —
          <a href="https://maps.google.com/?q=58+rue+des+Ecoles,+75005+Paris" target="_blank" rel="noopener">Plan</a>
        </li>
        <li>
          <strong><a href="https://www.memorialdelashoah.org/" target="_blank" rel="noopener">Librairie du Mémorial de la Shoah</a></strong><br>
          17 rue Geoffroy l'Asnier, 75004 Paris —
          <a href="https://maps.google.com/?q=17+rue+Geoffroy+l%27Asnier,+75004+Paris" target="_blank" rel="noopener">Plan</a>
        </li>
        <li>
          <strong><a href="http://lescahiersdecolette.com/" target="_blank" rel="noopener">Les Cahiers de Colette</a></strong><br>
          23 rue Rambuteau, 75003 Paris —
          <a href="https://maps.google.com/?q=23+rue+Rambuteau,+75003+Paris" target="_blank" rel="noopener">Plan</a>
        </li>
      </ul>

      <h2>Contact</h2>
      <p>
        Association pour un Judaïsme Humaniste et Laïque (AJHL)<br>
        83, avenue d'Italie — 75013 Paris<br>
        <a href="mailto:izio.rosenman@gmail.com">izio.rosenman@gmail.com</a>
      </p>

    </div>
  </div>
</section>
"""
    return html_page(
        "À propos", content, depth=0, active_nav="about",
        description=("À propos de Plurielles, revue semestrielle de culture juive laïque fondée en 1993 "
                     "par l'AJHL. Comment se procurer la revue, librairies partenaires, contact."),
        extra_head=f'\n  <link rel="canonical" href="{_SITE_BASE_URL}/about.html">'
    )


# ─── Main Build Process ───────────────────────────────────────────────────────
def escape_html(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def build():
    print("Building Plurielles website...")

    # Setup directories
    (OUTPUT / "css").mkdir(exist_ok=True)
    (OUTPUT / "numeros").mkdir(exist_ok=True)
    (OUTPUT / "assets" / "pdfs").mkdir(parents=True, exist_ok=True)
    (OUTPUT / "comite").mkdir(exist_ok=True)

    # Write CSS
    css_path = OUTPUT / "css" / "style.css"
    css_path.write_text(CSS, encoding="utf-8")
    print("  ✓ CSS written")

    # Process issues
    all_issues = set(ISSUES.keys())

    # Copy PDFs to assets
    print("  Copying PDFs...")
    for n, pdf_src in PDF_FILES.items():
        if Path(pdf_src).exists():
            dst = OUTPUT / "assets" / "pdfs" / f"pl{n:02d}.pdf"
            if not dst.exists():
                shutil.copy2(pdf_src, dst)
                print(f"    Copied PL{n} PDF")

    # Process issues 7-22: extract from page-range PDFs
    for n in range(7, 23):
        issue_dir = ARTICLES_BY_ISSUE / f"Plurielles {n}"
        issue_out = OUTPUT / "numeros" / f"pl{n:02d}"
        articles_out = issue_out / "articles"
        issue_out.mkdir(exist_ok=True)
        articles_out.mkdir(exist_ok=True)

        info = ISSUES[n]
        print(f"  Processing issue {n}: {info['title']}")

        if issue_dir.exists():
            pdfs = sorted(p for p in issue_dir.iterdir() if p.suffix.lower() == '.pdf')
            pdf_articles = []   # articles shown in sommaire (have known metadata)
            known_articles = info.get('articles', [])

            # Precompute print-order prev/next nav for known articles
            order_key = info.get('order')
            if order_key:
                # print_slugs: article slugs in print order (only known-article indices)
                print_slugs = [
                    pdfs[j].stem.replace(' ', '-').lower()
                    for j in order_key
                    if j < len(pdfs) and j < len(known_articles)
                ]
                print_nav = {
                    slug: (
                        print_slugs[pos - 1] if pos > 0 else '',
                        print_slugs[pos + 1] if pos < len(print_slugs) - 1 else '',
                    )
                    for pos, slug in enumerate(print_slugs)
                }
            else:
                print_nav = None

            for i, pdf in enumerate(pdfs):
                clip_bottom = 0.92 if n in {12, 16, 22} else 0.86
                pages = extract_pdf_text(pdf, fix_char_spacing=(n in {9, 10, 12, 22}), clip_bottom=clip_bottom)
                if not pages:
                    continue
                # Determine metadata before stripping so we can use it as signal
                if i < len(known_articles):
                    known_author, known_title = known_articles[i]
                    title_candidate = known_title
                    author_candidate = known_author
                    include_in_sommaire = True
                else:
                    # Extra PDFs (editorial, intros, reviews beyond known articles):
                    # still generate the article page but don't list in sommaire
                    title_candidate = f"Document supplémentaire {i - len(known_articles) + 1}"
                    author_candidate = ""
                    include_in_sommaire = False

                body_html = pdf_pages_to_html(pages, title_candidate, author_candidate)

                # Generate slug from PDF filename
                slug = pdf.stem.replace(' ', '-').lower()
                article_file = f"{slug}.html"

                # Determine prev/next in print order (falls back to filename sort order)
                if print_nav and slug in print_nav:
                    prev_s, next_s = print_nav[slug]
                    prev_link = f"{prev_s}.html" if prev_s else ""
                    next_link = f"{next_s}.html" if next_s else ""
                else:
                    prev_link = f"{pdfs[i-1].stem.replace(' ', '-').lower()}.html" if i > 0 else ""
                    next_link = f"{pdfs[i+1].stem.replace(' ', '-').lower()}.html" if i < len(pdfs)-1 else ""

                # Copy article PDF to assets for per-article download link
                pdf_dst_dir = OUTPUT / "assets" / "pdfs" / "articles" / f"pl{n:02d}"
                pdf_dst_dir.mkdir(parents=True, exist_ok=True)
                pdf_dst = pdf_dst_dir / pdf.name
                if not pdf_dst.exists():
                    shutil.copy2(pdf, pdf_dst)
                pdf_url = f"../../../assets/pdfs/articles/pl{n:02d}/{pdf.name}"

                art_html = generate_article_page(
                    n, info,
                    escape_html(title_candidate),
                    escape_html(author_candidate),
                    body_html,
                    prev_link, next_link,
                    pdf_url=pdf_url,
                    article_slug=slug
                )
                (articles_out / article_file).write_text(art_html, encoding="utf-8")

                if include_in_sommaire:
                    pdf_articles.append((slug, title_candidate, author_candidate))

            # Reorder sommaire using printing order from ISSUES dict (by page number)
            order = info.get('order')
            if order:
                # 'order' maps printing position → index in string-sorted pdf_articles list.
                # Only include indices that are actually within bounds.
                pdf_articles = [pdf_articles[i] for i in order if i < len(pdf_articles)]
            else:
                # Fallback: move editorial to front
                editorial_idx = next(
                    (j for j, (_, t, _) in enumerate(pdf_articles) if 'éditorial' in t.lower()),
                    None
                )
                if editorial_idx is not None and editorial_idx > 0:
                    pdf_articles = [pdf_articles[editorial_idx]] + pdf_articles[:editorial_idx] + pdf_articles[editorial_idx+1:]

            # Generate issue index: clean sommaire using known ISSUES metadata
            articles_html = ""

            if pdf_articles:
                articles_html += f'<p class="article-list__section-header">Articles à lire en ligne ({len(pdf_articles)})</p>\n'
                articles_html += '<ul class="article-list">\n'
                for j, (slug, title, author) in enumerate(pdf_articles):
                    articles_html += f"""<li class="article-list__item">
    <a href="articles/{slug}.html" class="article-list__link">
      <span class="article-list__num">{j+1}</span>
      <div class="article-list__info">
        <div class="article-list__title">{escape_html(title)}</div>
        <div class="article-list__author">{escape_html(author) if author else ''}</div>
      </div>
      <span class="article-list__arrow">→</span>
    </a>
  </li>\n"""
                articles_html += '</ul>\n'

            info['_has_pdfs'] = bool(pdf_articles)
        else:
            articles_html = "<p style='color:var(--clr-muted)'>Numéro disponible en PDF.</p>"

        pdf_path = PDF_FILES.get(n)
        issue_html = generate_issue_page(n, info, articles_html, pdf_path)
        (issue_out / "index.html").write_text(issue_html, encoding="utf-8")
        print(f"    ✓ Issue {n} done")

    # Process issue 23: individual article PDFs
    print("  Processing issue 23 (individual articles)...")
    issue23_out = OUTPUT / "numeros" / "pl23"
    articles23_out = issue23_out / "articles"
    issue23_out.mkdir(exist_ok=True)
    articles23_out.mkdir(exist_ok=True)

    pl23_pdfs = sorted(
        p for p in ARTICLES_PL23.iterdir()
        if p.suffix.lower() == '.pdf'
        and not p.name.startswith('PL23')
        and not p.name.startswith('S23')
        and not p.name.startswith('Rachel Ertel Les vies d')
    )

    PL23_SKIP_NUMS = {0, 21, 22}  # Sommaire, Les auteurs, Sommaires précédents

    articles23 = []
    for pdf in pl23_pdfs:
        # Parse filename: "1-Author Title.pdf" or "0-PL23-Sommaire.pdf"
        name = pdf.stem
        match = re.match(r'^(\d+)-(.+)$', name)
        if not match:
            continue
        num = int(match.group(1))
        if num in PL23_SKIP_NUMS:
            continue
        rest = match.group(2)

        # Parse author/title from filename
        # Format: "Author Title" or "A.Author Title" or "I Rosenman et A Dayan Rosenman Édito"
        pages = extract_pdf_text(pdf)
        full_text = '\n\n'.join(pages)
        paragraphs = text_to_paragraphs(full_text)

        # Get title and author from filename as fallback
        parts = rest.split(' ', 2)
        if len(parts) >= 2:
            # Try to figure out where author ends and title begins
            # Usually: "LastName Title words..."
            # Or: "FirstInitial.LastName Title..."
            file_label = rest
        else:
            file_label = rest

        # Extract from PDF content for better title
        title_from_pdf = ""
        author_from_pdf = ""
        for p in paragraphs[:8]:
            p_clean = p.strip()
            if re.match(r'^Plurielles', p_clean, re.I):
                continue
            if re.match(r'^\d+$', p_clean):
                continue
            if len(p_clean) > 8 and not title_from_pdf:
                title_from_pdf = p_clean[:120]
            elif len(p_clean) > 4 and title_from_pdf and not author_from_pdf:
                author_from_pdf = p_clean[:80]
                break

        title = title_from_pdf or file_label
        author = author_from_pdf

        slug = f"article-{num:02d}"
        articles23.append((num, slug, title, author, pdf))

    articles23.sort(key=lambda x: x[0])
    ISSUES[23]['articles'] = [(a[3], a[2]) for a in articles23]

    for idx, (num, slug, title, author, pdf) in enumerate(articles23):
        # Use hardcoded metadata if available
        if num in PL23_ARTICLES:
            author, title = PL23_ARTICLES[num]

        pages = extract_pdf_text(pdf)
        body_html = pdf_pages_to_html(pages, title, author)

        prev_slug = articles23[idx-1][1] if idx > 0 else ""
        next_slug = articles23[idx+1][1] if idx < len(articles23)-1 else ""
        prev_link = f"{prev_slug}.html" if prev_slug else ""
        next_link = f"{next_slug}.html" if next_slug else ""

        art_html = generate_article_page(
            23, ISSUES[23],
            escape_html(title),
            escape_html(author),
            body_html,
            prev_link, next_link,
            article_slug=slug
        )
        (articles23_out / f"{slug}.html").write_text(art_html, encoding="utf-8")

    # Issue 23 index (use hardcoded metadata)
    articles23_list_html = f'<p class="article-list__section-header">Articles à lire en ligne ({len(articles23)})</p>\n'
    articles23_list_html += '<ul class="article-list">\n'
    for j, (num, slug, title, author, _) in enumerate(articles23):
        if num in PL23_ARTICLES:
            author, title = PL23_ARTICLES[num]
        articles23_list_html += f"""<li class="article-list__item">
    <a href="articles/{slug}.html" class="article-list__link">
      <span class="article-list__num">{j+1}</span>
      <div class="article-list__info">
        <div class="article-list__title">{escape_html(title)}</div>
        <div class="article-list__author">{escape_html(author) if author else ''}</div>
      </div>
      <span class="article-list__arrow">→</span>
    </a>
  </li>\n"""
    articles23_list_html += '</ul>'

    ISSUES[23]['_has_pdfs'] = True
    issue23_html = generate_issue_page(23, ISSUES[23], articles23_list_html, PDF_FILES.get(23))
    (issue23_out / "index.html").write_text(issue23_html, encoding="utf-8")
    print("    ✓ Issue 23 done")

    # Issues 1-6: TOC only with PDF links
    for n in range(1, 7):
        issue_out = OUTPUT / "numeros" / f"pl{n:02d}"
        issue_out.mkdir(exist_ok=True)

        info = ISSUES[n]
        print(f"  Processing issue {n}: {info['title']}")

        if n <= 5:
            note = "<p style='color:var(--clr-muted); font-family:var(--font-ui); font-size:0.9rem; margin-bottom:2rem; padding:1rem; background:#f4f0e8; border-radius:4px;'>⚠ Ce numéro est un scan — les articles ne sont pas disponibles en texte. Contactez l'AJHL pour obtenir un exemplaire.</p>"
        else:
            pdf_link = f'<a href="../../assets/pdfs/pl{n:02d}.pdf" style="color:var(--clr-primary)">Télécharger le PDF complet</a>'
            note = f"<p style='color:var(--clr-muted); font-family:var(--font-ui); font-size:0.9rem; margin-bottom:2rem; padding:1rem; background:#f4f0e8; border-radius:4px;'>Les articles de ce numéro ne sont pas encore disponibles individuellement en texte. → {pdf_link}</p>"

        articles_html = note
        articles_html += f'<p class="article-list__section-header">Index des articles du numéro</p>\n'
        articles_html += '<ul class="article-list">\n'
        if info.get('articles'):
            for j, (author, title) in enumerate(info['articles']):
                articles_html += f"""<li class="article-list__item">
    <div class="article-list__link">
      <span class="article-list__num">{j+1}</span>
      <div class="article-list__info">
        <div class="article-list__title">{escape_html(title)}</div>
        <div class="article-list__author">{escape_html(author)}</div>
      </div>
    </div>
  </li>\n"""
        articles_html += '</ul>'

        pdf_path = PDF_FILES.get(n)
        issue_html = generate_issue_page(n, info, articles_html, pdf_path)
        (issue_out / "index.html").write_text(issue_html, encoding="utf-8")

    # Issue 24: individual DOCX articles
    print("  Processing issue 24 (DOCX articles)...")
    issue24_out = OUTPUT / "numeros" / "pl24"
    articles24_out = issue24_out / "articles"
    issue24_out.mkdir(exist_ok=True)
    articles24_out.mkdir(exist_ok=True)

    D = ARTICLES_PL24_DIR   # main folder
    A = ARTICLES_PL24_ALT   # alternate folder

    def find_docx(folder, stem_prefix):
        """Glob for a DOCX whose filename starts with stem_prefix (handles encoding variants)."""
        matches = sorted(folder.glob(f"{stem_prefix}*.docx"))
        return matches[0] if matches else folder / f"{stem_prefix}.docx"

    # (slug, author, title, docx_path)
    PL24_ARTICLES_LIST = [
        ("article-01", "Izio Rosenman",
         "Éditorial — Juif visible / Juif invisible",
         D / "Izio Rosenman PL24 Edito.docx"),
        ("article-02", "Livia Parnes",
         "Le sens (impré)visible de l'invisible : le cas du marranisme portugais",
         D / "Livia Parnes. Visible-invisible.docx"),
        ("article-03", "Chantal Meyer-Plantureux",
         "Le Juif au théâtre au XIXe — La belle époque de l'antisémitisme",
         D / "Chantal Meyer-Plantureux, Le Juif au théâtre au xixème. La belle époque de l'antisémitisme.docx"),
        ("article-04", "Sylvie Lindeperg",
         "Vie et destin des « images de la Shoah » — Cécité, invisibilité, hyper-réalité",
         D / "Sylvie Lindeperg. Vie et destin des images de la Shoah.docx"),
        ("article-05", "Paul Salmona",
         "Une note de bas de page dans le « Malet et Isaac » — Invisibilité des Juifs dans l'histoire de France",
         D / "Paul Salmona. Une note de bas de page.docx"),
        ("article-06", "Lola Lafon",
         "L'ineffaçable — Sur l'invisibilisation d'Anne Frank : entretien avec Brigitte Stora",
         D / "Lola Lafon. L'ineffaçable. Entretien Avec Brigitte Stora.docx"),
        ("article-07", "Evelyn Torton Beck",
         "La politique d'invisibilisation des femmes juives dans le féminisme américain",
         D / "Evelyn Torton Beck. Invisibillité..docx"),
        ("article-08", "Emmanuel Levine",
         "Levinas et les formes de l'invisibilité juive",
         find_docx(D, "Emmanuel Levine")),
        ("article-09", "Rivon Krygier",
         "Visibilités juives — entretien avec Philippe Zard",
         D / "Ryvon Krygier. Visibilités juives. Entretien avec Philippe Zard.docx"),
        ("article-10", "Léa Veinstein",
         "Un regard sans paupière — L'invisible chez Kafka",
         D / "Léa Veinstein. Un regard sans paupière.L'invisible chez Kafka.docx"),
        ("article-11", "Cécile Rousselet",
         "L'invisibilité de l'esclave et du Juif chez André Schwarz-Bart",
         D / "Cécile Rousselet. Schwarz-Bart - Maryse Condé.docx"),
        ("article-12", "Anny Dayan Rosenman",
         "Judéités gariennes",
         A / " Anny Judéités gariennes 10 CORR IZIO.docx"),
        ("article-13", "Itzhak Goldberg",
         "On n'y voit rien — L'invisible abstrait : Kandinsky et les autres",
         D / "Itzhak Goldberg. Invisible.  2023.docx"),
        ("article-14", "Céline Masson",
         "Retrouver le nom caché",
         D / "Céline Masson. Retrouver le nom caché.docx"),
        ("article-15", "Nadine Vasseur",
         "Changement de nom",
         D / "Nadine Vasseur. Changement de nom..docx"),
        ("article-16", "Carole Ksiazenicer-Matheron",
         "Un questionnaire au temps de Vichy — Juifs visibles, juifs invisibles : une histoire de famille",
         D / "Carole Matheron. Un questionnaire au temps deVichy..docx"),
        ("article-17", "Jean-Charles Szurek",
         "Romuald Jakub Weksler-Waszkinel",
         D / "J.C. Szurek. Romuald Jakub Weksler-Waszkinel..docx"),
        ("article-18", "Simon Wuhl",
         "Universalisme juif et singularité",
         D / "Simon Wuhl. Universalisme juif et singularité .docx"),
        ("article-19", "Philippe Vellila",
         "Israël en crise",
         D / "Philippe Vellila. Israël en crise. .docx"),
    ]

    articles24 = []
    for idx, (slug, author, title, docx_path) in enumerate(PL24_ARTICLES_LIST):
        if not docx_path.exists():
            print(f"    ⚠ Missing: {docx_path.name}")
            continue
        raw_paras, fn_dict = extract_docx_text(docx_path)
        body_html = docx_paras_to_html(raw_paras, title, author, footnotes=fn_dict or None)
        prev_slug = PL24_ARTICLES_LIST[idx - 1][0] if idx > 0 else ""
        next_slug = PL24_ARTICLES_LIST[idx + 1][0] if idx < len(PL24_ARTICLES_LIST) - 1 else ""
        art_html = generate_article_page(
            24, ISSUES[24], title, author,
            body_html,
            f"{prev_slug}.html" if prev_slug else "",
            f"{next_slug}.html" if next_slug else "",
            article_slug=slug
        )
        (articles24_out / f"{slug}.html").write_text(art_html, encoding="utf-8")
        articles24.append((slug, author, title))

    ISSUES[24]['articles'] = [(a, t) for _, a, t in articles24]

    # Build a slug→index map for section rendering
    slug_to_idx = {slug: idx for idx, (slug, _, _) in enumerate(articles24)}

    articles24_list_html = f'<p class="article-list__section-header">Articles à lire en ligne ({len(articles24)})</p>\n'

    sections24 = ISSUES[24].get('sections', [(None, (0, len(articles24)))])
    art_counter = 0
    for section_name, (start, end) in sections24:
        if section_name:
            articles24_list_html += f'<p class="article-list__section-header" style="margin-top:1.5rem">{escape_html(section_name)}</p>\n'
        articles24_list_html += '<ul class="article-list">\n'
        for j in range(start, end):
            if j >= len(articles24):
                break
            slug, author, title = articles24[j]
            art_counter += 1
            articles24_list_html += f"""<li class="article-list__item">
    <a href="articles/{slug}.html" class="article-list__link">
      <span class="article-list__num">{art_counter}</span>
      <div class="article-list__info">
        <div class="article-list__title">{escape_html(title)}</div>
        <div class="article-list__author">{escape_html(author)}</div>
      </div>
      <span class="article-list__arrow">→</span>
    </a>
  </li>\n"""
        articles24_list_html += '</ul>\n'

    issue24_html = generate_issue_page(24, ISSUES[24], articles24_list_html, PDF_FILES.get(24))
    (issue24_out / "index.html").write_text(issue24_html, encoding="utf-8")

    # Issues index page
    issues_html = generate_issues_index(all_issues)
    (OUTPUT / "numeros" / "index.html").write_text(issues_html, encoding="utf-8")
    print("  ✓ Issues index done")

    # Homepage
    homepage_html = generate_homepage(all_issues)
    (OUTPUT / "index.html").write_text(homepage_html, encoding="utf-8")
    print("  ✓ Homepage done")

    # Comité de rédaction
    comite_html = generate_comite_page()
    (OUTPUT / "comite.html").write_text(comite_html, encoding="utf-8")
    print("  ✓ Comité page done")

    # About page
    about_html = generate_about_page()
    (OUTPUT / "about.html").write_text(about_html, encoding="utf-8")
    print("  ✓ About page done")

    # ── Sitemap & robots.txt ────────────────────────────────────────────────────
    print("  Generating sitemap.xml and robots.txt...")
    today = datetime.date.today().isoformat()

    # Collect all HTML files, excluding .claude / .git / worktree paths
    sitemap_urls = []
    for html_file in sorted(OUTPUT.rglob("*.html")):
        rel = html_file.relative_to(OUTPUT)
        rel_str = rel.as_posix()
        # Skip files inside hidden/internal directories or non-content pages
        if any(part.startswith('.') for part in rel.parts):
            continue
        if rel_str == "404.html":
            continue
        url = f"{_SITE_BASE_URL}/{rel_str}"
        # Assign priority based on path depth / type
        if rel_str == "index.html":
            priority = "1.0"
            changefreq = "monthly"
        elif rel_str in ("numeros/index.html", "about.html", "comite.html"):
            priority = "0.8"
            changefreq = "monthly"
        elif rel_str.endswith("/index.html"):
            priority = "0.7"
            changefreq = "yearly"
        else:
            priority = "0.5"
            changefreq = "never"
        sitemap_urls.append((url, today, changefreq, priority))

    sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url, lastmod, changefreq, priority in sitemap_urls:
        sitemap_xml += (f"  <url>\n"
                        f"    <loc>{url}</loc>\n"
                        f"    <lastmod>{lastmod}</lastmod>\n"
                        f"    <changefreq>{changefreq}</changefreq>\n"
                        f"    <priority>{priority}</priority>\n"
                        f"  </url>\n")
    sitemap_xml += '</urlset>\n'
    (OUTPUT / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8")
    print(f"    ✓ sitemap.xml ({len(sitemap_urls)} URLs)")

    robots_txt = (f"User-agent: *\n"
                  f"Allow: /\n"
                  f"Sitemap: {_SITE_BASE_URL}/sitemap.xml\n")
    (OUTPUT / "robots.txt").write_text(robots_txt, encoding="utf-8")
    print("    ✓ robots.txt")

    print("\nBuild complete!")
    print(f"Output: {OUTPUT}")
    print(f"\nTo preview: cd {OUTPUT} && python3 -m http.server 8080")


if __name__ == "__main__":
    build()
