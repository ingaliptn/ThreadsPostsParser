# Розгортання Threads Search Scraper + Telegram Bot на macOS

Ця інструкція описує повний процес розгортання проєкту, щоб комп'ютер працював як постійний хост для Telegram-бота і парсера Threads. Для роботи парсера потрібні Python, Playwright і локально встановлений Chromium, оскільки Playwright відкриває сторінки Threads і збирає дані з відповіді браузера.[1][2]

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

## Крок 7. Базове налаштування Threads-сесії

Для роботи парсера треба, щоб Playwright мав збережену авторизовану сесію Threads. Найзручніше — один раз увійти в акаунт і зберегти стан браузера у файл `auth.json`. Playwright підтримує збереження стану сесії через storage state, що дозволяє використовувати повторно cookies і локальний стан під час наступних запусків.[1][2]

### Якщо у проєкті вже є `login_and_save_session.py`

Запустити:

```bash
source .venv/bin/activate
python login_and_save_session.py
```

Далі:

1. Відкриється браузер.
2. Увійти в Threads/Instagram-акаунт вручну.
3. Дочекатися повного входу.
4. Після завершення має з'явитися файл `auth.json` у корені проєкту.

### Як перевірити, що сесія збережена

Переконатися, що файл існує:

```bash
ls -la auth.json
```

Також можна виконати перевірочний скрипт сесії, якщо він є в проєкті:

```bash
python check_session.py
```

Якщо `auth.json` протухне, потрібно буде знову пройти логін і пересохранити сесію.

## Крок 8. Перевірити ручний запуск Telegram-бота

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

Бот використовує long polling через `getUpdates`, що підходить для локального або домашнього “сервера”.[3][8]

## Крок 9. Оновлення коду в майбутньому

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

Якщо OS блокує запуск, дозволити його в Security & Privacy і повторити запуск. Playwright використовує локально встановлений Chromium для автоматизації.[2][13]

### Бот пише `chat not found`

Бот не доданий у потрібну групу, вказано неправильний `LOG_CHAT_ID`, або Telegram-група має інший id. Для групових чатів від’ємний id — це нормально.[6][7][3]

### Користувач не отримує повідомлення від бота

Користувач повинен сам відкрити чат із ботом і натиснути `/start`. Telegram-бот не може першим написати в приватний чат користувачу без його взаємодії.[14][3]

### `auth.json` перестав працювати

Сесія протухла або була скинута. Треба заново пройти логін через скрипт збереження сесії і пересоздати `auth.json`.

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

## 5) Запустити Telegram-бота вручну

```bash
python telegram_bot.py
```

Після цього в Telegram:
- відкрити чат з ботом;
- написати `/start`;
- додати keyword;
- натиснути `Run`.

## 6) Перевірити keywords-файл

```bash
cat keywords.json
```

## 7) Оновити код з GitHub

```bash
git pull
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

##  Швидка перевірка, що все готово

Ознаки, що налаштування коректне:
- `python3 --version` працює;
- `.venv` активується без помилок;
- `pip install -r requirements.txt` проходить успішно;
- `python -m playwright install chromium` завершується без помилок;
- існує `auth.json`;
- `check_session.py` не падає;
- `threads_scraper.py` створює файли в `output/`;
- бот відповідає на `/start`.