"""
linkedin.py  – LinkedIn Easy-Apply bot v2.1
──────────────────────────────────────────────────────────────────────────────
• Logs in (cached cookies) → builds URLs from config → loops through jobs
• Presses the Easy-Apply button (robust JS fallback)
• Auto-fills every required field (text / number / radio / checkbox / select)
• Keeps clicking  Next → Review → Submit  until the application is sent
• Logs every action to console and /data/Applied Jobs DATA - YYYYMMDD.txt
"""

import os, time, random, pickle, hashlib, math, re
from typing import List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementNotInteractableException,
    StaleElementReferenceException,
)
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService

import utils, constants, config, answers

# ─────────────────────────────────────────────────────────────────────────────
# Helper – Easy-Apply wizard
# ─────────────────────────────────────────────────────────────────────────────
class EasyApplyWizard:
    """Auto-fill & press through the Easy-Apply modal."""

    def __init__(self, driver, timeout: int = 15):
        self.driver = driver
        self.wait   = WebDriverWait(driver, timeout)

    # ─────────── internal helpers
    def _scroll_modal(self):
        box = self.driver.find_element(By.CSS_SELECTOR, "div.artdeco-modal__content")
        self.driver.execute_script(
            "arguments[0].scrollTop = arguments[0].scrollHeight;", box
        )

    def _js_click(self, el):  # click via JavaScript
        self.driver.execute_script("arguments[0].click();", el)

    def _click(self, label: str) -> bool:
        """Return *True* if a button with that aria-label was clicked."""
        try:
            btn = self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, f'button[aria-label="{label}"]')
                )
            )
            self._scroll_modal()
            try:
                btn.click()
            except ElementNotInteractableException:
                self._js_click(btn)
            return True
        except Exception:
            return False

    # ─────────── auto-fill required questions
    def _default_for(self, label: str, typ: str) -> str:
        label = (label or "").lower()
        val = answers.lookup(label)
        if val is not None:
            return val
        # generic fallbacks …
        if typ in ("number", "tel"):
            return "0"
        if "year" in label and typ == "text":
            return "0"
        return "N/A"

    def _fill_modal(self):
        modal = self.driver.find_element(By.CSS_SELECTOR, "div.artdeco-modal__content")

        # input[type=*] -----------------------------------------------------
        for inp in modal.find_elements(By.CSS_SELECTOR, "input[aria-required='true']"):
            if inp.get_attribute("value"):
                continue
            label = inp.get_attribute("aria-label") or ""
            typ   = (inp.get_attribute("type") or "text").lower()
            inp.send_keys(self._default_for(label, typ))

        # textarea ----------------------------------------------------------
        for ta in modal.find_elements(By.CSS_SELECTOR, "textarea[aria-required='true']"):
            if not ta.get_attribute("value"):
                ta.send_keys("N/A")

        # radio groups ------------------------------------------------------
        radios = modal.find_elements(By.CSS_SELECTOR, "input[type='radio']")
        seen = set()
        for ra in radios:
            name = ra.get_attribute("name")
            if name in seen:
                continue
            if not any(r.is_selected() for r in radios if r.get_attribute("name") == name):
                self._js_click(ra)   # first option
            seen.add(name)

        # required checkboxes ----------------------------------------------
        for cb in modal.find_elements(By.CSS_SELECTOR, "input[type='checkbox'][aria-required='true']"):
            if not cb.is_selected():
                self._js_click(cb)

        # <select> dropdowns -----------------------------------------------
        for sel in modal.find_elements(By.TAG_NAME, "select"):
            select = Select(sel)
            if select.first_selected_option.get_attribute("value"):
                continue
            for opt in select.options:
                if not opt.get_attribute("disabled"):
                    select.select_by_visible_text(opt.text)
                    break

    # ─────────── public
    def run(self) -> str:
        for _ in range(10):                     # hard stop after 10 modal pages
            self._fill_modal()
            if self._click("Submit application"):
                return "submitted"
            if self._click("Review your application"):
                continue
            if self._click("Continue to next step"):
                continue
            if self._click("Next"):
                continue
            break
        return "stopped"

