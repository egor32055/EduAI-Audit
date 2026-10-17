// Browser smoke check against the actual bundled executable, not Python sources.
const {chromium} = require(process.env.EDUAI_PLAYWRIGHT || 'playwright');
const fs = require('node:fs/promises');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch({headless: true,
    executablePath: path.join(process.env.PROGRAMFILES || 'C:/Program Files', 'Google/Chrome/Application/chrome.exe')});
  const page = await browser.newPage();
  page.setDefaultTimeout(30000);
  const errors = [];
  page.on('pageerror', error => errors.push(String(error)));
  const button = name => page.getByRole('button', {name, exact: true});
  const idle = async () => {
    await page.locator('[data-testid="stApp"][data-test-script-state="notRunning"]').waitFor();
    await page.waitForTimeout(400);
    await page.locator('[data-testid="stApp"][data-test-script-state="notRunning"]').waitFor();
  };
  const checkMetrics = async expected => {
    const actual = await page.locator('[data-testid="stMetricValue"]').allTextContents();
    if (actual.join('|') !== expected) throw Error(`Unexpected counts: ${actual}`);
  };
  const download = async name => {
    const pending = page.waitForEvent('download');
    await button(name).click();
    const file = await pending;
    const contents = await fs.readFile(await file.path());
    await idle();
    return contents;
  };
  try {
    await page.goto('http://127.0.0.1:8512/');
    await button('Try example').waitFor(); await idle();
    await button('Try example').click(); await button('Save settings JSON').waitFor(); await idle();
    await button('Run audit').click(); await button('Download full HTML report').waitFor(); await idle();
    await checkMetrics('16|4|2|5|2');
    const single = (await download('Download full HTML report')).toString('utf8');
    if ((single.match(/<svg /g) || []).length !== 4 || single.includes('<script')) throw Error('Invalid single report');
    await button('Try comparison example').click(); await idle();
    await page.getByLabel('Model B probability column', {exact: true}).waitFor();
    await button('Run audit').click(); await button('Download comparison tables ZIP').waitFor(); await idle();
    await checkMetrics('2|2|2|10');
    const language = page.getByLabel('Language / Язык', {exact: true});
    await language.click(); await language.press('ArrowDown'); await language.press('End'); await language.press('Enter');
    await button('Скачать HTML-отчёт сравнения').waitFor(); await idle();
    await checkMetrics('2|2|2|10');
    const comparison = (await download('Скачать HTML-отчёт сравнения')).toString('utf8');
    if (!comparison.includes('lang="ru"') || comparison.includes('<script') || (comparison.match(/<svg /g) || []).length !== 8) throw Error('Invalid comparison report');
    const archive = await download('Скачать таблицы сравнения ZIP');
    if (archive.readUInt32LE(0) !== 0x04034b50) throw Error('Invalid ZIP download');
    const settings = JSON.parse((await download('Сохранить настройки JSON')).toString('utf8'));
    if (settings.comparison_score_column !== 'dropout_probability_b' || settings.audit.focus_share !== .2) throw Error('Invalid example settings');
    if (errors.length) throw Error(errors.join('\n'));
    console.log('Bundled single/comparison examples, language switch, HTML, ZIP and settings verified.');
  } catch (error) {
    await page.screenshot({path: 'build/release-ui-error.png'});
    throw error;
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
