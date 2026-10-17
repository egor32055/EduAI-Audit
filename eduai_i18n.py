"""Human-written UI translations. Dataset names and source codes stay intact."""

RU = {
    "Custom CSV": "Свой CSV", "Synthetic example": "Синтетический пример",
    "Audit existing probability predictions against observed outcomes. Compare review capacities, inspect group results, and download a report.": "Сравните готовые прогнозы вероятности с известными исходами: настройте доли отбора, изучите результаты по группам и скачайте отчёт.",
    "This app does not train a model or recommend a review capacity.": "Приложение проверяет готовые прогнозы. Выбор доли отбора остаётся за вами.",
    "1. Upload predictions and outcomes": "1. Загрузите прогнозы и исходы",
    "CSV file": "CSV-файл", "Choose a CSV file": "Выберите CSV-файл",
    "One row per decision; include existing probabilities and observed outcomes.": "Одна строка на единицу аудита: студент, запись на курс или период. Нужны готовая вероятность и известный исход.",
    "Delimiter": "Разделитель", "Comma": "Запятая", "Semicolon": "Точка с запятой", "Tab": "Табуляция", "Pipe": "Вертикальная черта",
    "Encoding": "Кодировка", "Upload a CSV file to configure an audit.": "Загрузите CSV-файл, чтобы настроить аудит.",
    "Download sample CSV": "Скачать пример CSV",
    "The sample contains synthetic data. Select the Synthetic example preset after uploading it.": "В примере вымышленные данные. После загрузки выберите пресет «Синтетический пример».",
    "Loaded {rows} rows and {columns} columns.": "Загружено строк: {rows}; столбцов: {columns}.",
    "Preview the first 10 rows": "Первые 10 строк файла",
    "Only one column was found. Check the delimiter if you expected several columns.": "Найден только один столбец. Если их должно быть несколько, проверьте разделитель.",
    "2. Configure the audit": "2. Настройте аудит", "Configuration preset": "Пресет настроек",
    "Presets fill matching fields from PROTOTYPE. Review them for your file; every field remains editable.": "Пресеты заполняют найденные поля по настройкам PROTOTYPE. Проверьте их для своего файла; каждое поле можно изменить.",
    "UPV 2022 requires one prepared row per student. Raw course rows must be checked and aggregated before prediction export.": "Для UPV 2022 нужна одна подготовленная строка на студента. Исходные строки по курсам нужно проверить и объединить до выгрузки прогнозов.",
    "OULAD selects course enrollments. One student may have several enrollments; use the composite decision key and student ID.": "В OULAD отбираются записи на курс. У студента может быть несколько таких записей: укажите составной ключ решения и ID студента.",
    "UCI has no verified student identifier. A Source Row ID or an explicitly chosen technical row key cannot establish real student identity.": "В UCI нет проверяемого ID студента. Source Row ID или явно выбранный номер строки не подтверждает реальную личность студента.",
    "Dataset name": "Название выборки", "Select a column": "Выберите столбец", "Select a value": "Выберите значение", "Choose values": "Выберите значения",
    "Observed outcome column": "Столбец известного исхода",
    "Positive-outcome probability column": "Столбец вероятности положительного исхода",
    "Scores must be existing probabilities from 0 to 1 for the positive outcome.": "Готовые вероятности от 0 до 1 именно для выбранного положительного исхода — например, отчисления.",
    "No recognized prediction column was found. Choose an existing probability column if it has another name. Raw dataset features are not prediction probabilities.": "Знакомый столбец прогноза не найден. Если вероятность уже есть под другим именем, выберите её. Признаки исходного датасета не являются готовыми прогнозами.",
    "The selected preset could not find these expected columns: {columns}. Select available mappings or upload a prepared prediction export.": "Для пресета не найдены ожидаемые столбцы: {columns}. Укажите подходящие поля или загрузите подготовленный файл с прогнозами.",
    "How to export ready predictions from PROTOTYPE": "Как выгрузить готовые прогнозы из PROTOTYPE",
    "After the notebook's Input validation section has completed, run this cell in Colab and upload the downloaded CSV. It exports existing held-out scores without fitting another model.": "После выполнения раздела Input validation в тетрадке запустите эту ячейку в Colab и загрузите скачанный CSV. Она выгружает уже рассчитанные проверочные прогнозы без нового обучения.",
    "The outcome column contains missing values. Resolve them in the CSV before auditing.": "В столбце исхода есть пропуски. Исправьте их в CSV перед аудитом.",
    "No observed outcome values were found.": "В столбце не найдены известные исходы.",
    "Positive outcome": "Положительный исход", "Negative outcomes": "Отрицательные исходы", "Excluded outcomes": "Исключаемые исходы",
    "Positive means the event being audited, such as dropout; it does not mean a desirable outcome.": "Положительный исход — событие, которое проверяем, например отчисление. Слово «положительный» не означает, что событие желательно.",
    "Explicitly select the resolved outcomes that count as negative.": "Выберите известные исходы, при которых проверяемое событие не произошло.",
    "These rows are counted, then removed before ranking and metric calculations.": "Эти строки будут посчитаны и исключены до ранжирования и расчёта показателей.",
    "Every outcome value must be assigned to positive, negative, or excluded. Missing outcomes are rejected.": "Каждое значение исхода нужно отнести к положительным, отрицательным или исключаемым. Пропуски в исходах недопустимы.",
    "Unmapped outcomes: {values}.": "Не назначены правила для исходов: {values}.",
    "Decision unit": "Единица аудита", "Student": "Студент", "Course Enrollment": "Запись на курс", "Student Period": "Студент за период", "Record": "Запись",
    "What does one CSV row represent? For prepared UPV 2022 this is a student; for OULAD it is a course enrollment.": "Что представляет одна строка CSV? В подготовленном UPV 2022 — студента, в OULAD — запись студента на курс.",
    "Student ID column (optional)": "Столбец ID студента (необязательно)", "Not supplied": "Не указан", "No reference": "Без базовой группы",
    "Needed to account for repeated records from the same student. Without it, intervals for non-student units are unavailable.": "Нужен, чтобы учитывать связь нескольких записей одного студента. Без него интервалы для единиц, отличных от студента, недоступны.",
    "Use source row number as a technical decision key": "Использовать номер строки как технический ключ решения",
    "Use only when the CSV has no decision ID. Row order is preserved, but this cannot verify real student identity or duplicate students.": "Для файла без ID решения. Порядок строк сохраняется, но такой ключ не подтверждает личность и не выявляет повторяющихся студентов.",
    "The report will identify the technical key and its identity limitation.": "Отчёт укажет, что ключ технический и не проверяет реальную личность студента.",
    "Decision key columns": "Столбцы ключа решения",
    "Choose columns that together identify one decision. Duplicate or missing keys stop the audit.": "Столбцы, которые вместе однозначно определяют одну единицу аудита. Для UPV 2022 — dni_hash; для OULAD — студент, курс и учебный период. Повторы и пропуски останавливают аудит.",
    "Group columns (optional)": "Столбцы групп (необязательно)",
    "Missing group values remain visible as Unknown in the audit.": "Показатели будут рассчитаны отдельно для значений каждого выбранного столбца. Пропуски останутся в группе Unknown.",
    "Reference groups for signed comparisons (optional)": "Базовые группы для расчёта разниц (необязательно)",
    "Reference for {column}": "Базовая группа для {column}",
    "A reference is the baseline for differences: other group minus reference. It does not change scores, selections, or group metrics. For example, TP recall 40% minus TC recall 50% gives −10 percentage points.": "Разница считается как показатель другой группы минус показатель базовой. База не меняет прогнозы, отбор или показатели групп. Например, Recall TP 40% минус Recall TC 50% = −10 процентных пунктов.",
    "Review shares (%)": "Доли отбора (%)",
    "Select one or more percentages. Selection counts round upward after exclusions.": "Выберите одну или несколько долей от 1% до 100%. Число выбранных строк округляется вверх после исключения исходов.",
    "Select at least one review share.": "Выберите хотя бы одну долю отбора.",
    "Enter percentages separated by commas. Selection counts round upward after exclusions.": "Введите проценты через запятую. Например, 15, 20, 30. Число выбранных строк округляется вверх после исключения исходов.",
    "Report focus share": "Доля отбора для подробного отчёта",
    "The focus share controls detailed group results. It is not a recommended capacity.": "Для этой доли будут показаны подробные результаты по группам. Это ваш выбор для просмотра, а не рекомендация приложения.",
    "Dataset context (optional)": "Контекст данных (необязательно)",
    "At enrollment": "При поступлении",
    "At the end of the first semester": "В конце первого семестра",
    "At the end of an academic year": "В конце учебного года",
    "By the end of the first semester": "К концу первого семестра",
    "By the end of the first year": "К концу первого учебного года",
    "By the end of an academic year": "К концу учебного года",
    "By the end of the programme": "К завершению программы обучения",
    "If no option matches your data, leave Not supplied.": "Если подходящего варианта нет, оставьте «Не указано».",
    "When were the predictions produced?": "Когда были получены прогнозы?", "For example: at enrollment": "Например: при поступлении",
    "What outcome period do they cover?": "За какой период наблюдались исходы?", "For example: by the end of the first year": "Например: к концу первого учебного года",
    "These descriptions are supplied by you; the app cannot verify prediction timing or outcome definitions.": "Это ваши пояснения: приложение не может проверить время получения прогнозов и смысл исходов.",
    "3. Run audit": "3. Запустите аудит", "Run audit": "Запустить аудит",
    "Select the outcome, probability, and positive-outcome fields.": "Выберите столбцы исхода и вероятности, а также положительный исход.",
    "Select at least one negative outcome.": "Выберите хотя бы один отрицательный исход.",
    "Select decision key columns or explicitly use source row numbers.": "Выберите столбцы ключа решения или явно включите использование номеров строк.",
    "Calculating audit metrics and uncertainty intervals...": "Расчёт показателей и интервалов неопределённости…",
    "4. Results and report": "4. Результаты и отчёт",
    "Audit complete. Results describe the submitted, outcome-filtered records.": "Аудит завершён. Результаты относятся к загруженным строкам после исключения указанных исходов.",
    "Audited records": "Проверено строк", "Selected records": "Выбрано строк", "Found cases": "Найдено случаев", "Missed cases": "Пропущено случаев", "False alarms": "Ложные тревоги",
    "Key findings": "Основные результаты", "Review capacities": "Сравнение долей отбора", "Additional workload": "Дополнительная нагрузка",
    "Group comparisons at the focus share": "Сравнение групп при выбранной доле",
    "Data and scope": "Данные и условия аудита", "Group counts": "Числа по группам", "Group metrics and uncertainty": "Показатели групп и неопределённость",
    "Reading notes and limits": "Как читать результаты и ограничения", "No results for this section.": "Для этого раздела нет результатов.",
    "Download full HTML report": "Скачать полный HTML-отчёт",
    "Counts across review shares": "Числа при разных долях отбора", "Metrics across review shares": "Показатели при разных долях отбора",
    "Requested review share (%)": "Заданная доля отбора (%)", "Records": "Строки", "Rate (%)": "Показатель (%)", "Metric": "Показатель",
    "Recall": "Recall", "Precision": "Precision", "False-positive rate": "False-Positive Rate (FPR)",
    "Found positive cases divided by all positive cases. Shows how many actual cases were detected.": "Найденные положительные случаи / все положительные случаи. Показывает, какую долю реальных случаев удалось обнаружить.",
    "Found positive cases divided by selected records. Shows how many selected records are actual positive cases.": "Найденные положительные случаи / выбранные строки. Показывает, какая доля выбранных записей действительно относится к положительному исходу.",
    "False alarms divided by all negative cases. Shows how many negative cases were selected unnecessarily.": "Ложные тревоги / все отрицательные случаи. Показывает, какая доля записей с отрицательным исходом попала в отбор.",
    "Additional found positive cases divided by additional selected records when the review share increases. Undefined when no records are added.": "Дополнительно найденные положительные случаи / дополнительно выбранные строки при увеличении доли отбора. Не определена, если новые строки не добавились.",
    "Recall = found / all positive cases. Precision = found / selected. False-positive rate = false alarms / all negative cases.": "Recall = найденные случаи / все положительные случаи. Precision = найденные случаи / выбранные строки. False-Positive Rate (FPR) = ложные тревоги / все отрицательные случаи.",
    "Lines connect observed results at the declared shares. They do not select an optimal capacity. Intervals and support notes are in the tables.": "Линии соединяют результаты при заданных долях. Графики не выбирают оптимальную долю. Интервалы и замечания о числе наблюдений приведены в таблицах.",
    "Report focus": "Фокус отчёта", "Audit Report": "Отчёт аудита", "Findings": "Результаты",
}


