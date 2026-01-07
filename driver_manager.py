# driver_manager.py
# Global DriverManager
# Keeps your working launch/connect logic the same.

import json
import os, time, subprocess, shutil, socket, urllib.request, tempfile
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    shutil.which("chrome"),
    shutil.which("chrome.exe"),
]
CHROME_EXE = next((p for p in CHROME_CANDIDATES if p and os.path.exists(p)), None)
if not CHROME_EXE:
    raise RuntimeError("chrome.exe not found")

with open("emails.json", 'r', encoding='utf-8') as f:
    CHROME_PROFILES = json.load(f)

def get_profile_info(email:str):
    profile = CHROME_PROFILES.get(email)
    if not profile:
        raise Exception(f"No Chrome profile found for {email}")
    profile_num = profile["profile_num"]
    profile = f"Profile {profile_num}"
    return profile


class DriverManager:
    user_email: str = ""

    def __init__(self, email:str = ""):
        if not email:
            email = DriverManager.user_email

        if email != DriverManager.user_email:
            self._kill_all_chrome()
            time.sleep(3)

        self.shadow_root = tempfile.mkdtemp(prefix="ChromeShadow_")
        port = self.free_port()

        profile = get_profile_info(email)

        self.proc = self._launch_chrome(self.shadow_root, profile, port, disable_ext=False)
        time.sleep(0.8)

        if self.proc.poll() is not None:
            self.proc = self._launch_chrome(self.shadow_root, profile, port, disable_ext=True)
            time.sleep(0.8)

        if not self.devtools_alive(port, 25):
            try:
                if self.proc: self.proc.terminate()
            except: pass
            time.sleep(0.5)
            try:
                if self.shadow_root: shutil.rmtree(self.shadow_root, ignore_errors=True)
            except: pass

            self.proc = None
            self.shadow_root = None
            raise RuntimeError("DevTools did not start")

        self.driver = self.connect_selenium(port)
        time.sleep(1)

        DriverManager.user_email = email

    def open_gmail(self) -> str:
        print(f"###### DriverManager: Open Gmail")
        url = self.open_site("https://mail.google.com/mail/u/0/#inbox")
        if "accounts.google.com" in url:
            for i in range(3):
                url = self.current_url()
                if "mail.google.com/mail" in url:
                    print("GMAIL OPENED")
                    return url
                try:
                    email_input = self.click_element(By.ID, "identifierId")
                    email_input.clear()
                    while not email_input.get_attribute("value"):
                        email_input.send_keys(DriverManager.user_email)

                    next_btn = self.click_element(By.ID, "identifierNext")

                    password_input = self.click_element(By.NAME, "Passwd")
                    password_input.clear()
                    while not password_input.get_attribute("value"):
                        password_input.send_keys("Adam1Idan2")

                    next_btn = self.click_element(By.ID, "passwordNext")
                finally:
                    continue
        if "mail.google.com/mail" in url:
            return url
        raise Exception("Couldn't open gmail ( DriverManager.open_gmail(self) )")

    def open_site(self, href:str):
        old_url =  self.current_url()
        self.driver.get(href)
        new_url = self.current_url()
        return new_url if new_url != old_url else False

    def current_url(self, timeout:int = 10):
        return self.wait(timeout).until(lambda d: d.current_url)

    def _by_value(self, by:By|str) -> By|str:
        return by.value if isinstance(by, By) else by

    def wait(self, timeout:int = 10):
        if self.driver is None:
            raise RuntimeError("Driver not initialized. Call DriverManager.init(email)")
        return WebDriverWait(self.driver, timeout)

    def click_element(self, by:By|str, value:str, timeout:int = 10):
        print(f"###### DriverManager: Click element: {by}, {value}")
        element = self.wait(timeout).until(EC.element_to_be_clickable((self._by_value(by), value)))
        element.click()
        return element

    def find_element(self, by:By|str, value:str, parent = None, timeout:int = 10):
        parent = self.driver if parent is None else parent
        return self.wait(timeout).until(lambda d: parent.find_element(self._by_value(by), value))

    def find_elements(self, by:By|str, value:str, parent = None, timeout:int = 10):
        print(f"###### DriverManager: Find all elements: {by}, {value}")
        parent = self.driver if parent is None else parent
        return self.wait(timeout).until(lambda d: parent.find_elements(self._by_value(by), value))

    @staticmethod
    def _kill_all_chrome():
        for name in ("chrome.exe", "GoogleCrashHandler.exe", "GoogleCrashHandler64.exe"):
            subprocess.run(
                ["taskkill", "/IM", name, "/F", "/T"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        time.sleep(0.6)

    @staticmethod
    def free_port() -> int:
        s = socket.socket()
        s.bind(("", 0))
        port = s.getsockname()[1]
        s.close()
        return port

    @staticmethod
    def _launch_chrome(user_data_root:str, profile:str, port:int, disable_ext:bool = False):
        cmd = [
            CHROME_EXE,
            f"--user-data-dir={user_data_root}",
            f"--profile-directory={profile}",
            "--remote-debugging-address=127.0.0.1",
            f"--remote-debugging-port={port}",
            "--remote-allow-origins=*",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-session-crashed-bubble",
            "about:blank",
        ]
        if disable_ext:
            cmd.insert(-1, "--disable-extensions")
        return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @staticmethod
    def devtools_alive(port:int, timeout:int = 20) -> bool:
        url = f"http://127.0.0.1:{port}/json/version"
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                with urllib.request.urlopen(url, timeout=1):
                    return True
            except:
                time.sleep(0.25)
        return False

    @staticmethod
    def connect_selenium(port:int) -> WebDriver:
        os.environ["SE_USE_PATH"] = "0"
        opts = Options()
        opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
        opts.set_capability("pageLoadStrategy", "none")
        drv = webdriver.Chrome(service=Service(), options=opts)
        drv.set_page_load_timeout(60)
        return drv

    def close(self):
        print(f"###### DriverManager: Closing driver")
        try:
            if self.driver:
                try: self.driver.quit()
                except: pass

            if self.proc:
                try: self.proc.terminate()
                except: pass

            time.sleep(0.5)

            if self.shadow_root:
                try: shutil.rmtree(self.shadow_root, ignore_errors=True)
                except: pass
        finally:
            self.driver = None
            self.proc = None
            self.shadow_root = None

    def shutdown_all(self):
        try: self.close()
        except: pass

        try: self ._kill_all_chrome()
        except:  pass

import atexit
import signal
import sys

def _install_global_cleanup():
    # 1) ביציאה “רגילה” מהתהליך
    atexit.register(DriverManager.shutdown_all)

    # 2) Ctrl+C / SIGTERM
    def _sig_handler(signum, frame):
        DriverManager.shutdown_all()
        raise KeyboardInterrupt

    for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
        if sig is not None:
            try:
                signal.signal(sig, _sig_handler)
            except:
                pass

    # 3) חריגה לא מטופלת (קריסה)
    old_hook = sys.excepthook
    def _excepthook(exc_type, exc, tb):
        try:
            DriverManager.shutdown_all()
        finally:
            old_hook(exc_type, exc, tb)
    sys.excepthook = _excepthook

_install_global_cleanup()