# EduAI Audit

[Русская инструкция](docs/README.ru.md)

Research prototype for auditing university dropout risk predictions. The project examines who is selected for review, which observed positive cases are found or missed, and how errors vary across student groups and review capacities.

**Current stage:** a working Google Colab research prototype and a bilingual local audit app. The app accepts existing predicted probabilities and observed outcomes. Earlier notebook sections train baseline models to produce example predictions; the audit app does not train a model.

## Run the local audit app

Use Python 3.11 or newer. On Windows, from this repository folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the local address shown by Streamlit. The workflow is: upload one CSV of
existing positive-outcome probabilities and observed outcomes, map outcomes and
decision keys, choose groups and review shares, run the audit, then download a
standalone HTML report. The app runs locally and does not call an AI service.

After installing the dependencies, double-click `start_app.bat` on Windows. It
starts a background server, waits for it to be ready, and opens the browser. If
the server is already running, it opens the existing app. Startup errors are
saved to `.venv/eduai-app.log`. Closing the browser does not stop the background
server; it ends when Windows shuts down.

A desktop shortcut can point to `.venv\Scripts\pythonw.exe` with the full path to
`launch_app.py` as its quoted argument and this repository as its working directory.
This shortcut uses the current local installation; it is not a standalone executable.
To start with terminal output, use the Streamlit command above.

For the self-contained Windows installer and portable build, see
[packaging/README.md](packaging/README.md). Installed builds open the browser
interface on port 8502 and include Python and the runtime dependencies.

For a first try, click **Try example**, then **Run audit**. The app loads artificial
data and complete settings without a file upload, with review shares 15%, 20%,
and 30% and a 20% report focus. **Try comparison example** loads two predictions.
**Use my CSV**, or uploading a new file, returns to your own data and clears the
example results. Example settings are separate from uploaded-file settings.

You can also upload [examples/sample_predictions.csv](examples/sample_predictions.csv)
and select the **Synthetic example** preset. It fills `outcome` as the outcome column,
`dropout_probability` as the score, `Dropout` as positive, `Graduate` as negative,
`Enrolled` as excluded, `student_id` as decision key and student ID, and `study_mode`
as a group. Review or edit any field before running the audit.
The file is synthetic demonstration data, not a research result.

### Language, presets, and results

- Select **English** or **Русский** at the top. Labels, explanations, findings,
  tables, charts, and the downloadable report use that language. Switching language
  keeps the uploaded file, configured values, and completed audit; calculations
  are not repeated. Metric names stay in English in both languages. Hover over
  their help icons for definitions in the selected language. Source column names
  and outcome codes stay unchanged.
- Presets for **UPV 2022**, **OULAD**, and **UCI** fill the notebook's mappings when
  the corresponding columns and values are present. Defaults remain editable.
  Presets do not aggregate raw records, fit a model, or manufacture probabilities.
- Settings use selection lists with typing disabled. Choose review shares from
  1% to 100% in whole percentage points. The dataset name comes from the filename
  or preset; optional timing and outcome periods use a fixed list with an
  explicit unspecified option.
- Charts show existing counts, recall, precision, and false-positive rate across
  the declared review shares. Hover for values. Tables retain individual intervals
  and support notes. The downloaded HTML includes offline SVG charts.
- The decision key identifies one decision, possibly using several columns. The
  optional student ID identifies repeated records from the same person. A reference
  group is the baseline for **other group minus reference**; choosing it changes
  signed comparisons, not ranking or group metrics.
- Before running, a population summary shows input, excluded and audited records,
  positive and negative outcomes, distinct supplied student IDs, and missing group
  values after exclusions. It uses the notebook's input checks without calculating
  rankings or intervals.
- The group view plots Recall and FPR at the focus share with the existing
  individual confidence intervals. Hover for denominators, interval status and
  support notes. Undefined metrics are labelled; unavailable intervals are omitted.
  Offline group plots for every configured feature are included in the HTML report.
- **Save settings JSON** downloads a versioned mapping, CSV parser options, outcome
  rules, groups, references, shares, and context. Upload it under **Load saved
  settings**, then select **Apply settings**. The current CSV is checked before any
  widget is changed. Missing columns or incompatible data leave the current settings
  intact. No student rows, predictions, or audit results are saved in this profile.
- Export one aggregate table as CSV or all six tables in a ZIP. Exports cover every
  declared share, keep numeric precision and source/status codes, and use UTF-8 with
  BOM. Numeric missing values stay empty. The ZIP manifest describes the scope;
  consult the HTML report for assumptions and limitations.

An original dataset CSV usually has outcomes and features but no model predictions.
If the expected score column is missing, the app explains what to upload and shows
an export cell for PROTOTYPE. See [Export ready predictions](docs/EXPORT_PREDICTIONS.md)
for the exact schemas and notebook export instructions.