RU.update({
    "Load saved settings (optional)": "Загрузить сохранённые настройки (необязательно)",
    "Settings JSON file": "JSON-файл настроек", "Apply settings": "Применить настройки",
    "Settings applied. Review the data summary before running the audit.": "Настройки применены. Перед запуском проверьте сводку данных.",
    "Save settings JSON": "Сохранить настройки JSON", "Data summary before audit": "Сводка данных перед аудитом",
    "Input records": "Строк на входе", "Excluded records": "Исключено строк", "Positive cases": "Положительные случаи",
    "Negative cases": "Отрицательные случаи", "Distinct supplied student IDs": "Различных указанных ID студентов",
    "Group column": "Столбец группы", "Group": "Группа",
    "Missing group values after exclusions": "Пропуски в группе после исключений",
    "This summary uses the declared outcome mapping and exclusions. Input checks do not verify real student identity or prediction provenance.": "Сводка учитывает выбранные исходы и исключения. Проверка данных не подтверждает реальную личность студентов и происхождение прогнозов.",
    "Complete the outcome, probability, key, and share selections to preview the audit population.": "Выберите исходы, вероятность, ключ и доли отбора, чтобы увидеть состав проверяемой выборки.",
    "Group metrics at the focus share": "Показатели групп при выбранной доле", "Compare groups by": "Сравнить группы по столбцу",
    "Points show group estimates; lines show available confidence intervals. Unavailable intervals are not drawn. Inspect support notes in the tooltips and tables.": "Точки показывают значения метрик, линии — доступные доверительные интервалы. Недоступные интервалы не изображаются. Замечания о числе наблюдений доступны в подсказках и таблицах.",
    "Reference group": "Базовая группа", "Other group": "Другая группа", "No support flag": "Без замечания о числе наблюдений",
    "Metric unavailable": "Метрика недоступна",
    "Interval lower bound (%)": "Нижняя граница интервала (%)", "Interval upper bound (%)": "Верхняя граница интервала (%)",
    "Interval status": "Статус интервала", "Relevant outcomes": "Исходов в знаменателе", "Contributing students": "Студентов в знаменателе",
    "Support note": "Замечание о наблюдениях", "Available": "Доступен", "No Relevant Outcomes": "Нет исходов для расчёта",
    "Missing Entity ID": "Не указан ID студента", "Too Few Independent Units": "Слишком мало независимых студентов",
    "Boundary Estimate: Bootstrap Unavailable": "Граничная оценка: бутстрэп недоступен",
    "Too Few Outcome Event Units": "Слишком мало студентов с выбранными или невыбранными исходами",
    "Too Many Undefined Resamples": "Слишком много неопределённых повторных выборок", "Degenerate Bootstrap": "Вырожденные повторные выборки бутстрэпа",
    "Limited Outcome Support": "Мало студентов с соответствующим исходом",
    "Sparse Selected or Unselected Outcomes": "Мало студентов с выбранными или невыбранными исходами",
    "Export audit tables": "Скачать таблицы аудита", "Table to download": "Таблица для скачивания",
    "Group comparisons at all shares": "Сравнение групп при всех долях отбора",
    "Download selected table CSV": "Скачать выбранную таблицу CSV", "Download all tables ZIP": "Скачать все таблицы ZIP",
    "CSVs include all compared shares with numeric values and original column and status codes. Empty numeric cells mean unavailable, not zero.": "CSV содержат все сравниваемые доли отбора: числовые значения и исходные названия столбцов и коды статусов. Пустая числовая ячейка означает, что значение недоступно, а не равно нулю.",
})


