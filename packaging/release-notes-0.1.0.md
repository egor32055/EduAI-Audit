## Windows preview / Пробная версия для Windows

Download **EduAI-Audit-Setup-0.1.0.exe** from the assets below and run it.
Скачайте **EduAI-Audit-Setup-0.1.0.exe** ниже и запустите установку.

- Windows 10/11 x64. Python is bundled; PyCharm is not required.
- CSV upload with existing predictions and known outcomes; no model training.
- Single-prediction audit and comparison of two probability columns.
- English / Russian UI, one-click artificial examples, HTML and CSV/ZIP reports.
- The installed app opens a local browser interface at `http://127.0.0.1:8502/`.
- Use **Stop EduAI Audit** in the Start menu to stop the local server.

Python устанавливать отдельно не нужно. После установки откройте ярлык **EduAI Audit**.
Для знакомства нажмите **«Попробовать пример»** или **«Попробовать сравнение»**, затем **«Запустить аудит»**.

This installer is built by GitHub Actions from the tagged source with pinned
dependencies. The workflow runs the test suite and checks both examples and
report downloads in the bundled runtime. `build-info.json` lists exact versions
and the source commit; the `.sha256` file contains the installer's checksum.

This is an unsigned preview. The installer wizard and uninstall sequence have
not been automatically tested. Real student data and prediction exports are not
included; sample records and scores are artificial.
