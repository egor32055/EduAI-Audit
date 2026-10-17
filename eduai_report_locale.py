"""Russian presentation of an already computed report, preserving its evidence."""

from copy import deepcopy
from html import escape
import re

import pandas as pd

from eduai_charts import charts_html
from eduai_i18n import tr
from eduai_report import _report_interval, _report_number, _report_percent


HEADERS_RU = {
    "Field": "Поле", "Value": "Значение", "Dataset": "Выборка", "Input Records": "Строк на входе",
    "Excluded Records": "Исключено строк", "Audited Records": "Проверено строк", "Decision Unit": "Единица аудита",
    "Outcome Column": "Столбец исхода", "Positive Outcome": "Положительный исход", "Negative Outcomes": "Отрицательные исходы",
    "Excluded Outcomes": "Исключаемые исходы", "Decision Key": "Ключ решения", "Student ID Column": "Столбец ID студента",
    "Group Features": "Столбцы групп", "Score Column": "Столбец вероятности", "Focus Review Share": "Доля для подробного отчёта",
    "Actual Selected Share": "Фактическая доля отбора", "Compared Review Shares": "Сравниваемые доли отбора",
    "Confidence Level": "Доверительный уровень", "Interval Method": "Метод интервалов", "Bootstrap Resamples": "Повторные выборки бутстрэпа",
    "Resampling Seed": "Начальное значение генератора", "Reference Groups": "Базовые группы", "Capacity Rounding": "Округление отбора",
    "Equal-Score Rule": "Правило равных вероятностей", "Prediction Timing": "Момент получения прогнозов", "Outcome Horizon": "Период наблюдения исходов",
    "Decision Key Note": "Примечание о ключе решения", "Review Share": "Доля отбора", "Selected Records": "Выбрано строк",
    "Found Cases": "Найдено случаев", "Missed Cases": "Пропущено случаев", "False Alarms": "Ложные тревоги",
    "Precision": "Точность отбора", "Recall": "Полнота", "False-Positive Rate": "Доля ложных тревог",
    "Group Feature": "Столбец группы", "Group": "Группа", "Records": "Строки", "Positive Outcomes": "Положительные исходы",
    "Metric": "Показатель", "Estimate": "Оценка", "Relevant Outcomes": "Исходы в знаменателе",
    "Contributing Students": "Студенты в знаменателе", "Interval Status": "Статус интервала", "Support Note": "Замечание о наблюдениях",
    "Comparison": "Сравнение", "Difference (pp)": "Разница (п. п.)", "From Review Share": "С доли отбора", "To Review Share": "До доли отбора",
    "Additional Records": "Дополнительно строк", "Additional Found Cases": "Дополнительно найдено случаев",
    "Additional False Alarms": "Дополнительные ложные тревоги", "Marginal Precision": "Точность дополнительного отбора",
}
STATUS_RU = {
    "Available": "Доступен", "Unavailable": "Недоступно", "No Relevant Outcomes": "Нет исходов для расчёта",
    "Missing Entity ID": "Не указан ID студента", "Too Few Independent Units": "Слишком мало независимых студентов",
    "Boundary Estimate: Bootstrap Unavailable": "Граничная оценка: бутстрэп недоступен",
    "Too Few Outcome Event Units": "Слишком мало студентов с выбранными или невыбранными исходами",
    "Too Many Undefined Resamples": "Слишком много неопределённых повторных выборок",
    "Degenerate Bootstrap": "Вырожденные повторные выборки бутстрэпа",
    "Component Interval Unavailable": "Интервал одной из сравниваемых групп недоступен",
    "Limited Outcome Support": "Мало студентов с соответствующим исходом",
    "Sparse Selected or Unselected Outcomes": "Мало студентов с выбранными или невыбранными исходами",
    "Wilson": "Уилсон", "Newcombe": "Ньюкомб", "Student Cluster Bootstrap": "Бутстрэп с кластерами по студентам",
    "Not supplied": "Не указано", "Not used": "Не используется", "None": "Нет",
    "Ceiling of declared decimal share times audited records": "Произведение заданной доли и числа проверяемых строк округляется вверх",
    "Stable original input row order": "Исходный порядок строк файла",
    "Technical source row number only; real student identity is not verified.": "Только технический номер строки; реальная личность студента не проверена.",
}
LIMITS_RU = {
    "Counts describe the submitted, outcome-filtered cohort. Positive cases mean the declared positive outcome; course withdrawal and university dropout are different events.": "Числа описывают загруженную выборку после исключения исходов. Положительным считается указанный вами исход. Уход с курса и отчисление из университета — разные события.",
    "Intervals describe evaluation-sample uncertainty for fixed scores and selections, assuming independent students and allowing dependence within supplied student IDs. They do not cover model refitting, re-ranking, or future-cohort changes.": "Интервалы описывают неопределённость проверочной выборки при фиксированных прогнозах и отборе. Предполагается независимость студентов, а записи одного студента могут быть связаны. Повторное обучение, новое ранжирование и изменения будущих наборов студентов не учитываются.",
    "Intervals are individual exploratory comparisons without simultaneous coverage across groups or review shares. An interval including zero does not establish equality; excluding zero does not establish causation or discrimination.": "Интервалы относятся к отдельным исследовательским сравнениям, без одновременной гарантии для всех групп и долей отбора. Наличие нуля в интервале не доказывает равенство; отсутствие нуля не доказывает причинность или дискриминацию.",
    "Capacity changes are observed count differences. The report does not infer significance of policy changes or select an optimal capacity.": "Изменения при переходе между долями отбора — наблюдаемые разницы чисел. Отчёт не оценивает статистическую значимость изменения политики и не выбирает оптимальную долю.",
    "Recall divides found positive cases by all positive cases. False-positive rate divides false alarms by negative cases. Precision is the positive-case share of selected records; marginal precision uses only additional selected records.": "Полнота — доля найденных положительных случаев среди всех положительных. Доля ложных тревог — число ложных тревог, делённое на число отрицательных случаев. Точность отбора — доля положительных случаев среди выбранных строк; точность дополнительного отбора использует только добавленные строки.",
    "Group labels follow the supplied display mapping; unmapped values remain source codes. Support flags and bootstrap guards are diagnostic rules, not guarantees of interval coverage.": "Названия групп следуют переданным подписям; остальные значения остаются исходными кодами. Замечания о числе наблюдений и ограничения бутстрэпа служат диагностике и не гарантируют покрытие интервалов.",
    "No student ID was supplied. Student identity and duplicate students cannot be verified from technical row keys; student intervals rely on the one-row-per-student assumption.": "ID студента не указан. Технический ключ строки не проверяет личность и повторяющихся студентов; интервалы для студентов опираются на предположение «одна строка — один студент».",
    "Outcome exclusions change the evaluation population. Compare capacities within this filtered cohort; results do not describe the excluded outcomes.": "Исключение исходов меняет оцениваемую выборку. Сравнивайте доли отбора внутри этой выборки; результаты не описывают исключённые исходы.",
    "Prediction timing and/or outcome horizon were not supplied. Verify them with the data provider before interpreting this as an operational evaluation.": "Момент получения прогнозов и/или период наблюдения исходов не указаны. Уточните их у поставщика данных перед использованием результатов в практическом решении.",
    "Prediction timing and outcome horizon are supplied descriptions; this report does not verify their provenance or rule out outcome leakage.": "Момент получения прогнозов и период исходов описаны пользователем. Отчёт не проверяет происхождение этих сведений и не исключает использование будущих исходов при получении прогнозов.",
}


