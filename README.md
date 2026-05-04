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


////////////////////////////////////////////////////////////////////////////////////////////////////////


# Threads Search Scraper + Telegram Bot: macOS Deployment Guide

This guide describes how to take the project from GitHub and deploy it on an iMac running macOS so the machine acts as the always-on host for the Threads parser and Telegram bot.[1][2]

## What this project needs

The project depends on Python 3.8+ and Playwright with a Chromium browser installed locally, because the scraper uses Playwright to open Threads search pages and collect responses.[1][2]

The deployment machine should have:

- An iMac on macOS that can stay powered on and connected to the internet.
- Access to the GitHub repository.
- A Telegram bot token.
- A valid `auth.json` session file for Threads.
- Permission for the bot to send messages to users and, if enabled, to the log group.[3][2]

## Recommended project layout

Create a working folder like this on the iMac:

```text
/Users/<MAC_USERNAME>/apps/threads-search-scraper/
```

Inside it, the project should contain the scraper files, `auth.json`, `keywords.json`, `output/`, and the Python modules used by the bot and scraper.[4]

## Step 1: Install Homebrew

Open Terminal and install Homebrew if it is not already installed:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Verify installation:

```bash
brew --version
```

Homebrew is the easiest way to install Python on macOS for this setup.[5]

## Step 2: Install Python

Install Python with Homebrew:

```bash
brew install python
```

Verify:

```bash
python3 --version
pip3 --version
```

Playwright for Python supports Python 3.8 or higher on macOS.[1]

## Step 3: Clone the repository

Go to the target folder and clone the project:

```bash
mkdir -p ~/apps
cd ~/apps
git clone <YOUR_GITHUB_REPO_URL> threads-search-scraper
cd threads-search-scraper
```

If the repository is already cloned, pull the latest version:

```bash
git pull
```

## Step 4: Create a virtual environment

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

A virtual environment isolates package versions for the project and is the recommended way to manage Python dependencies for Playwright projects.[6][5]

## Step 5: Install Python dependencies

If the repository has a `requirements.txt`, run:

```bash
pip install -r requirements.txt
```

If it does not, install the core dependencies manually:

```bash
pip install playwright httpx
```

If the project also uses other libraries, add them to `requirements.txt` and reinstall from that file for consistency.

## Step 6: Install Playwright browser binaries

Install Chromium for Playwright:

```bash
python -m playwright install chromium
```

Playwright stores browser binaries separately and they must be installed after the Python package itself.[2]

If needed, install all Playwright browsers instead:

```bash
python -m playwright install
```

## Step 7: Add project runtime files

Place the following files in the project root:

- `auth.json` — Threads logged-in browser session.
- `keywords.json` — array of keywords, for example:

```json
[
  "тцк",
  "azure",
  "леді гага"
]
```

- `constants.py` configured with the bot token and desired options.

Example configuration:

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

`LOG_CHAT_ID` can be a negative number if it is a Telegram group chat id, which is normal for group chats.[7][8]

## Step 8: Test the scraper manually

Activate the virtual environment and run a manual scraper test:

```bash
source .venv/bin/activate
python threads_scraper.py --keywords "azure" --max-posts-new 1 --scroll-attempts 1
```

Expected result:

- The script opens Threads through Playwright.
- It writes JSON results to the `output/` folder.
- It updates `output/search_state.json`.
- It writes `output/threads_search_summary.json`.[4][2]

## Step 9: Test the Telegram bot manually

Run the bot:

```bash
source .venv/bin/activate
python telegram_bot.py
```

Then in Telegram:

1. Open the bot chat.
2. Press `/start`.
3. Add a test keyword if needed.
4. Press `Run`.

The current implementation uses Telegram long polling via `getUpdates`, which is suitable for a simple always-on bot on a personal machine.[3][9]

## Step 10: Keep the bot running after login

On macOS, the standard way to run a user process automatically is a LaunchAgent via `launchd`.[10][11]

Create the folder if needed:

```bash
mkdir -p ~/Library/LaunchAgents
```

Create a file:

```text
~/Library/LaunchAgents/com.threadsparser.bot.plist
```

Use this template and replace `<MAC_USERNAME>` with the real macOS username:

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

Load it:

```bash
launchctl unload ~/Library/LaunchAgents/com.threadsparser.bot.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/com.threadsparser.bot.plist
```

Check status:

```bash
launchctl list | grep threadsparser
```

LaunchAgents are the normal macOS way to keep a user-scoped background process running after login.[10][11][12]

## Updating the code later

To update the project on the iMac:

```bash
cd ~/apps/threads-search-scraper
git pull
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
launchctl unload ~/Library/LaunchAgents/com.threadsparser.bot.plist
launchctl load ~/Library/LaunchAgents/com.threadsparser.bot.plist
```

Re-running `playwright install chromium` is safe and ensures the browser binary remains present after dependency changes.[2]

## Troubleshooting

### `python3: command not found`

Python is not installed or not in PATH. Install it with Homebrew and verify with `python3 --version`.[5][1]

### `ModuleNotFoundError`

The virtual environment is not activated or dependencies were not installed. Activate `.venv` and run `pip install -r requirements.txt`.

### `playwright: command not found`

The Python package may not be installed in the active environment. Use:

```bash
python -m playwright install chromium
```

This runs Playwright from the current Python environment and avoids PATH issues.[2][13]

### Browser does not launch

Playwright requires its managed browser binaries to be installed locally. Re-run:

```bash
python -m playwright install chromium
```

If macOS blocks first launch, allow the app in system security settings and retry. Playwright uses a local Chromium binary for automation.[2][14]

### Telegram log chat returns `chat not found`

The bot is not in the target group, the group id is wrong, or the bot does not have permission to post there. Group chat ids can be negative, which is expected.[7][8][3]

### The bot works, but no results are sent to a user

The user must have started the bot chat first. Telegram bots cannot freely open a private chat with a user before the user interacts with the bot.[15][3]

## Packaging checklist for handoff

Before sending the project to the iMac owner, make sure the repository contains:

- Source code files.
- `requirements.txt`.
- Example or template `keywords.json`.
- This deployment guide.
- A note explaining how to provide `auth.json` securely.

Do not commit a real bot token or a personal `auth.json` into a public repository.

## Recommended handoff sequence

1. Push the latest working code to GitHub.
2. Add `requirements.txt` if it is missing.
3. Add this guide to the repository root as `README_DEPLOY_MACOS.md`.
4. Send the repository URL to the iMac owner.
5. Send `auth.json` securely outside GitHub.
6. Walk through the first manual launch together.
7. Enable LaunchAgent only after the manual run works.

This two-stage approach reduces setup risk because it separates environment problems from background-service problems.[10][2]