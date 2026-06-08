#### 1) System prompt

Du bist ein hilfreicher Assistent, der die wissenschaftlichen DeLFI Publikationen (DeLFI - e-Learning Fachtagung Informatik) im Rahmen einer quantitativen Inhaltsanalyse annotiert. 
Die DeLFI Publikationen beschäftigen sich mit allen Informatik-Aspekten internet-, medien- und rechnergestützter Lehr- und Lernformen in Schule, Hochschule, beruflicher und privater Aus- und Weiterbildung.
Du MUSST IMMER mit einem gültigem JSON antworten, das genau dem vorgegebenen Schema entspricht.
Füge vor oder nach dem JSON keinen erklärenden Text ein. 

#### 2) User prompt 

Hier ist der Titel, die Autoren, das Jahr, der Abstract, der Text und das Literaturverzeichnis einer DeLFI-Publikation:

Titel: {row['title']} 

Autoren: {row['authors']}

Jahr: {row['year']}

Abstract: {row['abstract']}

Text: {row['text']}

Literaturverzeichnis: {row['references']}

Annotiere diese Publikation auf Basis des folgenden Schemas: 


In einem ersten Schritt sollen folgende Variablen annotiert werden:

1) Forschungssoftware (label_forschungssoftware): Enthält die Publikation Forschungssoftware? Forschungssoftware umfasst Quellcode-Dateien, Algorithmen, Skripte, rechnergestützte Arbeitsabläufe und ausführbare Dateien, die zu einem Forschungszweck erstellt wurden. (nein = 0, ja = 1)

2) Software Evaluation (label_software_evaluation): Wird in der Publikation die Forschungssoftware evaluiert? (nein = 0, ja = 1)

3) Lehr-Lern-Setting (label_lehr_lern_setting): Geht es um ein konkretes Lehr-Lern-Setting? (nein = 0, ja = 1)


In einem zweiten Schritt soll der Evaluationsfokus der Publikation anhand von vier Paradigmen annotiert werden: 

4) Prozessorientiertes Paradigma (label_prozess_paradigma): Wird der Lehr-Lern-Prozess durch die Forschungssoftware vereinfacht? Im Vordergrund steht hier, inwiefern die Forschungssoftware die Organisation und Gestaltung des Lehr-Lern-Settings erleichtert - etwa durch die Vereinfachung organisatorischer Abläufe, die Entlastung der Lehrenden oder die Verbesserung der Rahmenbedingungen der Lehre. Bei diesem Paradigma ist die Wirkung der Forschungssoftware auf den Lerneffekt nur mittelbar über die Organisationserleichterung von Interesse. (-1, 0, 1)

5) Lernendenorientiertes Paradigma (label_lernende_paradigma): Werden die Effekte der Forschungssoftware auf die Lernenden gemessen? Hierzu zählen kognitive Wirkungen (z.B. Wissenserwerb, Kompetenzerwerb), motivationale Wirkungen (z.B. intrinsische Motivation, Selbstwirksamkeit) sowie affektive Wirkungen (zB. Einstellungen, Zufriedenheit gegenüber dem Lerngegenstand oder der Lernsituation). (-1, 0, 1)


6) Designorientiertes Paradigma (label_design_paradigma): Steht die Entwicklung der Forschungssoftware im Vordergrund? In diesem Paradigma wird neue Forschungssoftware selbst gebaut und erfüllt Funktionen, die so zuvor noch nicht realisierbar gewesen sind. (-1, 0, 1)

7) Bildungstechnologie-Paradigma (label_bildungstechnologie_paradigma): Wird in der Publikation eine allgemeine Bildungstechnologie eingesetzt, die nicht als Forschungssoftware im Sinne von Definition 1) (label_forschungssoftware) gilt? Im Vordergrund steht hier die Anwendung von digitaler Technologie, die nicht eigens für einen konkreten Forschungszweck entwickelt wurde, sondern im Zuge einer gesellschaftlichen oder technologischen Entwicklung, zum Beispiel der Digitalisierung von Lehr-Lern-Prozessen, verfügbar geworden ist und nun in einem Bildungskontext angewendet wird. (-1, 0, 1)

Wenn ein Paradigma von den Autoren explizit verfolgt wird (z.B. Messung des Lernerfolgs) wird dieses mit 1 annotiert. Wenn ein Paradigma implizit enthalten ist oder einen geringen Stellenwert einnimmt, wird dieses mit 0 annotiert. Ist ein Paradigma nicht enthalten, wird eine -1 vergeben. Dabei wird die Qualität der unternommenen Evaluation ignoriert. Es geht nur um die intendierten Evaluationsergebnisse. 

Erkläre für jede der Annotationen kurz deine Entscheidung. 

Antworte AUSSCHLIESSLICH in diesem JSON-Format (kein anderer Text):

{
  "label_forschungssoftware": 0 oder 1,
  "label_forschungssoftware_erklärung": "kurze Erklärung",
  "label_software_evaluation": 0 oder 1,
  "label_software_evaluation_erklärung": "kurze Erklärung",
  "label_lehr_lern_setting": 0 oder 1,
  "label_lehr_lern_setting_erklärung": "kurze Erklärung",
  "label_prozess_paradigma": -1 oder 0 oder 1,
  "label_prozess_paradigma_erklärung": "kurze Erklärung",
  "label_lernende_paradigma": -1 oder 0 oder 1,
  "label_lernende_paradigma_erklärung": "kurze Erklärung",
  "label_design_paradigma": -1 oder 0 oder 1,
  "label_design_paradigma_erklärung": "kurze Erklärung",
  "label_bildungstechnologie_paradigma": -1 oder 0 oder 1,
  "label_bildungstechnologie_paradigma_erklärung": "kurze Erklärung"
}