def _status(text):
    return "; ".join(STATUS_RU.get(part, part) for part in str(text).split("; "))


def _formatted(text):
    return str(text).replace("Unavailable", "Недоступно").replace(" to ", " — ").replace(" pp", " п. п.")


def _header(text):
    match = re.fullmatch(r"(?:(Recall|False-Positive Rate) )?([\d.]+)% CI", text)
    if match:
        prefix = HEADERS_RU[match[1]] + ": " if match[1] else ""
        return prefix + "ДИ " + match[2] + "%"
    return HEADERS_RU.get(text, text)


def _russian_tables(report, comparison):
    tables = {}
    for key, original in report["tables"].items():
        table = original.copy(deep=True)
        if key == "scope":
            for index, row in table.iterrows():
                field, value = row["Field"], row["Value"]
                if field == "Decision Unit":
                    table.at[index, "Value"] = tr(value, "ru")
                elif field in {"Interval Method", "Bootstrap Resamples", "Resampling Seed", "Capacity Rounding", "Equal-Score Rule", "Decision Key Note"}:
                    table.at[index, "Value"] = _status(value)
                elif field in {"Student ID Column", "Prediction Timing", "Outcome Horizon"} and value == "Not supplied":
                    table.at[index, "Value"] = "Не указано"
                elif field in {"Group Features", "Reference Groups", "Negative Outcomes", "Excluded Outcomes"} and value == "None":
                    table.at[index, "Value"] = "Нет"
                table.at[index, "Field"] = HEADERS_RU.get(field, field)
        else:
            for column in table.columns:
                if column in {"Interval Status", "Support Note"}:
                    table[column] = table[column].map(_status)
                elif column == "Metric":
                    table[column] = table[column].map(lambda value: HEADERS_RU.get(value, value))
                elif column not in {"Group Feature", "Group", "Comparison"}:
                    table[column] = table[column].map(_formatted)
            if key == "group_comparisons" and not table.empty:
                rows = comparison["reports"][report["focus_share"]]["group_comparisons"]
                table["Comparison"] = [f"{row.group_value} минус {row.reference_group}" for _, row in rows.iterrows()]
        tables[key] = table.rename(columns=_header)
    return tables


