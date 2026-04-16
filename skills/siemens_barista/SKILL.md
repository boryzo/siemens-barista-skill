---
name: siemens_barista
description: Control a Siemens coffee machine (power on/off and brew drinks) using the local siemens-barista.py CLI.
metadata: {"openclaw":{"requires":{"bins":["python3"]}}}
---

# Siemens Barista

Use this skill when the user wants to control the Siemens coffee machine.

Command path

- Script: `{baseDir}/scripts/siemens-barista.py`

Supported actions

- Turn machine on: `python3 {baseDir}/scripts/siemens-barista.py on`
- Turn machine off: `python3 {baseDir}/scripts/siemens-barista.py off`
- Brew drink: `python3 {baseDir}/scripts/siemens-barista.py create <drink>`

Supported `<drink>` values

- `americano`, `caffe-creme`, `caffe-grande`, `caffe-latte`, `cappuccino`, `coffee`, `cortado`, `espresso`, `espresso-doppio`, `espresso-macchiato`, `flat-white`, `hot-water`, `latte-macchiato`, `milk-froth`, `ristretto`, `warm-milk`, `xl-coffee`

Behavior rules

- If the user asks to "make coffee" without specifying a drink, use `espresso`.
- If `~/.siemens_barista.json` is missing or the command output asks for setup, tell the user to run: `python3 {baseDir}/scripts/siemens-barista.py config`.
- Execute only one requested machine action at a time unless the user explicitly asks for a sequence.
- For `create <drink>`, first confirm a cup is under the spout unless the user already stated it.
- Treat `filiżanka`, `kubek`, `szklanka`, and `cup` as valid confirmation words.
- If not confirmed, ask: `Czy pod wylewka stoi juz filizanka/kubek/szklanka?`
