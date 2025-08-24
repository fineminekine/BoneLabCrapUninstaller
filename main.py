import shutil
import requests
import os
import json
import tkinter as tk
from tkinter import filedialog

bonelabAPI = "https://g-3809.modapi.io/v1"

bold = "\033[1m"
colourBlack = "\033[30m"
colourRed = "\033[31m"
colourGreen = "\033[32m"
colourYellow = "\033[33m"
backgroundWhite = "\033[47m"
colourReset = "\033[0m"


def grabJSON(name):
    if os.path.exists(name):
        with open(name, "r") as f:
            x = json.load(f)
            return x
    return None


def printMenu():
    print("\033c", end="")
    user = grabJSON("user.json")
    if user:
        print(
            colourGreen
            + f"Logged in as {user['username']} ({user['profileURL']})"
            + colourReset
        )
    subscriptions = grabJSON("subscriptions.json")
    if subscriptions:
        print(
            colourGreen + f"Found {len(subscriptions)} subscribed mods." + colourReset
        )
    else:
        print(
            colourRed
            + "No subscribed mods found, please generate a list!"
            + colourReset
        )
    installedMods = grabJSON("installedMods.json")
    if installedMods:
        print(colourGreen + f"Found {len(installedMods)} installed mods." + colourReset)
    else:
        print(
            colourRed + "No installed mods found, please generate a list!" + colourReset
        )
    print("Bonelab Storage Saver")
    print("1. Get Subscribed Mods")
    print("2. Get Installed Mods")
    print("3. Delete Unsubscribed Mods")
    print("4. Exit")
    return input("Choose an option (1-4): ")


def setupUserConfig():
    if not os.path.exists("user.json"):
        root = tk.Tk()
        root.withdraw()
        modsPath = filedialog.askdirectory(title="Select Mods Directory")
        OAuth2 = input("Enter your OAuth2 token (https://mod.io/me/access): ")
        r = requests.get(
            bonelabAPI + "/me", headers={"Authorization": "Bearer " + OAuth2}
        )
        responseJson = r.json()
        user = {
            "modsPath": modsPath,
            "OAuth2": OAuth2,
            "username": responseJson["username"],
            "profileURL": responseJson["profile_url"],
        }
        with open("user.json", "w") as f:
            json.dump(user, f, indent=4)
    return True


def getSubscribedMods():
    if os.path.exists("subscriptions.json"):
        ask = input(
            "subscriptions.json already exists. Do you want to overwrite it? (y/N): "
        )
        if not ask.lower() == "y":
            _ = input("Cancelled! Press Enter to continue...")
            return

    user = grabJSON("user.json")
    if not user:
        print("User not found.")
        return

    getBLSubscriptions = "/me/subscribed?game_id=3809"
    requestURL = bonelabAPI + getBLSubscriptions
    r = requests.get(requestURL, headers={"Authorization": "Bearer " + user["OAuth2"]})
    responseJson = r.json()
    totalMods = responseJson["result_total"]
    numPages = (totalMods + 99) // 100
    print(f"Total Mods: {totalMods}")

    allMods = []
    for offset in range(0, numPages):
        print(f"Loading page {offset + 1}...")
        paginatedUrl = requestURL + f"&_offset={offset * 100}"
        r = requests.get(
            paginatedUrl, headers={"Authorization": "Bearer " + user["OAuth2"]}
        )
        pageData = r.json()
        allMods.extend(pageData["data"])

    responseJson["data"] = allMods
    modInfo = [{"name": mod["name"], "id": mod["id"]} for mod in responseJson["data"]]
    with open("subscriptions.json", "w") as f:
        json.dump(modInfo, f, indent=4)


def getInstalledMods():
    if os.path.exists("installedMods.json"):
        ask = input(
            "installedMods.json already exists. Do you want to overwrite it? (y/N): "
        )
        if not ask.lower() == "y":
            _ = input("Cancelled! Press Enter to continue...")
            return

    with open("user.json", "r") as f:
        user = json.load(f)
        print("Scanning for installed mods...")
        installedMods = []
        for rootDir, dirs, files in os.walk(user["modsPath"]):
            for file in files:
                if file.endswith(".manifest"):
                    manifestPath = os.path.join(rootDir, file)
                    try:
                        with open(manifestPath, "r") as f:
                            manifest = json.load(f)
                            if "objects" in manifest and "3" in manifest["objects"]:
                                barcode = manifest["objects"]["2"]["barcode"]
                                modId = manifest["objects"]["3"]["modId"]
                                installedMods.append(
                                    {"barcode": barcode, "modId": modId}
                                )
                    except Exception as e:
                        print(f"Error reading manifest {manifestPath}: {e}")
                        continue
        print(f"Found {len(installedMods)} installed mods")
        with open("installedMods.json", "w") as f:
            json.dump(installedMods, f, indent=4)


