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
            ("Claude Mossé", "Judaïsme et hellénisme"),
            ("Jacques Hassoun", "Les Juifs d'Alexandrie et le multiculturalisme"),
            ("Mireille Hadas-Lebel", "La renaissance de l'hébreu et de la conscience nationale juive"),
            ("Delphine Bechtel", "La guerre des langues entre l'hébreu et le yiddish"),
            ("Itzhok Niborski", "Le Yiddish, un passé, un présent et un futur ?"),
            ("Haïm Vidal-Sephiha", "Langue et littérature judéo-espagnoles"),
            ("Régine Robin", "La nostalgie du yiddish chez Kafka"),
            ("Henri Raczymow", "Retrouver la langue perdue. Les mots de ma tribu"),
            ("Shlomo Ben Ami", "Après les accords de Wye Plantation où va-t-on ?"),
            ("Dominique Bourel", "Moses Mendelssohn, fondateur d'un judaïsme moderne et ouvert"),
            ("Anny Dayan Rosenman", "Entendre la voix du témoin"),
        ],
    },
    8: {
        "title": "Un engagement vers les autres / Les Juifs et l'engagement politique",
        "year": "2000",
        "dossier": "Les Juifs et l'engagement politique",
        "articles": [
            ("Hubert Hannoun", "Barukh Spinoza, rebelle politique"),
            ("Henri Minczeles", "Engagement universaliste et identité nationale : le Bund"),
            ("Alain Dieckhoff", "Le sionisme : la réussite d'un projet national"),
            ("Henry Bulawko", "Bernard Lazare, le lutteur"),
            ("Jean-Charles Szurek", "En Espagne... et ailleurs"),
            ("Anny Dayan Rosenman", "Albert Cohen, un Valeureux militant"),
            ("Lucien Lazare", "La résistance juive dans sa spécificité"),
            ("Gérard Israël", "René Cassin, l'homme des droits de l'homme"),
        ],
    },
    9: {
        "title": "Les Juifs et l'Europe",
        "year": "2001",
        "dossier": "Les Juifs et l'Europe",
        "articles": [
            ("Daniel Lindenberg", "Europa Judaïca ?"),
            ("Alain Touraine", "Nous sommes tous des Juifs européens"),
            ("Michael Löwy", "La culture juive allemande entre assimilation et catastrophe"),
            ("Diana Pinto", "Vers une identité juive européenne"),
            ("Henri Minczeles", "Le concept d'extraterritorialité des Juifs en Europe médiane au XXe siècle"),
            ("Jean-Charles Szurek", "Jedwabne et la mémoire polonaise"),
            ("Daniel Oppenheim", "Dans l'après-coup de l'événement"),
        ],
    },
    10: {
        "title": "Kaléidoscope / Israël-diasporas – interrogations",
        "year": "2002",
        "dossier": "Israël-diasporas – interrogations",
        "articles": [
            ("Jacques Burko", "Je suis un Juif diasporiste"),
            ("Ilan Greilsammer", "Gauche française, gauche israélienne : regards croisés"),
            ("Jean-Charles Szurek", "Le duo Eyal Sivan et Rony Braumann"),
            ("Olivier Revault d'Allonnes", "Être Goy en diaspora"),
            ("Rachid Aous", "Laïcité et démocratie en terre d'Islam"),
            ("Françoise Carasso", "Primo Levi, le malentendu"),
        ],
    },
    11: {
        "title": "Voyages imaginaires, voyages réels",
        "year": "2003",
        "dossier": "Voyages",
        "articles": [
            ("Daniel Oppenheim", "Éthique du voyage. Rêver, partir, retrouver l'Autre, se retrouver"),
            ("Carole Ksiazenicer-Matheron", "America, America – Récits juifs du Nouveau Monde"),
            ("Marie-France Rouart", "Le Juif errant vu lui-même"),
            ("Philippe Zard", "L'Europe et les Juifs. Les généalogies spécieuses de Jean-Claude Milner"),
            ("Hélène Oppenheim-Gluckman", "Être Juif en Chine (compte rendu)"),
        ],
    },
    12: {
        "title": "Interroger, transmettre, être fidèle ou infidèle ?",
        "year": "2004",
        "dossier": "Fidélité-infidélité",
        "articles": [
            ("Daniel Lindenberg", "Le franco-judaïsme entre fidélité et infidélité"),
            ("Ariane Bendavid", "Spinoza face à sa judéité, le défi de la laïcité"),
            ("Martine Leibovici", "Mendelssohn ou la fidélité au-delà de la rationalité"),
            ("Henri Meschonnic", "Fidèle, infidèle, c'est tout comme"),
            ("Philippe Zard", "Le Commandeur aux enfers. Libres variations sur Don Juan, l'infidélité et le christianisme"),
            ("Carole Ksiazenicer-Matheron", "Isaac Bashevis Singer, la fiction de l'infidélité"),
            ("Daniel Oppenheim", "Entre tradition et subversion, la contradiction du roi des schnorrers"),
        ],
    },
    13: {
        "title": "Sortir du ressentiment ?",
        "year": "2005",
        "dossier": "Le ressentiment",
        "articles": [
            ("Catherine Chalier", "Le ressentiment de Caïn"),
            ("Rita Thalmann", "La culture du ressentiment dans l'Allemagne du IIe au IIIe Reich"),
            ("Paul Zawadski", "Temps et ressentiment"),
            ("Janine Altounian", "Ni ressentiment, ni pardon"),
            ("Michèle Fellous", "Conflits de mémoire, conflits de victimes, lutte pour la reconnaissance"),
            ("Philippe Zard", "Un étrange apôtre. Réflexions sur la question Badiou"),
        ],
    },
    14: {
        "title": "Frontières",
        "year": "2007",
        "dossier": "Frontières",
        "articles": [
            ("Emilia Ndiaye", "Frontières entre le barbare et le civilisé dans l'Antiquité"),
            ("Catherine Withol de Wenden", "Les frontières de l'Europe"),
            ("Carole Ksiazenicer-Matheron", "Frontières ashkénazes"),
            ("Riccardo Calimani", "Le ghetto – paradigme des paradoxes de l'histoire juive"),
            ("Zygmunt Bauman", "Juifs et Européens. Les anciens et les nouveaux..."),
            ("Philippe Zard", "De quelques enjeux éthiques de La Métamorphose"),
            ("Anny Dayan Rosenman", "Aux frontières de l'identité et de l'Histoire – Monsieur Klein"),
            ("Ilan Greilsammer", "Réflexions sur les futures frontières israélo-palestiniennes"),
        ],
    },
    15: {
        "title": "Les Pères Juifs",
        "year": "2009",
        "dossier": "Les Pères Juifs",
        "articles": [
            ("Jean-Charles Szurek", "La Guerre d'Espagne, mon père et moi"),
            ("Carole Ksiazenicer-Matheron", "En quête du père – devenirs de la disparition"),
            ("Anny Dayan Rosenman", "Romain Gary – au nom du père"),
            ("Pierre Pachet", "Le père juif selon Bruno Schulz"),
            ("Daniel Oppenheim", "Être fils, être père dans la Shoah et après"),
            ("Mireille Hadas-Lebel", "Mariages mixtes – matrilinéarité ou patrilinéarité"),
            ("Jean-Yves Potel", "Anna Langfus et son double"),
        ],
    },
    16: {
        "title": "Il était une fois l'Amérique – Juifs aux États-Unis",
        "year": "2010",
        "dossier": "Juifs aux États-Unis",
        "articles": [
            ("Françoise S. Ouzan", "Le judaïsme américain en question – transformations identitaires et sociales"),
            ("Carole Matheron-Ksiazenicer", "Abe Cahan, une vie en Amérique"),
            ("Hélène Oppenheim-Gluckman", "Freud et l'Amérique"),
            ("Jacques Solé", "L'apogée de la prostitution juive aux États-Unis vers 1900"),
            ("Nicole Lapierre", "L'histoire de Julius Lester"),
            ("Lewis R. Gordon", "Réflexions sur la question afro-juive"),
            ("Rachel Ertel", "Le vif saisi le mort : sur Cynthia Ozick"),
            ("Nathalie Azoulai", "La question juive dans Mad Men"),
            ("Nadine Vasseur", "Détective dans la NYPD"),
        ],
    },
    17: {
        "title": "Figures du retour – retrouver, réparer, renouer",
        "year": "2012",
        "dossier": "Figures du retour",
        "articles": [
            ("George Packer", "David Grossman, l'inconsolé"),
            ("Alain Medam", "Retours sans retours"),
            ("Philippe Zard", "De Révolution en Révélation : impasse Benny Lévy"),
            ("Gérard Haddad", "Ben Yehouda et la renaissance de l'hébreu"),
            ("Carole Ksiazenicer-Matheron", "A l'est d'Éden : nouvelles du retour et de l'oubli chez I. J. Singer"),
            ("Fleur Kuhn", "Melnitz de Charles Lewinsky ou les revenances du roman historique"),
        ],
    },
    18: {
        "title": "Que faisons-nous de notre histoire ?",
        "year": "2013",
        "dossier": "Histoire et mémoire",
        "articles": [
            ("Catherine Fhima", "Trajectoires de retour ou ré-affiliation ? Edmond Fleg et André Spire"),
            ("Martine Leibovici", "Quelques aller-retour au cœur de l'œuvre autobiographique d'Assia Djebar"),
            ("Anny Dayan Rosenman", "Primo Levi : La Trêve, un impossible retour ?"),
            ("Jean-Charles Szurek", "Le retour de Yaël Bartana en Pologne"),
            ("Martine Leibovici", "Une critique radicale du sionisme à partir de l'histoire juive diasporique ?"),
            ("Carole Ksiazenicer-Matheron", "Traduire"),
            ("Berthe Burko-Falcman", "Absence"),
        ],
    },
    19: {
        "title": "Intellectuels juifs – Itinéraires, engagements, écritures",
        "year": "2015",
        "dossier": "Intellectuels juifs",
        "articles": [
            ("Izio Rosenman", "Rabi, un intellectuel engagé"),
            ("Charles Malamud", "Pierre Vidal-Naquet"),
            ("Sandrine Szwarc", "Les colloques des intellectuels juifs"),
            ("Jean-Charles Szurek", "Enzo Traverso et Alain Finkielkraut, intellectuels nostalgiques"),
            ("Martine Leibovici", "Hannah Arendt, ni Juive d'exception, ni femme d'exception"),
            ("Daniel Oppenheim", "L'expérience de la barbarie par l'intellectuel et l'éthique du témoignage selon Jean Améry"),
            ("Michaël Löwy", "De quelques intellectuels juifs radicaux aux USA et en Europe"),
            ("Rachel Ertel", "Khurbn : l'homme chaos"),
        ],
    },
    20: {
        "title": "Dialogue",
        "year": "2016",
        "dossier": "Dialogue des religions et des cultures",
        "articles": [
            ("Franklin Rausky", "Le dialogue judéo-chrétien. Une mutation révolutionnaire"),
            ("Martine Leibovici", "Philosophie et révélation biblique selon Leo Strauss : un dialogue limité"),
            ("Joël Hubrecht", "Après un crime de masse, comment la justice peut-elle relancer le dialogue ?"),
            ("Jean-Yves Potel", "Du dialogue avec les nazis"),
            ("Hélène Oppenheim-Gluckman", "Grand-père n'était pas un nazi"),
            ("Anny Dayan Rosenman", "Répondre à la puissante voix des morts. Le dialogue dans l'œuvre d'Elie Wiesel"),
            ("Daniel Oppenheim", "Construire et habiter l'espace du dialogue et de l'hospitalité"),
            ("Brigitte Stora et Philippe Zard", "Le sujet qui fâche (entretien)"),
        ],
    },
    21: {
        "title": "La peur, hier et aujourd'hui",
        "year": "2018",
        "dossier": "La peur",
        "articles": [
            ("Russell Jacoby", "Peur et violence"),
            ("Martine Leibovici", "Peur et sentiment d'invulnérabilité dans Masse et puissance"),
            ("Delphine Horvilleur", "La peur dans la tradition juive"),
            ("Hélène Oppenheim-Gluckman", "Trauma et destructivité ?"),
            ("Daniel Oppenheim", "Peur et terreur"),
            ("Brigitte Stora", "Même pas peur ! Les chiens, les Justes et Spartacus"),
            ("Jean-Charles Szurek", "Le retour de la peur en Pologne"),
            ("Lydie Decobert", "Les ressorts de la peur dans le cinéma d'Alfred Hitchcock"),
        ],
    },
    22: {
        "title": "Le Juif et l'Autre",
        "year": "2020",
        "dossier": "Le Juif et l'Autre",
        "articles": [
            ("Mireille Hadas-Lebel", "Les juifs dans le monde hellénistique romain"),
            ("Danny Trom", "L'État-gardien, l'État de l'Autre"),
            ("François Rachline", "Juif, ou l'autre en soi"),
            ("Brigitte Stora", "Le juif et l'autre, une identité en péril"),
            ("Nadine Vasseur", "Les nôtres et les autres"),
            ("Martine Leibovici", "Entre autres. Quelques déclinaisons juives de la relation insider/outsider"),
            ("Michèle Tauber", "L'« autre » dans la littérature israélienne moderne"),
            ("Philippe Zard", "Anatomie d'un embarras. En lisant la poésie politique de Mahmoud Darwich"),
            ("Daniel Oppenheim", "Le regard sur les hommes et sur le monde d'Isaac Babel"),
            ("Simon Wuhl", "Les foyers de la haine antisémite en France"),
        ],
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
def extract_pdf_text(pdf_path):
    """Extract clean text from a PDF, clipping away headers and footers."""
    try:
        doc = fitz.open(str(pdf_path))
        pages = []
        for page in doc:
            ph = page.rect.height
            pw = page.rect.width
            # Clip away the top 11% (running headers) and bottom 14% (footers/page numbers)
            clip = fitz.Rect(0, ph * 0.11, pw, ph * 0.86)
            text = page.get_text("text", clip=clip)
            # Fix typographic ligatures → plain letters
            text = (text
                .replace('\ufb00', 'ff')
                .replace('\ufb01', 'fi')
                .replace('\ufb02', 'fl')
                .replace('\ufb03', 'ffi')
                .replace('\ufb04', 'ffl')
                .replace('\ufb05', 'st')
                .replace('\ufb06', 'st')
            )
            # Fix soft hyphenation: word- + newline + lowercase → join
            text = re.sub(r'-\n([a-zàâäéèêëîïôùûüœ])', r'\1', text)
            # Fix character-spaced words (PDF artifact where each letter is a separate object)
            # e.g. "i n c a r n e" → "incarne", "m a t e rn e l l e" → "maternelle"
            text = re.sub(
                r'(?<!\S)([A-Za-zÀ-ÿ]{1,3})( [A-Za-zÀ-ÿ]{1,3}){3,}',
                lambda m: m.group(0).replace(' ', ''),
                text
            )
            pages.append(text)
        doc.close()
        return pages
    except Exception as e:
        print(f"  Error reading {pdf_path}: {e}")
        return []


def extract_docx_text(docx_path):
    """Extract paragraph texts from a DOCX file as a list of strings."""
    _W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    try:
        with zipfile.ZipFile(str(docx_path)) as z:
            with z.open('word/document.xml') as f:
                tree = ET.parse(f)
        paras = []
        for p in tree.findall(f'.//{{{_W}}}p'):
            # Collect all text runs, including those inside hyperlinks
            text = ''.join(
                t.text or ''
                for t in p.findall(f'.//{{{_W}}}t')
            )
            paras.append(text)
        return paras
    except Exception as e:
        print(f"  Error reading {docx_path}: {e}")
        return []


def docx_paras_to_html(raw_paras):
    """Convert DOCX paragraph list to HTML, filtering boilerplate."""
    paragraphs = []
    for p in raw_paras:
        s = p.strip()
        if not s:
            continue
        # Skip very short lines (likely headers/footers/page numbers)
        if len(s) < 4:
            continue
        paragraphs.append(s)
    # Run through the same footnote pipeline as PDF articles
    return paragraphs_to_html(paragraphs)


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
        starts_new = False
        if current_words:
            actual_last = ''
            for w in reversed(current_words):
                if not (w.startswith('\x01') and w.endswith('\x02')):
                    actual_last = w
                    break
            if actual_last and actual_last[-1] in '.!?:':
                if stripped and (stripped[0].isupper() or
                                 re.match(r'^[A-ZÀ-Ö]\.?\s', stripped)):
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
# Paragraph that IS a footnote block: "N Some text..." (no dot after number = not section heading)
# Limit to footnote numbers ≤ 25 to avoid false positives with page numbers
_FN_PARA = re.compile(r'^([1-9]|1\d|2[0-5])(?!\s*[.:])\s+(?=[A-ZÀ-Û«\"\'])')
# Embedded footnote after sentence-ending punctuation or hyphen: "...word. 2 Footnote..."
# Require punctuation before the number to avoid "chapitre 3 La méthode" false positives
_FN_EMBED = re.compile(
    r'(?<=[.!?»,;\'\"\)\-])\s+([1-9]|1\d|2[0-5])\s+(?=[A-ZÀ-Û«\"\'])'
)
# Inline footnote ref in body: word-char immediately followed by single digit
_FN_REF = re.compile(r'(?<=[a-zA-ZàâäéèêëîïôùûüœÀ-ÿ])([1-9])(?=[\s,;.!?»\'\")\]]|$)')


def _split_fn_block(text):
    """Parse a string of one or more footnotes into {num: text} dict."""
    # Split at boundaries like "...sentence end. 2 Next footnote"
    parts = re.split(r'(?<=[.!?»\'\")\]])\s+(?=\d{1,2}\s+[A-ZÀ-Û«\"\'])', text)
    result = {}
    for part in parts:
        m = re.match(r'^(\d{1,2})\s+(.+)', part, re.DOTALL)
        if m:
            result[int(m.group(1))] = m.group(2).strip()
    return result


def detect_footnotes(paragraphs):
    """
    Scan paragraphs for footnote text and inline markers.
    Returns (body_paragraphs, footnotes_dict) where body_paragraphs still contain
    \x01N\x02 tokens at reference positions, and footnotes_dict maps int→str.
    """
    body = []
    footnotes = {}

    for para in paragraphs:
        # Case 1: whole paragraph is footnote text
        if _FN_PARA.match(para) and len(para) > 25:
            footnotes.update(_split_fn_block(para))
            continue

        # Case 2: paragraph contains \x01N\x02 tokens from isolated digit lines
        if _FN_TOK.search(para):
            # Walk through chunks: [text, fn_num, text, fn_num, text, ...]
            chunks = _FN_TOK.split(para)
            body_buf = chunks[0]
            i = 1
            while i < len(chunks):
                fn_num = int(chunks[i])
                after = chunks[i + 1] if i + 1 < len(chunks) else ''
                after_stripped = after.lstrip()
                # Is what follows footnote text (starts with capital) or body continuation?
                if after_stripped and after_stripped[0].isupper() and len(after_stripped) > 20:
                    # Footnote starts here — save body up to this point with ref marker
                    body_buf = body_buf.rstrip() + f'\x01{fn_num}\x02'
                    # Parse footnote text (may contain further tokens/footnotes)
                    fn_raw = str(fn_num) + ' ' + after_stripped
                    footnotes.update(_split_fn_block(fn_raw))
                    body_buf_remaining = ''
                    i += 2
                    # Absorb any remaining chunks as more footnote text
                    while i < len(chunks):
                        fn_num2 = int(chunks[i])
                        after2 = chunks[i + 1] if i + 1 < len(chunks) else ''
                        after2s = after2.lstrip()
                        fn_raw2 = str(fn_num2) + ' ' + after2s
                        footnotes.update(_split_fn_block(fn_raw2))
                        i += 2
                    break
                else:
                    # Inline reference only — keep token in body text
                    body_buf += f'\x01{fn_num}\x02' + after
                    i += 2

            if body_buf.strip():
                body.append(body_buf.strip())
            continue

        # Case 3: embedded footnote text with no token (number ran together with prev line)
        m = _FN_EMBED.search(para)
        if m:
            body_part = para[:m.start()].strip()
            fn_num_str = m.group(1)
            fn_part = para[m.start():].strip()  # "N Footnote text..."
            if body_part:
                body.append(body_part)
            if fn_part:
                footnotes.update(_split_fn_block(fn_part))
            continue

        body.append(para)

    return body, footnotes


def paragraphs_to_html(paragraphs):
    """Convert list of paragraphs to HTML, extracting and linking footnotes."""
    body_paras, footnotes = detect_footnotes(paragraphs)

    # Track which ref IDs have been used (first occurrence gets the anchor, rest are plain links)
    used_ref_ids = set()

    def make_sup(n):
        ref_id = f'ref-{n}'
        id_attr = f' id="{ref_id}"' if ref_id not in used_ref_ids else ''
        used_ref_ids.add(ref_id)
        return f'<sup class="fn-ref"{id_attr}><a href="#fn-{n}">{n}</a></sup>'

    def render_para(p):
        # Escape HTML first (tokens are not HTML-special chars)
        p = p.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        # Replace \x01N\x02 tokens with <sup> links
        p = _FN_TOK.sub(lambda m: make_sup(int(m.group(1))), p)
        # Also catch inline refs (digit attached to word) for known footnotes
        def sub_ref(m):
            n = int(m.group(1))
            if n in footnotes:
                return make_sup(n)
            return m.group(0)
        p = _FN_REF.sub(sub_ref, p)
        return f'<p>{p}</p>'

    html_parts = [render_para(p) for p in body_paras if p]

    if footnotes:
        html_parts.append('<hr class="fn-rule">')
        html_parts.append('<ol class="footnotes">')
        for n in sorted(footnotes.keys()):
            text = (footnotes[n]
                    .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
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
def html_page(title, content, depth=0, active_nav=""):
    # Keep title short for browser tab
    title = title[:80] if len(title) > 80 else title
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
  <meta name="description" content="Plurielles, revue de culture juive laïque et humaniste">
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
"""
    return html_page("Accueil", content, depth=0, active_nav="")


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
    return html_page("Tous les numéros", content, depth=1, active_nav="numeros")


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
    return html_page(f"N° {n} — {info['title']}", content, depth=2, active_nav="numeros")


def generate_article_page(n, issue_info, title, author, body_html, prev_link="", next_link=""):
    nav = ""
    if prev_link or next_link:
        nav = f"""<div class="article-nav">
    {'<a href="' + prev_link + '">← Article précédent</a>' if prev_link else ''}
    {'<span class="article-nav__sep">·</span>' if prev_link and next_link else ''}
    {'<a href="' + next_link + '">Article suivant →</a>' if next_link else ''}
    <span style="flex:1"></span>
    <a href="../index.html">Retour au numéro {n}</a>
  </div>"""

    content = f"""
{breadcrumb(("Accueil", "../../../index.html"), ("Numéros", "../../index.html"), (f"N° {n}", "../index.html"), (title[:50], None))}

<div class="article-header">
  <div class="article-header__inner">
    <a href="../index.html" class="article-header__issue">← Plurielles N° {n} — {issue_info['year']}</a>
    <h1 class="article-header__title">{title}</h1>
    <p class="article-header__author">{author}</p>
  </div>
</div>

<div class="article-body">
  {body_html}
  {nav}
</div>
"""
    return html_page(f"{title} — N° {n}", content, depth=3, active_nav="numeros")


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
            photo_html = f'<img src="{photo}" alt="{member["name"]}" class="team-card__photo">'
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
    return html_page("Comité de rédaction", content, depth=0, active_nav="comite")


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
    return html_page("À propos", content, depth=0, active_nav="about")


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

            for i, pdf in enumerate(pdfs):
                pages = extract_pdf_text(pdf)
                if not pages:
                    continue
                full_text = '\n\n'.join(pages)
                paragraphs = text_to_paragraphs(full_text)
                body_html = paragraphs_to_html(paragraphs)

                # Use authoritative metadata from ISSUES dict when available
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

                # Generate slug from PDF filename
                slug = pdf.stem.replace(' ', '-').lower()
                article_file = f"{slug}.html"

                # Determine prev/next among sommaire-listed articles only
                prev_link = f"{pdfs[i-1].stem.replace(' ', '-').lower()}.html" if i > 0 else ""
                next_link = f"{pdfs[i+1].stem.replace(' ', '-').lower()}.html" if i < len(pdfs)-1 else ""

                art_html = generate_article_page(
                    n, info,
                    escape_html(title_candidate),
                    escape_html(author_candidate),
                    body_html,
                    prev_link, next_link
                )
                (articles_out / article_file).write_text(art_html, encoding="utf-8")

                if include_in_sommaire:
                    pdf_articles.append((slug, title_candidate, author_candidate))

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
        full_text = '\n\n'.join(pages)
        paragraphs = text_to_paragraphs(full_text)
        body_html = paragraphs_to_html(paragraphs)

        prev_slug = articles23[idx-1][1] if idx > 0 else ""
        next_slug = articles23[idx+1][1] if idx < len(articles23)-1 else ""
        prev_link = f"{prev_slug}.html" if prev_slug else ""
        next_link = f"{next_slug}.html" if next_slug else ""

        art_html = generate_article_page(
            23, ISSUES[23],
            escape_html(title),
            escape_html(author),
            body_html,
            prev_link, next_link
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
        raw_paras = extract_docx_text(docx_path)
        body_html = docx_paras_to_html(raw_paras)
        prev_slug = PL24_ARTICLES_LIST[idx - 1][0] if idx > 0 else ""
        next_slug = PL24_ARTICLES_LIST[idx + 1][0] if idx < len(PL24_ARTICLES_LIST) - 1 else ""
        art_html = generate_article_page(
            24, ISSUES[24], title, author,
            body_html,
            f"{prev_slug}.html" if prev_slug else "",
            f"{next_slug}.html" if next_slug else "",
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

    print("\nBuild complete!")
    print(f"Output: {OUTPUT}")
    print(f"\nTo preview: cd {OUTPUT} && python3 -m http.server 8080")


if __name__ == "__main__":
    build()
