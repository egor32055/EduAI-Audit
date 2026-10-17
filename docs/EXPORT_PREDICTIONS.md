# Export ready predictions / Выгрузка готовых прогнозов

The original source datasets contain observed outcomes and features. A score
column is created by a model outside the audit app. Do not use a grade, outcome,
or arbitrary numeric feature as a prediction probability.

Исходные датасеты содержат исходы и признаки. Столбец прогноза создаёт модель
отдельно от приложения аудита. Оценка по предмету, код исхода или произвольный
числовой признак не заменяют готовую вероятность.

## Export from PROTOTYPE in Colab

After the **Input validation for observed-outcome audits** section has completed,
the `validated_predictions` dictionary contains the held-out scored tables.
Choose a dataset and run this extra cell. It exports existing scores without
fitting another model or changing their order.

После выполнения раздела **Input validation for observed-outcome audits** в
`validated_predictions` находятся проверочные таблицы с прогнозами. Выберите
датасет и выполните дополнительную ячейку. Она не обучает новую модель и не меняет
порядок строк.

```python
from google.colab import files

dataset_to_export = "UPV 2022"  # or "OULAD", "UCI"
filename = "upv_2022_predictions.csv"
validated_predictions[dataset_to_export].to_csv(filename, index=False)
files.download(filename)
```

The dictionary exists only in an executed notebook session. Saved cell outputs
alone do not restore the model or its individual predictions. A new run may
produce slightly different probabilities with different library versions.

Переменная существует только в выполненной сессии тетрадки. Сохранённые выводы
ячеек сами по себе не восстанавливают модель и прогнозы для каждого студента.
При новом запуске с другими версиями библиотек вероятности могут немного отличаться.

## Preset schemas

All notebook exports use `Predicted Dropout Risk` as the score column. Alternative
column names remain selectable in the app. Probabilities must describe the
declared positive event using information available at prediction time.

| Preset | Outcome | Positive | Negative | Excluded | Decision key | Student ID | Groups | Reference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UPV 2022 | `abandono_hash` | `A` | `B` | None | `dni_hash` | `dni_hash` | `dedicacion`, `desplazado_hash`, `estudios_m_hash` | `dedicacion`: `TC` |
| OULAD | `final_result` | `Withdrawn` | `Pass`, `Fail`, `Distinction` | None | `id_student`, `code_module`, `code_presentation` | `id_student` | `imd_band` | None |
| UCI | `Target` | `Dropout` | `Graduate` | `Enrolled` | `Source Row ID` | Not supplied | `Daytime/evening attendance` | `Daytime` |

UPV exports already contain one checked, aggregated student row. OULAD exports
retain enrollments. UCI source row numbers are technical keys; they cannot verify
actual student identity. All rows, including declared exclusions, must have valid
scores and known outcome mappings.

Prepared real prediction exports are not included as application examples.
`examples/sample_predictions.csv` contains only synthetic demonstration data.