def _russian_findings(report, comparison):
    focus_share = report["focus_share"]
    focus = comparison["reports"][focus_share]
    review, validation = focus["review"], comparison["input_validation"]
    count, percent = _report_number, _report_percent
    share = percent(100 * focus_share)
    unit = tr(focus["configuration"]["selection_unit"].replace("_", " ").title(), "ru").lower()
    cutoff = comparison["summary"].loc[comparison["summary"].review_share_pct.eq(100 * focus_share)].iloc[0]
    changes = iter(comparison["marginal_changes"].itertuples())
    differences = iter(focus["group_comparisons"].itertuples())
    missing = iter((c, n) for c, n in validation["missing_group_records"].items() if n)
    result = []
    for finding in report["findings"]:
        rule = finding["rule"]
        if rule == "focus_outcomes":
            text = f"При доле отбора {share} выбрано записей: {count(review['selected_records'])}. Единица отбора: {unit}. Найдено положительных случаев: {count(review['found_positives'])} из {count(review['found_positives'] + review['missed_positives'])}; пропущено: {count(review['missed_positives'])}; ложных тревог: {count(review['false_alarms'])}."
        elif rule == "outcome_exclusions":
            exclusions = ", ".join(f"{label}: {count(n)}" for label, n in validation["excluded_outcome_counts"].items())
            text = f"По правилам исходов исключено строк: {count(validation['excluded_records'])} ({exclusions}). Результаты относятся к оставшимся строкам: {count(validation['audited_records'])}."
        elif rule == "record_and_student_units":
            text = f"В выбранных записях ({count(review['selected_records'])}) представлены различные ID студентов: {count(review['unique_entities_to_review'])}."
        elif rule == "cutoff_ties":
            text = f"Одинаковая вероятность на границе отбора встречается у записей: {count(cutoff.cutoff_tie_records)}. Из них выбрано {count(cutoff.selected_at_cutoff)} по исходному порядку строк файла."
        elif rule == "capacity_change":
            row = next(changes)
            text = f"Увеличение доли отбора с {percent(row.from_review_share_pct)} до {percent(row.to_review_share_pct)} добавляет к проверке записей: {count(row.additional_records)}; дополнительно найдено положительных случаев: {count(row.additional_found_positives)}; добавлено ложных тревог: {count(row.additional_false_alarms)}."
        elif rule == "group_difference":
            row = next(differences)
            metric = HEADERS_RU[{"recall_pct": "Recall", "false_positive_rate_pct": "False-Positive Rate"}[row.metric]].lower()
            interval = _formatted(_report_interval(row._asdict(), difference=True))
            difference = "Недоступно" if pd.isna(row.difference_pp) else f"{row.difference_pp:+.1f} п. п."
            if row.ci_status != "Available":
                direction = "Интервал недоступен; направление разницы не оценивается."
            elif row.ci_lower_pp <= 0 <= row.ci_upper_pp:
                direction = "Интервал включает ноль; направление разницы не установлено."
            else:
                direction = "При указанных предположениях интервал лежит " + ("выше" if row.ci_lower_pp > 0 else "ниже") + " нуля."
            confidence = 100 * focus["uncertainty_configuration"]["confidence_level"]
            interval_sentence = interval if interval.endswith(".") else interval + "."
            text = f"При доле {share}, {row.group_column}: {row.group_value} минус {row.reference_group}; {metric}, разница: {difference}; отдельный ДИ {confidence:g}%: {interval_sentence} {direction}"
            if row.support_note:
                text += " Замечание: " + _status(row.support_note) + "."
        elif rule == "no_group_reference":
            text = "Показатели групп доступны; базовые группы для расчёта разниц не заданы."
        elif rule == "no_groups":
            text = "Столбцы групп не заданы; отчёт содержит только общие результаты."
        elif rule == "group_interval_support":
            intervals = focus["group_uncertainty"]
            unavailable = int(intervals.ci_status.ne("Available").sum())
            limited = int(intervals.support_note.ne("").sum())
            text = f"При выбранной доле недоступных интервалов показателей групп: {unavailable}; показателей с замечаниями о числе наблюдений: {limited}. Проверьте число исходов и студентов в знаменателе."
        elif rule == "missing_group_values":
            column, n = next(missing)
            text = f"В столбце {column} нет значения у проверяемых строк: {count(n)}. Эти строки остаются в группе Unknown."
        else:
            raise ValueError(f"Untranslated finding rule: {rule}")
        result.append({**finding, "text": text})
    return result