def tr(text, language="en", **values):
    if language not in ("en", "ru"):
        raise ValueError("Unsupported language")
    return (RU.get(text, text) if language == "ru" else text).format(**values)


METRIC_HELP = {
    "Recall": "Found positive cases divided by all positive cases. Shows how many actual cases were detected.",
    "Precision": "Found positive cases divided by selected records. Shows how many selected records are actual positive cases.",
    "False-Positive Rate": "False alarms divided by all negative cases. Shows how many negative cases were selected unnecessarily.",
    "Marginal Precision": "Additional found positive cases divided by additional selected records when the review share increases. Undefined when no records are added.",
}


def metric_help(label, language="en"):
    """Explain displayed metric names, including interval headings, on demand."""
    for name in ("Marginal Precision", "False-Positive Rate", "Recall", "Precision"):
        if label.startswith(name):
            return tr(METRIC_HELP[name], language)
    return None


ERRORS_RU = {
    "The settings file has an invalid structure or unsupported values.": "В файле настроек неверная структура или неподдерживаемые значения.",
    "This settings file is not a supported EduAI-Audit version.": "Версия файла настроек не поддерживается EduAI-Audit.",
    "Choose a settings JSON file smaller than 256 KB.": "Выберите JSON-файл настроек размером до 256 КБ.",
    "The settings file is not valid UTF-8 JSON.": "Файл настроек должен быть корректным JSON в кодировке UTF-8.",
    "The CSV file is empty.": "CSV-файл пуст.",
    "The file cannot be decoded with the selected encoding.": "Файл не читается в выбранной кодировке. Попробуйте другую кодировку.",
    "The CSV file has no readable header.": "Не удалось прочитать строку названий столбцов CSV.",
    "Every CSV column must have a non-empty name.": "У каждого столбца CSV должно быть непустое название.",
    "The CSV header contains duplicate column names.": "В заголовке CSV повторяются названия столбцов.",
    "The CSV file could not be parsed. Check its delimiter and rows.": "Не удалось разобрать CSV. Проверьте разделитель и структуру строк.",
    "The CSV file has no data rows.": "В CSV нет строк с данными.",
    "The outcome column contains blank values.": "В столбце исхода есть пустые значения.",
    "Target column contains missing outcomes; resolve them before auditing": "В столбце исхода есть пропуски. Исправьте их перед аудитом.",
    "Positive, negative, and excluded outcomes must not overlap": "Положительные, отрицательные и исключаемые исходы не должны пересекаться.",
    "Outcome and score columns must be separate from group columns": "Столбцы исхода и вероятности нельзя использовать как столбцы групп.",
    "Decision keys must be separate from outcome and score columns": "Ключ решения должен отличаться от столбцов исхода и вероятности.",
    "Entity ID must be separate from outcome and score columns": "ID студента должен отличаться от столбцов исхода и вероятности.",
    "Duplicate decision keys; supply one row per decision unit": "Ключи решения повторяются. Оставьте одну строку на единицу аудита; приложение не объединяет строки автоматически.",
    "Student audit contains repeated entity IDs; aggregate or correct the records explicitly": "При аудите студентов найдены повторяющиеся ID. Сначала подготовьте по одной строке на студента.",
    "Scores must be probabilities, not boolean predictions": "Нужны вероятности от 0 до 1, а не логические метки прогноза.",
    "Score column must contain numeric probabilities": "Столбец вероятности должен содержать числа от 0 до 1.",
    "Score column must contain finite probabilities between 0 and 1": "Вероятности должны быть конечными числами от 0 до 1 без пропусков, в том числе в исключаемых строках.",
    "Audited rows must contain both outcome classes after exclusions": "После исключений должны остаться и положительные, и отрицательные исходы.",
    "dataset_name must be a non-empty string": "Введите непустое название выборки.",
    "Enter at least one review share, such as 15, 20, 30.": "Введите хотя бы одну долю отбора, например 15, 20, 30.",
    "Review shares must be comma-separated percentages.": "Введите проценты, разделённые запятыми, например 15, 20, 30.",
    "Each review share must be above 0% and at most 100%.": "Каждая доля должна быть больше 0% и не больше 100%.",
    "Review shares must be unique.": "Доли отбора не должны повторяться.",
}


def error_text(error, language):
    message = str(error)
    if language == "en":
        return message
    if message in ERRORS_RU:
        return ERRORS_RU[message]
    for prefix, translated in [
        ("ID column contains missing or blank values: ", "В столбце ID есть пропуски или пустые значения: "),
        ("Missing columns: ", "В файле отсутствуют столбцы: "),
        ("Reference group not found in audited rows: ", "Базовая группа отсутствует в проверяемых строках столбца: "),
    ]:
        if message.startswith(prefix):
            return translated + message[len(prefix):]
    if " rows contain unmapped outcomes;" in message:
        return "Есть строки с нераспределёнными исходами: " + message.split(" rows", 1)[0] + ". Назначьте каждый исход положительным, отрицательным или исключаемым."
    if message.startswith("The CSV column name ") and message.endswith(" is reserved."):
        return "В CSV используется зарезервированное название столбца __source_row_number__. Переименуйте его."
    return "Проверьте настройки аудита. Подробности: " + message
