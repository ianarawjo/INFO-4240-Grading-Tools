# Add location of INFO 4240 grading library to module search path
import sys
BASE_PATH = "./"
sys.path.append(BASE_PATH)

import asyncio
import os
from pathlib import Path
import shutil
import zipfile
from pyppeteer import launch

# Load config info for assignments
import load
CONFIG_PATH = os.path.join(BASE_PATH, "config.json")
config = load.config(CONFIG_PATH)
DOWNLOAD_DIR = config["pyppeteerDownloadDir"] # where Chromium will d/l its files
assn_name, assn_info = None, None

# Special commands:
# You can add <assn_name> to . After assn_name, you can add "--once" to do only once.
ONLY_ONCE = False
def parse_arg(arg):
    global assn_name, assn_info, ONLY_ONCE
    if arg[:2] == "--":
        if arg[2:] == "once": ONLY_ONCE = True
    elif arg in config["assignments"]:
        assn_name, assn_info = arg, config["assignments"][arg]
for arg in sys.argv[1:]:
    parse_arg(arg)

# Ask for which assignment to scrape:
if assn_name is None:
    assn_name, assn_info = load.promptSelectAssignment(config)

""" Watcher to download gradesheets for an assignment automatically to specified folder.
    Must set WATCH_DIR and DOWNLOAD_DIR.
"""

ASSN_PAGE = assn_info["url"]
WATCH_DIR = os.path.join(BASE_PATH, assn_info["data"]) # be careful --the script removes files automatically at the dir
SLEEP_INTERVAL = 60 # time between downloads, in seconds
REVIEW_PAGE = os.path.join(ASSN_PAGE, "review_grades")

async def setup(reviewpage):
    browser = await launch({"autoClose":False,'headless': False, 'userDataDir':'./pyppeteer_data'})
    page = await browser.newPage()
    await page.goto(REVIEW_PAGE)

    await page.setViewport({ #  maximize window
      "width": 1400,
      "height": 800
      })
    return page

async def main():
    page = await setup(REVIEW_PAGE)

    print('Watching grades for', ASSN_PAGE, "...")
    while(True):

        action_btns = await page.querySelectorAll('.actionBar--action')
        export_eval_btn = None
        download_csv_btn = None
        for btn in action_btns:
            title = await page.evaluate("(btn) => btn.getAttribute('title')", btn)
            if title == "Download marked rubrics for each question":
                export_eval_btn = btn
                break
        action_btns = await page.querySelectorAll('.popover--listItem')
        for btn in action_btns:
            href = await page.evaluate("(btn) => btn.getAttribute('href')", btn)
            if href[-10:] == "scores.csv":
                download_csv_btn = btn
                break

        # Download eval sheets
        print(" | downloading csvs...")
        await export_eval_btn.click()

        # Wait
        await asyncio.sleep(2)

        # Download scores csv
        download_btn = await page.querySelectorAll('#download-grades-tooltip-link')
        await download_btn[0].click()
        await asyncio.sleep(1)
        await download_csv_btn.click()

        # Wait
        await asyncio.sleep(5)

        # Delete contents of watch folder
        print(" | deleting contents of watch folder...")
        for root, dirs, files in os.walk(WATCH_DIR):
            for f in files:
                os.remove(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))

        # Move downloaded files to watch folder + unzip
        print(" | moving downloaded files...")
        paths = sorted(Path(DOWNLOAD_DIR).iterdir(), key=os.path.getmtime, reverse=True)
        for path in paths[:2]:
            if str(path)[-4:] == ".csv":
                shutil.copy2(path, WATCH_DIR)
            elif str(path)[-4:] == ".zip":
                with zipfile.ZipFile(path, 'r') as zip_ref:
                    zip_ref.extractall(WATCH_DIR)
        await asyncio.sleep(1)

        if ONLY_ONCE:
            break

        print("Re-downloading files in {} seconds...".format(SLEEP_INTERVAL))
        await page.goto(REVIEW_PAGE)
        await asyncio.sleep(SLEEP_INTERVAL)

if '__main__' == __name__:
    asyncio.get_event_loop().run_until_complete(main())
