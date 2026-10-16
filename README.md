# EduAI Audit

Research prototype for auditing university dropout risk predictions. The project examines who is selected for review, which observed positive cases are found or missed, and how errors vary across student groups and review capacities.

**Current stage:** a working Google Colab prototype. The audit accepts existing predicted probabilities and observed outcomes. Earlier notebook sections train baseline models to produce example predictions; the audit functions themselves do not train a model.

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

## Next steps

- Move the reusable audit functions into an application and build a file-upload, configuration, and report interface.
- Develop a separate audit mode for cases where observed outcomes are unavailable.
- Explore AI-assisted explanations grounded in the calculated results.

The current prototype uses deterministic calculations and rule-based report findings; AI-generated explanations are not implemented.