# ─────────────────────────────────────────────────────────────────────────────
# Main bot
# ─────────────────────────────────────────────────────────────────────────────
class Linkedin:
    def __init__(self):
        utils.prYellow("🤖  Easy-Apply bot starting …")
        self.driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=utils.chromeBrowserOptions(),
        )

        self.cookies_path = os.path.join("cookies", self._md5(config.email) + ".pkl")
        self.driver.get("https://www.linkedin.com")
        self._load_cookies()

        if not self._is_logged_in():
            self._login()
            self._save_cookies()

        self._generate_urls()
        self._main_loop()

    # ─────────── housekeeping
    @staticmethod
    def _md5(s: str) -> str:
        import hashlib
        return hashlib.md5(s.encode()).hexdigest()

    def _load_cookies(self):
        if os.path.exists(self.cookies_path):
            with open(self.cookies_path, "rb") as fh:
                for ck in pickle.load(fh):
                    self.driver.add_cookie(ck)

    def _save_cookies(self):
        os.makedirs("cookies", exist_ok=True)
        with open(self.cookies_path, "wb") as fh:
            pickle.dump(self.driver.get_cookies(), fh)

    def _is_logged_in(self) -> bool:
        self.driver.get("https://www.linkedin.com/feed")
        return "feed" in self.driver.current_url and "login" not in self.driver.current_url

    def _login(self):
        self.driver.get("https://www.linkedin.com/login")
        utils.prYellow("🔄  Logging in …")
        self.driver.find_element(By.ID, "username").send_keys(config.email)
        self.driver.find_element(By.ID, "password").send_keys(config.password)
        self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(30)        # allow user to solve captcha / 2FA

    # ─────────── build URL list once
    def _generate_urls(self):
        os.makedirs("data", exist_ok=True)
        with open("data/urlData.txt", "w", encoding="utf-8") as fh:
            for url in utils.LinkedinUrlGenerate().generateUrlLinks():
                fh.write(url + "\n")
        utils.prGreen("✅  URL list written to data/urlData.txt")

    # ─────────── looping over jobs
    def _main_loop(self):
        total_seen = total_applied = 0

        for search_url in utils.getUrlDataFile():
            kw, loc = utils.urlToKeywords(search_url)
            utils.prYellow(f"\n🔎  {kw}  –  {loc}")

            self.driver.get(search_url)
            pages = utils.jobsToPages(
                self.driver.find_element(By.TAG_NAME, "small").text
            )

            for page in range(pages):
                self.driver.get(f"{search_url}&start={page*constants.jobsPerPage}")
                time.sleep(random.uniform(1, constants.botSpeed))

                offers = self.driver.find_elements(By.XPATH, "//li[@data-occludable-job-id]")
                ids = {o.get_attribute("data-occludable-job-id").split(":")[-1] for o in offers}

                for job_id in ids:
                    total_seen += 1
                    url = f"https://www.linkedin.com/jobs/view/{job_id}"
                    self.driver.get(url)
                    time.sleep(random.uniform(1, constants.botSpeed))

                    header = self._job_header(total_seen)

                    btn = self._easy_apply_btn()
                    if not btn:
                        utils.writeResults(f"{header} | 🥳 Already applied | {url}")
                        continue

                    if not self._safe_click(btn):
                        utils.writeResults(f"{header} | 🥵 Cannot click Easy-Apply | {url}")
                        continue

                    time.sleep(1)
                    self._choose_resume()

                    wizard = EasyApplyWizard(self.driver)
                    if wizard.run() == "submitted":
                        total_applied += 1
                        utils.writeResults(f"{header} | 🥳 Applied | {url}")
                    else:
                        utils.writeResults(f"{header} | 🥵 Stopped – extra Qs | {url}")

            utils.prYellow(f"==> Applied {total_applied}/{total_seen} this session.")

        utils.donate(self)

    # ─────────── small helpers
    def _job_header(self, n: int) -> str:
        title    = self._txt("h1")
        company  = self._txt("a[href*='company']")
        location = self._txt("span.jobs-unified-top-card__bullet")
        return f"{n} | {title} | {company} | {location}"

    def _txt(self, css: str) -> str:
        try:
            return self.driver.find_element(By.CSS_SELECTOR, css).text.strip()
        except Exception:
            return ""

    def _easy_apply_btn(self):
        try:
            return self.driver.find_element(
                By.CSS_SELECTOR,
                "button.jobs-apply-button:not(.artdeco-button--disabled)"
            )
        except Exception:
            return None

    def _safe_click(self, el) -> bool:
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            try:
                el.click()
            except ElementNotInteractableException:
                self.driver.execute_script("arguments[0].click();", el)
            return True
        except Exception:
            return False

    def _choose_resume(self):
        try:
            modal = self.driver.find_element(By.CSS_SELECTOR, "div.artdeco-modal__content")
            if modal.find_elements(By.CLASS_NAME, "jobs-document-upload__title--is-required"):
                pdfs = modal.find_elements(By.CSS_SELECTOR, "div.ui-attachment--pdf")
                if pdfs:
                    pdfs[min(len(pdfs), config.preferredCv) - 1].click()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    t0 = time.time()
    Linkedin()
    utils.prYellow(f"\nFinished in {round((time.time()-t0)/60,1)} min")