def deleteUnsubscribedMods():
    if not os.path.exists("subscriptions.json"):
        print("No subscriptions found. Please get subscribed mods first.")
        _ = input("Press Enter to continue...")
        return

    if not os.path.exists("installedMods.json"):
        print("No installed mods found. Please get installed mods first.")
        _ = input("Press Enter to continue...")
        return

    user = grabJSON("user.json")
    if not user:
        print("User config not found.")
        return

    with open("subscriptions.json", "r") as f:
        subscribedMods = {str(mod["id"]) for mod in json.load(f)}

    with open("installedMods.json", "r") as f:
        installedMods = json.load(f)

    # Find mods that are installed but not subscribed
    unsubscribedMods = [
        mod for mod in installedMods if str(mod["modId"]) not in subscribedMods
    ]

    if not unsubscribedMods:
        print("No unsubscribed mods found.")
        _ = input("Press Enter to continue...")
        return

    print(f"Found {len(unsubscribedMods)} unsubscribed mods to delete.")
    # Calculate total size of mods to be deleted
    totalSize = 0
    for mod in unsubscribedMods:
        barcode = mod["barcode"]
        modFolder = os.path.join(user["modsPath"], barcode)
        manifestFile = os.path.join(user["modsPath"], f"{barcode}.manifest")

        if os.path.exists(modFolder):
            totalSize += sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(modFolder)
                for filename in filenames
            )
        if os.path.exists(manifestFile):
            totalSize += os.path.getsize(manifestFile)

    print(f"Total size of mods to delete: {totalSize / (1024 * 1024 * 1024):.1f}GB")
    # Save list of mods to be deleted
    with open("modsToDelete.txt", "w") as f:
        for mod in unsubscribedMods:
            f.write(f"Mod ID: {mod['modId']}, Barcode: {mod['barcode']}\n")
    print(
        colourYellow
        + "Saved a list of mods to delete in modsToDelete.txt. Please review which mods are being deleted before confirming!"
        + colourReset
    )
    confirm = input(
        bold + "Are you sure you want to delete these mods? (y/N): " + colourReset
    )
    if confirm.lower() == "y":
        deleted_count = 0
        for mod in unsubscribedMods:
            barcode = mod["barcode"]
            # Delete the mod folder (named after barcode)
            mod_folder = os.path.join(user["modsPath"], barcode)
            manifest_file = os.path.join(user["modsPath"], f"{barcode}.manifest")

            try:
                # Delete the mod folder if it exists
                if os.path.exists(mod_folder):
                    shutil.rmtree(mod_folder)
                    print(f"Deleted folder: {barcode}")

                # Delete the manifest file if it exists
                if os.path.exists(manifest_file):
                    os.remove(manifest_file)
                    print(f"Deleted manifest: {barcode}.manifest")

                deleted_count += 1

            except Exception as e:
                print(f"Error deleting mod {barcode}: {e}")

        # Update installedMods.json with remaining mods
        remaining_mods = [
            mod for mod in installedMods if str(mod["modId"]) in subscribedMods
        ]
        with open("installedMods.json", "w") as f:
            json.dump(remaining_mods, f, indent=4)

        print(f"\nSuccessfully deleted {deleted_count} unsubscribed mods.")
    else:
        print("Operation cancelled.")

    _ = input("Press Enter to continue...")


def main():
    setupUserConfig()
    while True:
        choice = printMenu()
        if choice == "1":
            getSubscribedMods()
        elif choice == "2":
            getInstalledMods()
        elif choice == "3":
            deleteUnsubscribedMods()
        elif choice == "4":
            exit()
        else:
            print("Invalid option, please try again.")


if __name__ == "__main__":
    main()
