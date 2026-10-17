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

After installing the dependencies, you can also double-click `start_app.bat` on
Windows. Keep its terminal window open while using the app; closing it stops the
local server. The address `http://127.0.0.1:8501` is available only while the server
is running. To start it from the PyCharm terminal, use the last command above.

For a first try, upload [examples/sample_predictions.csv](examples/sample_predictions.csv).
Select the **Synthetic example** preset. It fills `outcome` as the outcome column,
`dropout_probability` as the score, `Dropout` as positive, `Graduate` as negative,
`Enrolled` as excluded, `student_id` as decision key and student ID, and `study_mode`
as a group. Review or edit any field before running the audit.
The file is synthetic demonstration data, not a research result.

### Language, presets, and results

- Select **English** or **Русский** at the top. Labels, explanations, findings,
  tables, charts, and the downloadable report use that language. Switching language
  keeps the uploaded file, configured values, and completed audit; calculations
  are not repeated. Source column names, outcome codes, and supplied context stay
  unchanged.
- Presets for **UPV 2022**, **OULAD**, and **UCI** fill the notebook's mappings when
  the corresponding columns and values are present. Defaults remain editable.
  Presets do not aggregate raw records, fit a model, or manufacture probabilities.
- Charts show existing counts, recall, precision, and false-positive rate across
  the declared review shares. Hover for values. Tables retain individual intervals
  and support notes. The downloaded HTML includes offline SVG charts.
- The decision key identifies one decision, possibly using several columns. The
  optional student ID identifies repeated records from the same person. A reference
  group is the baseline for **other group minus reference**; choosing it changes
  signed comparisons, not ranking or group metrics.

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

