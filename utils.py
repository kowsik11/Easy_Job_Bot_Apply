import math, time, os, constants, config
from typing import List
from selenium import webdriver


# ─────────────────────────────────────────────────────────────────────────────
# Chrome options
# ─────────────────────────────────────────────────────────────────────────────
def chromeBrowserOptions() -> webdriver.ChromeOptions:
    opts = webdriver.ChromeOptions()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--log-level=3")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])

    if config.headless:
        opts.add_argument("--headless=new")

    # use your local Chrome profile if configured
    if config.chromeProfilePath:
        base = config.chromeProfilePath.rsplit("/", 1)[0]
        prof = config.chromeProfilePath.rsplit("/", 1)[1]
        opts.add_argument(f"--user-data-dir={base}")
        opts.add_argument(f"--profile-directory={prof}")
    else:
        opts.add_argument("--incognito")
    return opts


# ─────────────────────────────────────────────────────────────────────────────
# Pretty console colours
# ─────────────────────────────────────────────────────────────────────────────
def prRed(txt):    print(f"\033[91m{txt}\033[0m")
def prGreen(txt):  print(f"\033[92m{txt}\033[0m")
def prYellow(txt): print(f"\033[93m{txt}\033[0m")


# ─────────────────────────────────────────────────────────────────────────────
# File helpers
# ─────────────────────────────────────────────────────────────────────────────
def getUrlDataFile() -> List[str]:
    try:
        with open("data/urlData.txt", encoding="utf-8") as fh:
            return [ln.strip() for ln in fh if ln.strip()]
    except FileNotFoundError:
        prRed("❌  data/urlData.txt not found – run the bot once to create it.")
        return []


def jobsToPages(num_of_jobs: str) -> int:
    if " " in num_of_jobs:
        total = int(num_of_jobs.split(" ")[0].replace(",", ""))
        pages = math.ceil(total / constants.jobsPerPage)
        return min(pages, 40)
    # fallback (already a number)
    try:
        return int(num_of_jobs)
    except ValueError:
        return 1


def urlToKeywords(url: str) -> List[str]:
    kw  = url.split("keywords=")[1].split("&")[0]
    loc = url.split("location=")[1].split("&")[0]
    return [kw, loc]


def writeResults(line: str):
    os.makedirs("data", exist_ok=True)
    fname = time.strftime("Applied Jobs DATA - %Y%m%d.txt")
    header = (
        "---- Applied Jobs Data ---- created at: "
        + time.strftime("%Y-%m-%d %H:%M")
        + "\n---- Number | Job | Company | Location | Result\n"
    )

    if not os.path.exists(f"data/{fname}"):
        with open(f"data/{fname}", "w", encoding="utf-8") as fh:
            fh.write(header)

    with open(f"data/{fname}", "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def donate(driver_holder):
    prYellow("If the project helped you, consider buying me a coffee ☕")
    try:
        driver_holder.driver.execute_script("window.open('https://www.automated-bots.com/');")
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# URL generator (same logic you had before, just clearer)
# ─────────────────────────────────────────────────────────────────────────────
class LinkedinUrlGenerate:
    def generateUrlLinks(self) -> List[str]:
        links = []
        for loc in config.location:
            for kw in config.keywords:
                parts = [
                    constants.linkJobUrl,
                    "?f_AL=true",
                    "&keywords=" + kw,
                    self.jobType(),
                    self.remote(),
                    self.checkJobLocation(loc),
                    self.jobExp(),
                    self.datePosted(),
                    self.salary(),
                    self.sortBy(),
                ]
                links.append("".join(parts))
        return links

    # ---------- building blocks ---------------------------------------
    def checkJobLocation(self, loc: str) -> str:
        geo = {
            "asia":         "102393603",
            "europe":       "100506914",
            "northamerica": "102221843",
            "southamerica": "104514572",
            "australia":    "101452733",
            "africa":       "103537801",
        }
        return f"&location={loc}&geoId={geo.get(loc.lower(),'')}"

    def jobExp(self) -> str:
        mapping = {
            "Internship":       "1",
            "Entry level":      "2",
            "Associate":        "3",
            "Mid-Senior level": "4",
            "Director":         "5",
            "Executive":        "6",
        }
        ids = [mapping[e] for e in config.experienceLevels if e in mapping]
        return "&f_E=" + "%2C".join(ids) if ids else ""

    def datePosted(self) -> str:
        mapping = {
            "Any Time":        "",
            "Past Month":      "&f_TPR=r2592000&",
            "Past Week":       "&f_TPR=r604800&",
            "Past 24 hours":   "&f_TPR=r86400&",
        }
        return mapping.get(config.datePosted[0], "")

    def jobType(self) -> str:
        mapping = {
            "Full-time":  "F", "Part-time": "P", "Contract": "C",
            "Temporary":  "T", "Volunteer": "V", "Intership": "I",
            "Other":      "O",
        }
        ids = [mapping[t] for t in config.jobType if t in mapping]
        return "&f_JT=" + "%2C".join(ids) + "&" if ids else ""

    def remote(self) -> str:
        mapping = {"On-site": "1", "Remote": "2", "Hybrid": "3"}
        ids = [mapping[r] for r in config.remote if r in mapping]
        return "f_WT=" + "%2C".join(ids) if ids else ""

    def salary(self) -> str:
        mapping = {
            "$40,000+": "1", "$60,000+": "2", "$80,000+": "3",
            "$100,000+": "4", "$120,000+": "5", "$140,000+": "6",
            "$160,000+": "7", "$180,000+": "8", "$200,000+": "9",
        }
        return f"f_SB2={mapping.get(config.salary[0],'')}&" if config.salary else ""

    def sortBy(self) -> str:
        return "sortBy=DD" if config.sort[0] == "Recent" else "sortBy=R"
