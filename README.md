# Розгортання Threads Search Scraper + Telegram Bot на macOS

Ця інструкція описує повний процес розгортання проєкту на iMac з macOS, щоб цей комп'ютер працював як постійний хост для Telegram-бота і парсера Threads. Для роботи парсера потрібні Python, Playwright і локально встановлений Chromium, оскільки Playwright відкриває сторінки Threads і збирає дані з відповіді браузера.[1][2]

## Що потрібно перед початком

Потрібно підготувати:

- iMac або інший Mac на macOS, який може бути увімкнений постійно.
- Доступ до GitHub-репозиторію з кодом.
- Telegram bot token.
- Файл `auth.json` або можливість створити його на цьому Mac після входу в Threads.
- Доступ до акаунта Threads, через який буде виконуватись пошук.
- За потреби — лог-групу в Telegram, якщо потрібні технічні логи.[3][2]

## Рекомендована структура папок

Рекомендується використати таку директорію:

```text
/Users/<MAC_USERNAME>/apps/threads-search-scraper/
```

У цій папці мають бути:

- Python-файли проєкту.
- `auth.json`.
- `keywords.json`.
- папка `output/`.
- `telegram_bot.py`.
- `threads_scraper.py`.
- допоміжні модулі (`collector.py`, `payload_parser.py`, `state_manager.py` тощо).

## Крок 1. Встановити Homebrew

Відкрити Terminal і виконати:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Перевірити:

```bash
brew --version
```

Homebrew — найзручніший спосіб встановити Python на macOS для такого сценарію.[4]

## Крок 2. Встановити Python

Виконати:

```bash
brew install python
```

Перевірити:

```bash
python3 --version
pip3 --version
```

Playwright для Python підтримує Python 3.8+ на macOS.[1]

## Крок 3. Клонувати проєкт з GitHub

```bash
mkdir -p ~/apps
cd ~/apps
git clone <URL_ТВОГО_REPO> threads-search-scraper
cd threads-search-scraper
```

Якщо проєкт уже скопійований, оновити його можна так:

```bash
git pull
```

## Крок 4. Створити virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Virtual environment ізолює залежності проєкту і є стандартним способом роботи з Python-проєктами.[5][4]

## Крок 5. Встановити залежності Python

Якщо в репозиторії є `requirements.txt`, виконати:

```bash
pip install -r requirements.txt
```

Якщо файлу ще немає, мінімально треба встановити:

```bash
pip install playwright httpx
```

Якщо є додаткові бібліотеки — їх також треба додати в `requirements.txt`, щоб на іншому Mac усе ставилось однією командою.

## Крок 6. Встановити браузер для Playwright

Після встановлення Python-пакета `playwright` треба окремо завантажити Chromium:

```bash
python -m playwright install chromium
```

Це обов'язковий крок, тому що Playwright зберігає браузери окремо від Python-пакетів.[2]

За потреби можна встановити всі підтримувані браузери:

```bash
python -m playwright install
```

## Крок 7. Налаштувати `constants.py`

Приклад базового конфігу:

```python
DEFAULT_AUTH_FILE = "auth.json"
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_STATE_FILE = "search_state.json"
DEFAULT_MAX_POSTS_NEW_KEYWORD = 10
DEFAULT_SCROLL_ATTEMPTS = 3
THREADS_SEARCH_URL = "https://www.threads.net/search"

# Telegram
TELEGRAM_BOT_TOKEN = "<BOT_TOKEN>"
KEYWORDS_FILE = "keywords.json"
LOG_CHAT_ID = "-5160568832"
SEND_RUN_LOG_TO_USER = False
SEND_SUMMARY_TO_USER = True
```

Для Telegram-груп chat id може бути від’ємним — це нормально для групових чатів.[6][7]

## Крок 8. Створити `keywords.json`

Приклад:

```json
[
  "тцк",
  "azure",
  "леді гага"
]
```

## Крок 9. Базове налаштування Threads-сесії

Для роботи парсера треба, щоб Playwright мав збережену авторизовану сесію Threads. Найзручніше — один раз увійти в акаунт і зберегти стан браузера у файл `auth.json`. Playwright підтримує збереження стану сесії через storage state, що дозволяє використовувати повторно cookies і локальний стан під час наступних запусків.[1][2]

### Варіант A — якщо у проєкті вже є `login_and_save_session.py`

Запустити:

```bash
source .venv/bin/activate
python login_and_save_session.py
```

Або, якщо файл називається інакше, використати його реальну назву, наприклад:

```bash
python login_and_save_session-4.py
```

Далі:

1. Відкриється браузер.
2. Увійти в Threads/Instagram-акаунт вручну.
3. Дочекатися повного входу.
4. Після завершення має з'явитися файл `auth.json` у корені проєкту.

