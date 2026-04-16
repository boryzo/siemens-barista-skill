# Siemens Barista CLI (Home Connect)

A simple Python CLI tool to control your Siemens Coffee Maker via the Home Connect API. This script is designed to be used as a backend for AI agents (like Open Claw skills) or manual terminal usage. It supports **OAuth 2.0 with automatic token refreshing**, so you only need to log in once.

## Features
- **OAuth 2.0 Flow**: Secure authorization using Client ID and Secret.
- **Persistent Sessions**: Automatically refreshes expired tokens in the background.
- **Single Command Brewing**: Just run `create caffe-creme` to start your coffee.
- **Auto-Discovery**: Automatically finds your coffee machine in your Home Connect account.

## Prerequisites
- Python 3.x
- `requests` library:
  ```bash
  pip install requests

  Setup Instructions
1. Create a Home Connect Developer Account
To use the API, you must register your "app" in the Home Connect system:

Go to the Home Connect Developer Portal.

Log in (preferably with the same email you use for your mobile app).

Go to Applications -> Register Application.

Fill in the form:

Application ID: SiemensBaristaCLI (or any name).

OAuth Flow: Select Authorization Code Grant Flow.

Redirect URI: Enter http://localhost.

Home Connect User Account for Testing: Your mobile app email.

Save and copy your Client ID and Client Secret.

2. Initial Configuration
Run the script with the config command to link your account:

Bash
python3 siemens-barista.py config
Enter your Client ID and Client Secret when prompted.

The script will provide a URL. Open it in your browser.

Log in to your Home Connect account and authorize the app.

After authorization, you will be redirected to http://localhost/?code=....

Copy the entire URL from your browser's address bar and paste it back into the terminal.

The script will now save your credentials and machine ID to ~/.siemens_barista.json.

Usage
Brew Caffe Crema
To start brewing your favorite coffee, run:

Bash
python3 siemens-barista.py create caffe-creme
Automation / Open Claw Skills
Since the script handles token refreshing automatically, you can simply call the command above from any automation tool or LLM skill. If the session expires, the script will silently update the tokens and proceed with the brewing command.

OpenClaw skill (added in this repo)

- Skill file: `skills/siemens_barista/SKILL.md`
- OpenClaw should load workspace skills from `<workspace>/skills`, so this skill is ready to use from this project directory.
- Supported actions via skill:
  - `python3 siemens-barista.py on`
  - `python3 siemens-barista.py off`
  - `python3 siemens-barista.py create <drink>`
- If skills were already loaded in your session, start a new chat/session (or reload skills) so OpenClaw picks up the new skill.

Error Handling
401 Unauthorized: The script automatically tries to refresh the token. If it fails, run config again.

406 Not Acceptable: This usually means a header mismatch. The script is configured to use application/vnd.bsh.sdk.v1+json.

409 Conflict: The machine is busy, turned off, or needs maintenance (water/beans/tray).

License
MIT License


---

### Krótkie podsumowanie tego, co zbudowaliśmy:

1.  **Plik `siemens-barista.py`**: Główne narzędzie.
    * **Mechanizm OAuth 2.0**: Skrypt nie trzyma tylko hasła, ale bezpieczne tokeny.
    * **Refresh Token**: Skrypt potrafi sam poprosić o nowy klucz dostępu, gdy stary wygaśnie, dzięki czemu "raz skonfigurowany, działa wiecznie".
    * **Nagłówki SDK**: Ustawiliśmy `Accept: application/vnd.bsh.sdk.v1+json`, czyli dokładnie to, czego wymaga Twój ekspres.
2.  **Plik `~/.siemens_barista.json`**: Tu skrypt przechowuje Twoje ID ekspresu i klucze. Nie musisz go edytować ręcznie.
3.  **Integracja**: Komenda `python3 siemens-barista.py create caffe-creme` jest idealna dla Open Claw, bo nie wymaga interakcji z użytkownikiem po pierwszym ustawieniu.

Teraz wystarczy, że upewnisz się, że funkcja `get_headers` ma to poprawione `sdk.v1` i możesz parzyć kawę! ☕🚀
