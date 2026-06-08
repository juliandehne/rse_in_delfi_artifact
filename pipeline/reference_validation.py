"""
reference_validation.py

External validation of the final aggregated labels against the 2017 reference
study (27 papers from 2014–2016, human-annotated). Ported from the source
``label_aggregation_inter_LLM.py`` (part 5), paths rewired to ``data/``.

Reference papers have no metadata page numbers, so they are matched to the final
dataframe by title (exact → case-insensitive → fuzzy).
"""

from __future__ import annotations

import warnings
from difflib import get_close_matches

import numpy as np
import pandas as pd
import krippendorff
from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa

from pipeline import config
from pipeline.step5_label_aggregation import gwet_ac1_binary

# (DelFI Band, Beitragstitelseite) -> title, to match the metadata-less reference rows.
TITLE_MAPPING = {
    (2014, 109): "ScratchDrone – Systematische Programmierung von Flugdrohnen für den Informatikunterricht",
    (2014, 133): "Moodle-Plug-in zur Analyse und Kennzeichnung der Barrierefreiheit von PDF-Dokumenten",
    (2014, 145): "Automatische Generierung von Übungsgruppen auf Basis der Nutzung von Online-Ressourcen",
    (2014, 193): "WARP – ein Trainingssystem für UML-Aktivitätsdiagramme mit mehrschichtigem Feedback",
    (2014, 217): "Erfahrungen mit mobile Learning in der Hochschullehre – Vergleich zwischen Massenveranstaltung und Seminar",
    (2014, 259): "ÜPS – Ein autorenfreundliches Trainingssystem für SQLAnfragen",
    (2014, 301): "Die Evaluation generischer Einbettung automatisierter Programmbewertung am Beispiel von Moodle und aSQLg",
    (2015, 81): "Mobil in und aus Situationen lernen: Erste Erfahrungen zum Studieneinstieg von Studierenden verschiedener Fachrichtungen",
    (2015, 107): "Zirkus Empathico: Eine mobile Applikation zum Training sozioemotionaler Kompetenzen bei Kindern imA utismus-Spektrum",
    (2015, 119): "5Code– Eine integrierte Entwicklungsumgebung für Programmieranfänger",
    (2015, 131): "Adaptive Lehrvideos",
    (2015, 183): "CrumbIT! – Community-basierte Lernpfade durch den Online-Wissensdschungel",
    (2015, 241): "Die Erweiterung von Lernräumen durch Augmented Reality am Beispiel des Social Augmented Learning",
    (2015, 265): "Ein Online-System zur Regionalisierung der Fahrschulausbildung",
    (2015, 277): "Multitouch-Pursuit – Ein generisches Lernspiel für Tischcomputer",
    (2016, 23): "Interest-based Recommendation in Academic Networks using Social Network Analysis",
    (2016, 35): "Adaption und Evaluation eines virtuellen Klassenzimmers für Blinde",
    (2016, 59): "Das erste Semester von Studierenden der Wirtschafts- und Sozialwissenschaften im Spiegel der Reflect-App",
    (2016, 83): "ConceptCloud: Supporting Reflection in the Online Learning Environment Go-Lab",
    (2016, 93): "Design eines Spiels zum Lernen von Informationskompetenz",
    (2016, 107): "Das Technologieakzeptanzmodell für kartenbasierte Lernspiele in der Bildauswertung",
    (2016, 155): "Ein Autorensystem zur Erstellung von adaptiven mobilen Mikrolernanwendungen",
    (2016, 179): "HardDriveExchange– Eine VR-Lernanwendung zur Durchführung von Festplattenwechseln in Speichersystemen",
    (2016, 192): "Elektronische Abstimmungssysteme in der Hochschullehre–Empirische Untersuchung zu ersten Erfahrungen mit dem Audience Response System eduVote",
    (2016, 203): "Evaluation automatisierter Ansätze für die Bewertung von Modellierungsaufgaben",
    (2016, 233): "MoodlePeers: Automatisierte Lerngruppenbildung auf Grundlage psychologischer Merkmalsausprägungen in E-Learning-Systemen",
    (2016, 257): "Anforderungen und ein Rahmenkonzept für inklusive E-Learning Software",
}