The CSV must have one row per declared decision, a finite probability in `[0, 1]`
for the positive outcome, and a known observed outcome on every row. Declare all
outcome values as positive, negative, or excluded. Excluded rows are counted but
do not enter the ranking or metrics. The decision key must be unique across the
whole uploaded batch. When no decision ID exists, the interface lets you
explicitly use the source row number as a technical key; that cannot verify real
student identity or detect duplicate students. For repeated enrollments or
periods, supply a student ID to account for clustering in uncertainty intervals.
CSV fields are initially read as text to preserve IDs and outcome codes such as
`001`; the selected score column is then validated and converted to probability.

Prediction timing and outcome horizon can be recorded in the report, but the app
cannot verify either. The report compares declared capacities; it does not choose
an optimal one or make an automatic fairness verdict. Auditing without observed
outcomes and AI-generated explanations are outside this app version.

The audit functions in `eduai_prediction_audit.py`, `eduai_validated_audit.py`,
`eduai_uncertainty.py`, `eduai_review_shares.py`, and `eduai_report.py` match the
final function definitions in `eduai_PROTOTYPE.ipynb`. The app calls the validated
capacity comparison and report builder rather than the notebook's training code.
`eduai_report_locale.py` formats the existing results in Russian;
`eduai_charts.py` plots existing capacity results. Neither reruns the audit.

Run the focused tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

### Compare two prediction columns

Upload one CSV containing outcomes, decision keys and two existing probability
columns. Both columns must refer to the same positive event, prediction time and
outcome horizon. Enable **Compare two prediction columns**, then select Model A
and Model B columns. A single mapping, outcome exclusion rule and review share
apply to both models. Every submitted score is validated, including excluded rows.

The comparison shows each model's counts, Recall, Precision and FPR, observed
differences **B minus A**, overlap (**both / only A / only B / neither**) and group
results. Overlap counts decision records; multiple course records may belong to
one student. Equal scores keep the original CSV order. The record inspector
shows supplied keys, source data-row numbers, scores and outcomes at the focus
share. Its separate CSV download includes those decision records; the comparison
ZIP contains aggregate tables and both individual audits' tables.

Individual model intervals retain the notebook's assumptions. Model differences
are descriptive counts and percentage-point differences, with no paired intervals
or significance test and no automatic model recommendation. The HTML report
includes aggregate comparisons and both full individual audit reports. Settings
JSON version 2 stores the second column; version 1 single-model profiles still load.

For a synthetic demonstration, click **Try comparison example**, then **Run audit**.
At the 20% focus, each model selects 4 of 16 audited records: A finds 2 positive
cases with 2 false alarms; B finds 4 positive cases with no false alarms. Two
records are selected by both, two only by A, and two only by B. Alternatively,
download **two-model sample CSV**, upload it, select **Synthetic example**, enable
comparison, and choose `dropout_probability_b` for B.
These are illustrative probabilities, not a newly trained model or research result.

## Notebooks

| Notebook | Purpose |
| --- | --- |
| [eduai_EDA.ipynb](eduai_EDA.ipynb) | Initial exploration of OULAD data. |
| [eduai_ML.ipynb](eduai_ML.ipynb) | Baseline modelling, initial group audits, and calibration analysis. |
| [eduai_VALIDATION.ipynb](eduai_VALIDATION.ipynb) | Group-aware validation and comparisons of review scenarios. |
| [eduai_PROTOTYPE.ipynb](eduai_PROTOTYPE.ipynb) | Reusable prediction audit, input validation, uncertainty intervals, capacity comparisons, and consolidated reports. |

Read the notebooks in this order to follow the development. **PROTOTYPE can be run independently:** it contains its own functions, data preparation, and example model training.