def present_report(report, comparison, language="en"):
    """Change presentation language and add plots without rerunning the audit."""
    if language not in ("en", "ru"):
        raise ValueError("Unsupported language")
    chart_html = charts_html(comparison["summary"], language)
    if language == "en":
        html = report["html"].replace("<html>", '<html lang="en">', 1)
        return {**report, "html": html.replace("<h3>Review Capacities</h3>", chart_html + "<h3>Review Capacities</h3>", 1)}
    result = deepcopy(report)
    result["tables"] = _russian_tables(report, comparison)
    result["findings"] = _russian_findings(report, comparison)
    result["limitations"] = [LIMITS_RU[note] for note in report["limitations"]]
    def table(key):
        frame = result["tables"][key]
        return '<p>Для этого раздела нет результатов.</p>' if frame.empty else '<div class="audit-table">' + frame.to_html(index=False, border=0, escape=True) + '</div>'
    title = "Отчёт аудита: " + result["dataset_name"]
    pieces = ['<!doctype html><html lang="ru"><head><meta charset="utf-8">',
              '<title>' + escape(title) + '</title>',
              '<style>body{font-family:Arial,sans-serif;line-height:1.5;max-width:1200px;margin:auto;padding:20px;color:#13233B}table{border-collapse:collapse;font-size:.9em}td,th{border:1px solid #ccd5e3;padding:6px;text-align:left;vertical-align:top}.audit-table{overflow-x:auto}svg{width:100%;height:auto}li{margin:8px 0}details{margin:16px 0}</style></head><body>',
              '<h1>' + escape(title) + '</h1>',
              '<p>Доля для подробного отчёта: <strong>' + _report_percent(100 * result["focus_share"]) + '</strong>. Это выбор пользователя для просмотра результатов, а не рекомендованная доля отбора.</p>',
              '<h2>Основные результаты</h2><ul>' + ''.join('<li>' + escape(f['text']) + '</li>' for f in result["findings"]) + '</ul>',
              '<h2>Данные и условия аудита</h2>' + table("scope"), chart_html,
              '<h2>Сравнение долей отбора</h2>' + table("capacity_results"),
              '<h2>Дополнительная нагрузка</h2>' + table("marginal_changes"),
              '<h2>Сравнение групп при выбранной доле</h2>' + table("group_comparisons"),
              '<details><summary>Числа по группам</summary>' + table("group_counts") + '</details>',
              '<details><summary>Показатели групп и неопределённость</summary>' + table("group_uncertainty") + '</details>',
              '<h2>Как читать результаты и ограничения</h2><ul>' + ''.join('<li>' + escape(note) + '</li>' for note in result["limitations"]) + '</ul></body></html>']
    result["html"] = ''.join(pieces)
    return result