REFERENCE_COL_MAPPING = {
    "Einzelne Software":            "label_forschungssoftware",
    "Evaluation durchgeführt":      "label_software_evaluation",
    "Lehr-Lernsetting":             "label_lehr_lern_setting",
    "Fokus Medialität":             "label_prozess_paradigma",
    "Fokus Akzeptanz":              "label_bildungstechnologie_paradigma",
    "Fokus Innovation":             "label_design_paradigma",
    "Fokus Empirischer Lernerfolg": "label_lernende_paradigma",
}


def load_reference_data() -> pd.DataFrame:
    df = pd.read_excel(config.REFERENCE_EXCEL)
    df = df[(df["Evaluation durchgeführt"] == 1) &
            (df["Einzelne Software"] == 1) &
            (df["Lehr-Lernsetting"] == 1)].copy()
    df["title"] = df.apply(
        lambda r: TITLE_MAPPING.get((r["DelFI Band"], r["Beitragstitelseite"])), axis=1)
    unnamed = [c for c in df.columns if c.startswith("Unnamed:")]
    df = df.dropna(subset=["title"]).drop(columns=unnamed).reset_index(drop=True)
    df = df.rename(columns=REFERENCE_COL_MAPPING)
    print(f"  Reference study loaded: {len(df)} papers.")
    return df


def _find(title, df, cutoff=0.85):
    exact = df[df["title"] == title]
    if not exact.empty:
        return exact
    ci = df[df["title"].str.lower() == title.lower()]
    if not ci.empty:
        return ci
    m = get_close_matches(title, df["title"].dropna().tolist(), n=1, cutoff=cutoff)
    return df[df["title"] == m[0]] if m else pd.DataFrame()


def validate_against_reference(df_final: pd.DataFrame) -> pd.DataFrame:
    df_ref = load_reference_data()
    ids = []
    for title in df_ref["title"]:
        hit = _find(title, df_final)
        if hit.empty:
            raise ValueError(f"Could not match reference title: {title!r}")
        ids.append(int(hit["id"].iloc[0]))
    df_ref = df_ref.copy()
    df_ref["id"] = ids
    df_ref = df_ref.sort_values("id").reset_index(drop=True)
    df_sub = df_final[df_final["id"].isin(ids)].sort_values("id").reset_index(drop=True)
    assert list(df_ref["id"]) == list(df_sub["id"]), "ID mismatch after alignment!"

    rows = []
    for col in config.BINARY_COLS:
        arrs = [df_ref[col].to_numpy(), df_sub[f"{col}_final"].to_numpy()]
        try:
            alpha = krippendorff.alpha(np.array(arrs), level_of_measurement="nominal")
        except ValueError:
            alpha = 1.0
        table, _ = aggregate_raters(np.column_stack(arrs))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            fk = fleiss_kappa(table)
        if np.isnan(fk):
            fk = 1.0
        rows.append({"label": col, "type": "binary", "krippendorff_alpha": round(alpha, 2),
                     "fleiss_kappa": round(fk, 2), "gwet_ac1": round(gwet_ac1_binary(arrs), 2)})
    df_icr = pd.DataFrame(rows)
    summary = pd.DataFrame([{
        "label": "Average (binary)", "type": "",
        "krippendorff_alpha": round(df_icr["krippendorff_alpha"].mean(), 2),
        "fleiss_kappa": round(df_icr["fleiss_kappa"].mean(), 3),
        "gwet_ac1": round(df_icr["gwet_ac1"].mean(), 2)}])
    df_icr = pd.concat([df_icr, summary], ignore_index=True)
    out = config.INTER_DIR / "icr_replication_prompt_template_1_reference_study.csv"
    df_icr.to_csv(out, index=False)
    print(f"  Reference validation ({len(df_ref)} papers) → {out.name}")
    print(df_icr.to_string(index=False))
    return df_icr