[Open PROTOTYPE in Colab](https://colab.research.google.com/github/egor32055/EduAI-Audit/blob/main/eduai_PROTOTYPE.ipynb)

## What the prototype does

- Requires explicit positive, negative, and excluded outcome mappings.
- Checks decision keys, missing outcomes, duplicate decisions, and finite probabilities in `[0, 1]`.
- Reports exclusions before calculating metrics.
- Ranks existing scores and compares configurable review shares; the current examples use 15%, 20%, and 30%.
- Reports selection counts, found and missed positive cases, false alarms, precision, recall, and false-positive rate.
- Calculates group metrics and individual confidence intervals, with support notes and unavailable intervals where appropriate.
- Builds readable HTML reports from existing audit results.

The main functions are defined inside the notebook: `audit_validated_predictions`, `audit_review_shares`, and `build_audit_report`.

## Data and units of analysis

| Dataset | Decision unit | Positive outcome | Final observed-outcome audit |
| --- | --- | --- | --- |
| OULAD, Open University | Course enrollment | `Withdrawn` | `Pass`, `Fail`, and `Distinction` are negative outcomes. One student can have several enrollments. |
| UPV, Universitat Politecnica de Valencia | Student after checking and aggregating course rows | `A` in `abandono_hash` | `B` is negative. The notebook includes 2022 experiments and 2018/2021 year checks. |
| UCI, Portuguese higher education dataset | Student, assuming one student per source row | `Dropout` | `Graduate` is negative; `Enrolled` is explicitly excluded. The public file has no real student identifier. |

UCI is the repository hosting the Portuguese dataset. Course withdrawal in OULAD and university dropout in the other datasets are different events.

Sources and documentation:

- [OULAD](https://analyse.kmi.open.ac.uk/open_dataset) — selected files are already in [OULAD_data/](OULAD_data/).
- [UPV archive on Zenodo](https://zenodo.org/records/17239943) — the notebook downloads the required yearly archives.
- [UCI: Predict Students' Dropout and Academic Success](https://archive.ics.uci.edu/dataset/697/predict%2Bstudents%2Bdropout%2Band%2Bacademic%2Bsuccess) — downloaded by the notebook.

Consult the original sources for dataset definitions and reuse terms. UPV and UCI files do not need to be uploaded separately to this repository to run the current prototype.

## Run PROTOTYPE in Google Colab

1. Open the notebook using the Colab link above.
2. Place [OULAD_data/studentInfo.csv](OULAD_data/studentInfo.csv) in your Google Drive at `MyDrive/eduai-audit/data/studentInfo.csv`, or change `data_path` in the loading cell to your actual Drive path.
3. Use a Python runtime. The notebook uses NumPy, pandas, scikit-learn, requests, and IPython, as well as the Colab Drive integration.
4. Restart the Python session and run all cells from top to bottom. Authorize the Drive mount if Colab requests it.
5. Allow the UPV downloads and repeated model experiments to finish. Internet access is required.
6. Read the final **Consolidated audit report** section.

All three final reports are retained in `audit_reports`. Set `report_dataset_to_view` to `'OULAD'`, `'UPV 2022'`, or `'UCI'` to choose the displayed report. Set `report_focus_share` to one of the computed shares to choose the group details, then rerun the report assembly cell. Change `review_shares_to_check` and rerun the capacity comparison and report assembly to compare other capacities.

Review capacity is rounded upward after outcome exclusions. Equal scores follow original input row order. OULAD capacity is measured in enrollments; unique students are also counted.

### Verified run

On 16 October 2026, PROTOTYPE was run from top to bottom after restarting the Colab Python session, with the Drive data already available. The exported notebook contains 58 cells, saved outputs, and no error outputs. Its internal checks confirmed agreement between direct and model-backed audits, expected rejection of six invalid-input scenarios, a hand-calculated example, and agreement of the capacity and report results.

At the current 20% review share, the final audits contain:

| Dataset | Audited Records | Selected Records | Found Cases | Missed Cases | False Alarms |
| --- | ---: | ---: | ---: | ---: | ---: |
| OULAD | 6 538 | 1 308 | 642 | 1 370 | 666 |
| UPV 2022 | 4 086 | 818 | 133 | 159 | 685 |
| UCI | 717 | 144 | 117 | 157 | 27 |

These are retrospective results on the notebook's held-out cohorts. UCI excludes 168 unresolved `Enrolled` records before its final audit. Earlier exploratory UCI sections use a different binary mapping; the explicit validated entry defines the final audit population.

## Interpretation and limits

One independent record per student uses Wilson intervals; repeated enrollments use 2,000 whole-student bootstrap resamples. Group differences use Newcombe intervals or shared student bootstrap draws, as appropriate.

Intervals are conditional on fixed predictions and selection flags. They do not include model refitting, re-ranking, future-year drift, or simultaneous coverage across multiple comparisons. Small or sparse groups are flagged; some intervals are unavailable.

Group differences are descriptive findings, not automatic discrimination or causality verdicts. An interval containing zero does not establish equal performance. The prototype does not select an optimal review capacity. Input checks cannot verify real student identity, prediction timing, or outcome definitions; missing timing and horizon remain visible in reports.

Methods: [NIST Wilson intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm), [Newcombe intervals](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.confint_proportions_2indep.html), and [Cameron and Miller (2015), cluster inference](https://cameron.econ.ucdavis.edu/research/Cameron_Miller_JHR_2015.pdf).

## Planned separately

- Develop a separate audit mode for cases where observed outcomes are unavailable.
- Explore AI-assisted explanations grounded in the calculated results.

The current prototype uses deterministic calculations and rule-based report findings; AI-generated explanations are not implemented.