### Варіант B — якщо треба вручну підготувати логін на основі Playwright

Якщо окремий скрипт логіну не працює або його ще треба адаптувати, логіка така:

- відкрити сторінку Threads через Playwright;
- виконати ручний логін;
- зберегти browser storage state у `auth.json`.

Саме цей файл потім буде використовуватись скрейпером для авторизованих запусків.[1]

### Як перевірити, що сесія збережена

Переконатися, що файл існує:

```bash
ls -la auth.json
```

Також можна виконати перевірочний скрипт сесії, якщо він є в проєкті:

```bash
python check_session.py
```

або, якщо у тебе зараз така назва файла:

```bash
python check_session-13.py
```

Якщо `auth.json` протухне, потрібно буде знову пройти логін і пересохранити сесію.

## Крок 10. Перевірити ручний запуск скрейпера

Після збереження `auth.json` виконати тест:

```bash
source .venv/bin/activate
python threads_scraper.py --keywords "azure" --max-posts-new 1 --scroll-attempts 1
```

Що має статись:

- відкриється Threads через Playwright;
- буде виконано пошук;
- результати запишуться у `output/`;
- оновиться `output/search_state.json`;
- збережеться `output/threads_search_summary.json`.[2]

## Крок 11. Перевірити ручний запуск Telegram-бота

Запуск:

```bash
source .venv/bin/activate
python telegram_bot.py
```

Далі у Telegram:

1. Відкрити чат з ботом.
2. Написати `/start`.
3. За потреби додати keyword.
4. Натиснути `Run`.

Бот використовує long polling через `getUpdates`, що підходить для локального або домашнього “сервера” на Mac.[3][8]

## Крок 12. Автозапуск бота після входу в macOS

На macOS для фонового запуску користувацьких процесів стандартно використовують `launchd` через LaunchAgent.[9][10]

Створити папку, якщо її немає:

```bash
mkdir -p ~/Library/LaunchAgents
```

Створити файл:

```text
~/Library/LaunchAgents/com.threadsparser.bot.plist
```

Вміст файла:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.threadsparser.bot</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/<MAC_USERNAME>/apps/threads-search-scraper/.venv/bin/python</string>
        <string>/Users/<MAC_USERNAME>/apps/threads-search-scraper/telegram_bot.py</string>
    </array>

    <key>WorkingDirectory</key>
    <string>/Users/<MAC_USERNAME>/apps/threads-search-scraper</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/<MAC_USERNAME>/apps/threads-search-scraper/output/launchd_stdout.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/<MAC_USERNAME>/apps/threads-search-scraper/output/launchd_stderr.log</string>
