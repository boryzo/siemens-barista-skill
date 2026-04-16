#!/usr/bin/env python3
import argparse
import json
import os
import requests
import sys
import time
from urllib.parse import urlparse, parse_qs

# Configuration constants
CONFIG_FILE = os.path.expanduser("~/.siemens_barista.json")
BASE_URL = "https://api.home-connect.com/api"
OAUTH_AUTH_URL = "https://api.home-connect.com/security/oauth/authorize"
OAUTH_TOKEN_URL = "https://api.home-connect.com/security/oauth/token"
POWER_STATE_KEY = "BSH.Common.Setting.PowerState"
POWER_STATE_ON = "BSH.Common.EnumType.PowerState.On"
POWER_STATE_OFF = "BSH.Common.EnumType.PowerState.Off"
POWER_STATE_STANDBY = "BSH.Common.EnumType.PowerState.Standby"

def save_config(config):
    """Saves the configuration dictionary to a JSON file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def load_config():
    """Loads the configuration from the JSON file."""
    if not os.path.exists(CONFIG_FILE):
        print("❌ Error: No configuration found.")
        print("👉 Please run the setup first: python3 siemens-barista.py config")
        sys.exit(1)
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def get_headers(token):
    """Generates the required HTTP headers for the Home Connect API."""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.bsh.sdk.v1+json"
    }

def refresh_access_token(config):
    """Refreshes the OAuth access token using the stored refresh token."""
    print("🔄 Access token expired. Attempting to refresh silently...")
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": config["refresh_token"],
        "client_id": config["client_id"],
        "client_secret": config["client_secret"]
    }
    
    response = requests.post(OAUTH_TOKEN_URL, data=payload)
    
    if response.status_code != 200:
        print("❌ Failed to refresh token. The refresh token might have expired.")
        print("👉 Please run 'python3 siemens-barista.py config' to log in again.")
        sys.exit(1)
        
    new_tokens = response.json()
    config["access_token"] = new_tokens["access_token"]
    
    if "refresh_token" in new_tokens:
        config["refresh_token"] = new_tokens["refresh_token"]
        
    save_config(config)
    print("✅ Token refreshed successfully.")
    return config["access_token"]

def do_config():
    """Handles the OAuth 2.0 setup, authorization code flow, and identifying the coffee maker."""
    print("=== Siemens Barista OAuth 2.0 Setup ===")
    
    client_id = input("Enter your Client ID: ").strip()
    client_secret = input("Enter your Client Secret: ").strip()
    redirect_uri = input("Enter your Redirect URI (e.g., http://localhost): ").strip()

    auth_url = (f"{OAUTH_AUTH_URL}?client_id={client_id}&redirect_uri={redirect_uri}"
                "&response_type=code&scope=IdentifyAppliance%20CoffeeMaker")
    
    print("\n1️⃣  Please open the following URL in your web browser to log in and authorize this app:")
    print(f"\n{auth_url}\n")
    print("2️⃣  After logging in, your browser will redirect you. Paste the FULL redirected URL below.")
    
    redirected_url = input("3️⃣  Redirected URL: ").strip()

    try:
        parsed_url = urlparse(redirected_url)
        auth_code = parse_qs(parsed_url.query)['code'][0]
    except Exception:
        print("❌ Error: Could not extract authorization code from the URL.")
        sys.exit(1)

    print("\n🔐 Exchanging authorization code for tokens...")
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "code": auth_code
    }
    
    token_response = requests.post(OAUTH_TOKEN_URL, data=payload)
    if token_response.status_code != 200:
        print(f"❌ Failed to get tokens: {token_response.status_code} - {token_response.text}")
        sys.exit(1)
        
    tokens = token_response.json()
    access_token = tokens["access_token"]
    refresh_token = tokens.get("refresh_token")

    print("🔍 Looking for coffee makers in your home...")
    api_response = requests.get(f"{BASE_URL}/homeappliances", headers=get_headers(access_token))

    if api_response.status_code != 200:
        print(f"❌ API Error while fetching appliances: {api_response.status_code} - {api_response.text}")
        sys.exit(1)

    appliances = api_response.json().get("data", {}).get("homeappliances", [])
    coffee_makers = [app for app in appliances if app.get("type") == "CoffeeMaker"]

    if not coffee_makers:
        print("❌ No coffee maker found linked to this account.")
        sys.exit(1)

    ha_id = coffee_makers[0]["haId"]
    name = coffee_makers[0].get("name", "Siemens Coffee Maker")

    print(f"✅ Found coffee maker: {name} (ID: {ha_id})")

    config = {
        "client_id": client_id,
        "client_secret": client_secret,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "ha_id": ha_id
    }
    save_config(config)
    print(f"✅ OAuth setup complete! Configuration saved to {CONFIG_FILE}\n")

def prepare_machine(ha_id, token):
    """Checks if the machine is on. If not, sends the command to turn it on and waits."""
    url = f"{BASE_URL}/homeappliances/{ha_id}/settings/{POWER_STATE_KEY}"
    resp = requests.get(url, headers=get_headers(token))
    
    if resp.status_code == 401:
        return 401 # Signal to refresh token
        
    if resp.status_code == 200:
        state = resp.json().get('data', {}).get('value')
        if state != POWER_STATE_ON:
            print("🔌 Machine is off or in standby. Turning it on...")
            put_resp = set_power_state(ha_id, token, POWER_STATE_ON)
            if put_resp.status_code in [200, 204]:
                print("⏳ Waiting 15 seconds for the machine to boot up and rinse...")
                time.sleep(15)
            else:
                print(f"⚠️ Warning: Tried to turn on the machine, but got API error: {put_resp.text}")
    return 200

def set_power_state(ha_id, token, power_value):
    """Sets machine power state to a Home Connect enum value."""
    payload = {
        "data": {
            "key": POWER_STATE_KEY,
            "value": power_value
        }
    }
    return requests.put(
        f"{BASE_URL}/homeappliances/{ha_id}/settings/{POWER_STATE_KEY}",
        headers=get_headers(token),
        json=payload
    )

def set_machine_power(power_action):
    """CLI action to explicitly turn machine power on or off."""
    config = load_config()
    ha_id = config["ha_id"]
    token = config["access_token"]

    if power_action == "on":
        targets = [POWER_STATE_ON]
    else:
        # Some models expect Standby instead of Off.
        targets = [POWER_STATE_STANDBY, POWER_STATE_OFF]

    for index, target_state in enumerate(targets):
        print(f"⚙️ Setting machine power to: {target_state.split('.')[-1]}")
        response = set_power_state(ha_id, token, target_state)

        if response.status_code == 401:
            token = refresh_access_token(config)
            print("⚙️ Retrying power command with the new token...")
            response = set_power_state(ha_id, token, target_state)

        if response.status_code in [200, 204]:
            if power_action == "on":
                print("✅ Machine is now ON.")
            else:
                print("✅ Machine is now OFF/STANDBY.")
            return

        can_try_next = (index < len(targets) - 1) and (response.status_code in [400, 409])
        if can_try_next:
            print("ℹ️ Power mode not accepted by this model, trying alternative...")
            continue

        print(f"❌ Power command failed ({response.status_code}): {response.text}")
        return

def fetch_and_print_warnings(ha_id, token):
    """Fetches the machine status to find exact reasons for brewing failure (e.g. no water)."""
    resp = requests.get(f"{BASE_URL}/homeappliances/{ha_id}/status", headers=get_headers(token))
    if resp.status_code == 200:
        statuses = resp.json().get('data', {}).get('status', [])
        found_issues = False
        for status in statuses:
            key = status.get('key', '')
            value = status.get('value', '')
            # Print if it's a boolean True and related to warning/error/empty/full
            if value is True and any(word in key for word in ['Warning', 'Error', 'Empty', 'Full']):
                print(f"   ⚠️ Machine reported: {key.split('.')[-1]}")
                found_issues = True
        
        if not found_issues:
            print("   ℹ️ No specific warnings found in the machine's status API. It might be currently running another program.")

def send_brew_command(ha_id, token, beverage_key):
    """Executes the HTTP PUT request to start brewing."""
    payload = {
        "data": {
            "key": beverage_key,
            "options": []
        }
    }
    return requests.put(
        f"{BASE_URL}/homeappliances/{ha_id}/programs/active",
        headers=get_headers(token),
        json=payload
    )

def brew_coffee(beverage_key):
    """Main function to handle preparation, brewing logic, and intelligent error handling."""
    config = load_config()
    ha_id = config["ha_id"]
    token = config["access_token"]

    # 1. Prepare the machine (Turn on if needed)
    prep_status = prepare_machine(ha_id, token)
    if prep_status == 401:
        token = refresh_access_token(config)
        prepare_machine(ha_id, token)

    # 2. Send brewing command
    print("⚙️ Sending brewing command to the coffee maker...")
    response = send_brew_command(ha_id, token, beverage_key)

    if response.status_code == 401:
        # Just in case token expired right between preparation and brewing
        token = refresh_access_token(config)
        print("⚙️ Retrying brewing command with the new token...")
        response = send_brew_command(ha_id, token, beverage_key)

    # 3. Handle results
    if response.status_code in [200, 204]:
        print("☕ Success! Your beverage is now brewing.")
    elif response.status_code == 409:
        error_data = {}
        try:
            error_data = response.json().get("error", {})
        except Exception:
            pass
        
        err_key = error_data.get("key", "UnknownError")
        err_desc = error_data.get("description", "Action cannot be executed.")
        
        print(f"\n❌ Error (409): {err_desc}")
        print("👉 DIAGNOSTIC:")
        
        # Siemens specific safety feature block
        if "RemoteControlStartNotAllowed" in err_key or "RemoteControlStartNotAllowed" in err_desc:
            print("   🔴 Remote Start is disabled! For safety, you must press the physical 'Remote Start' button on your coffee maker first.")
        else:
            # Check detailed status (water, beans, tray)
            fetch_and_print_warnings(ha_id, token)
            
    else:
        print(f"❌ API Error ({response.status_code}): {response.text}")

# Map of CLI drink names → actual Home Connect program keys (discovered from this machine)
DRINK_MAP = {
    "caffe-creme":      "ConsumerProducts.CoffeeMaker.Program.Beverage.CaffeGrande",
    "espresso":         "ConsumerProducts.CoffeeMaker.Program.Beverage.Espresso",
    "espresso-doppio":  "ConsumerProducts.CoffeeMaker.Program.Beverage.EspressoDoppio",
    "coffee":           "ConsumerProducts.CoffeeMaker.Program.Beverage.Coffee",
    "caffe-grande":     "ConsumerProducts.CoffeeMaker.Program.Beverage.CaffeGrande",
    "xl-coffee":        "ConsumerProducts.CoffeeMaker.Program.Beverage.XLCoffee",
    "cappuccino":       "ConsumerProducts.CoffeeMaker.Program.Beverage.Cappuccino",
    "latte-macchiato":  "ConsumerProducts.CoffeeMaker.Program.Beverage.LatteMacchiato",
    "caffe-latte":      "ConsumerProducts.CoffeeMaker.Program.Beverage.CaffeLatte",
    "milk-froth":       "ConsumerProducts.CoffeeMaker.Program.Beverage.MilkFroth",
    "warm-milk":        "ConsumerProducts.CoffeeMaker.Program.Beverage.WarmMilk",
    "hot-water":        "ConsumerProducts.CoffeeMaker.Program.Beverage.HotWater",
    "ristretto":        "ConsumerProducts.CoffeeMaker.Program.Beverage.Ristretto",
    "espresso-macchiato": "ConsumerProducts.CoffeeMaker.Program.Beverage.EspressoMacchiato",
    "americano":        "ConsumerProducts.CoffeeMaker.Program.CoffeeWorld.Americano",
    "flat-white":       "ConsumerProducts.CoffeeMaker.Program.CoffeeWorld.FlatWhite",
    "cortado":          "ConsumerProducts.CoffeeMaker.Program.CoffeeWorld.Cortado",
}

def main():
    parser = argparse.ArgumentParser(description="CLI tool to control a Siemens Coffee Maker via Home Connect API with OAuth 2.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: config
    subparsers.add_parser("config", help="Set up OAuth tokens and automatically find your coffee maker")

    # Subcommand: create
    create_parser = subparsers.add_parser("create", help="Command the machine to brew a beverage")
    create_parser.add_argument(
        "drink",
        choices=sorted(DRINK_MAP.keys()),
        help="The type of drink to brew"
    )

    # Subcommand: on
    subparsers.add_parser("on", help="Turn the coffee machine on")

    # Subcommand: off
    subparsers.add_parser("off", help="Turn the coffee machine off/standby")

    args = parser.parse_args()

    if args.command == "config":
        do_config()
    elif args.command == "create":
        program_key = DRINK_MAP[args.drink]
        print(f"☕ Brewing: {args.drink} → {program_key}")
        brew_coffee(program_key)
    elif args.command == "on":
        set_machine_power("on")
    elif args.command == "off":
        set_machine_power("off")

if __name__ == "__main__":
    main()