</dict>
</plist>
```

Завантажити агент:

```bash
launchctl unload ~/Library/LaunchAgents/com.threadsparser.bot.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/com.threadsparser.bot.plist
```

Перевірити, чи він є в системі:

```bash
launchctl list | grep threadsparser
```

LaunchAgent — стандартний спосіб запускати користувацький Python-процес автоматично після входу в систему на macOS.[9][10][11]

## Крок 13. Оновлення коду в майбутньому

```bash
cd ~/apps/threads-search-scraper
git pull
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
launchctl unload ~/Library/LaunchAgents/com.threadsparser.bot.plist
launchctl load ~/Library/LaunchAgents/com.threadsparser.bot.plist
```

Повторний `playwright install chromium` є нормальним і допомагає переконатися, що браузерні бінарники залишились доступними після оновлень.[2]

## Типові проблеми

### `python3: command not found`

Python не встановлений або не доданий у PATH. Треба встановити його через Homebrew і перевірити командою `python3 --version`.[4][1]

### `ModuleNotFoundError`

Не активовано `.venv` або не встановлені залежності. Треба активувати virtual environment і виконати `pip install -r requirements.txt`.

### `playwright: command not found`

Треба запускати Playwright через активне Python-оточення:

```bash
python -m playwright install chromium
```

Це дозволяє уникнути проблем із PATH.[2][12]

### Playwright не запускає браузер

Потрібно повторно встановити Chromium:

```bash
python -m playwright install chromium
```

Якщо macOS блокує запуск, дозволити його в Security & Privacy і повторити запуск. Playwright використовує локально встановлений Chromium для автоматизації.[2][13]

### Бот пише `chat not found`

Бот не доданий у потрібну групу, вказано неправильний `LOG_CHAT_ID`, або Telegram-група має інший id. Для групових чатів від’ємний id — це нормально.[6][7][3]

### Користувач не отримує повідомлення від бота

Користувач повинен сам відкрити чат із ботом і натиснути `/start`. Telegram-бот не може першим написати в приватний чат користувачу без його взаємодії.[14][3]

### `auth.json` перестав працювати

Сесія протухла або була скинута. Треба заново пройти логін через скрипт збереження сесії і пересоздати `auth.json`.

## Що обов'язково передати людині для розгортання

Перед передачею проєкту треба підготувати:

- код у GitHub-репозиторії;
- `requirements.txt`;
- інструкцію з цього файла;
- приклад `keywords.json`;
- приклад `constants.py` без реального токена;
- окремо передати реальний `auth.json` або разом пройти створення сесії на його Mac.

Не варто комітити в публічний репозиторій реальний Telegram token або чинний `auth.json`.

## Рекомендований порядок передачі

1. Залити актуальний код у GitHub.
2. Додати `requirements.txt`, `.gitignore`, приклади конфігів.
3. Передати посилання на репозиторій.
4. Окремо передати `auth.json` або налаштувати логін на його Mac.
5. Разом виконати перший ручний запуск.
6. Лише після успішного ручного тесту включати LaunchAgent.

Такий порядок безпечніший, тому що спочатку перевіряється середовище і логін у Threads, а вже потім — фоновий сервіс.[9][2]



# Швидкі команди для запуску і перевірки

Нижче зібрані основні команди для запуску, перевірки та базового налаштування проєкту без пошуку по повному README.

## 1) Перейти в папку проєкту

```bash
cd ~/apps/threads-search-scraper
```

## 2) Активувати virtual environment

```bash
source .venv/bin/activate
```

## 3) Встановити залежності

```bash
pip install -r requirements.txt
```

## 4) Встановити Chromium для Playwright

```bash
python -m playwright install chromium
```

## 5) Зберегти сесію Threads

Якщо є скрипт логіну:

```bash
python login_and_save_session-4.py
```

Що робити далі:
- відкриється браузер;
- увійти в Threads / Instagram;
- дочекатися завершення;
- переконатися, що створився `auth.json`.

## 6) Перевірити, чи існує і працює сесія

```bash
python check_session-13.py
```

Коментар:
- це перевірка, чи файл сесії існує і чи його можна використати для авторизованого доступу.

## 7) Перевірити, що `auth.json` реально є

```bash
ls -la auth.json
```

## 8) Перевірити ручний запуск скрейпера

```bash
python threads_scraper-10.py --keywords "azure" --max-posts-new 1 --scroll-attempts 1
```

Або, якщо у локальному репозиторії вже файл перейменований у нормальну назву:

```bash
python threads_scraper.py --keywords "azure" --max-posts-new 1 --scroll-attempts 1
```

## 9) Перевірити, що summary створився

```bash
ls -la output/threads_search_summary.json
```

## 10) Перевірити, що state створився

```bash
ls -la output/search_state.json
```

## 11) Запустити Telegram-бота вручну

```bash
python telegram_bot.py
```

Після цього в Telegram:
- відкрити чат з ботом;
- написати `/start`;
- додати keyword;
- натиснути `Run`.

## 12) Перевірити keywords-файл

```bash
cat keywords.json
```

## 13) Оновити код з GitHub

```bash
git pull
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## 14) Перезапустити LaunchAgent після оновлення

```bash
launchctl unload ~/Library/LaunchAgents/com.threadsparser.bot.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/com.threadsparser.bot.plist
```

## 15) Перевірити, чи LaunchAgent запущений

```bash
launchctl list | grep threadsparser
```

## 16) Перевірити лог стандартного виводу

```bash
tail -n 100 output/launchd_stdout.log
```

## 17) Перевірити лог помилок

```bash
tail -n 100 output/launchd_stderr.log
```

## 18) Типовий повний сценарій першого запуску

```bash
cd ~/apps/threads-search-scraper
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python login_and_save_session-4.py
python check_session-13.py
python threads_scraper-10.py --keywords "azure" --max-posts-new 1 --scroll-attempts 1
python telegram_bot.py
```

## 19) Якщо у репозиторії будуть нормальні імена файлів

Після перейменування файлів команди бажано використовувати такі:

```bash
python login_and_save_session.py
python check_session.py
python threads_scraper.py --keywords "azure" --max-posts-new 1 --scroll-attempts 1
python telegram_bot.py
```

## 20) Швидка перевірка, що все готово

Ознаки, що налаштування коректне:
- `python3 --version` працює;
- `.venv` активується без помилок;
- `pip install -r requirements.txt` проходить успішно;
- `python -m playwright install chromium` завершується без помилок;
- існує `auth.json`;
- `check_session-13.py` не падає;
- `threads_scraper.py` або `threads_scraper-10.py` створює файли в `output/`;
- бот відповідає на `/start`.