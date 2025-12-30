# driver_manager.py
# Global DriverManager
# Keeps your working launch/connect logic the same.

import os, time, subprocess, shutil, socket, urllib.request, tempfile
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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


class DriverManager:

    _driver = None
    _proc = None
    _shadow_root = None
    _profile = None

    @classmethod
    def init(cls, profile: str):
        if cls._driver is not None and cls._profile == profile:   # If already initialized with same profile, reuse
            return cls._driver

        if cls._driver is not None and cls._profile != profile:   # If initialized with different profile, close first
            cls.close()

        cls._kill_all_chrome()

        cls._shadow_root = tempfile.mkdtemp(prefix="ChromeShadow_")
        port = cls._free_port()

        cls._proc = cls._launch_chrome(cls._shadow_root, profile, port, disable_ext=False)
        time.sleep(0.8)

        if cls._proc.poll() is not None:
            cls._proc = cls._launch_chrome(cls._shadow_root, profile, port, disable_ext=True)
            time.sleep(0.8)

        if not cls._devtools_alive(port, 25):
            try:
                if cls._proc: cls._proc.terminate()
            except: pass
            time.sleep(0.5)
            try:
                if cls._shadow_root: shutil.rmtree(cls._shadow_root, ignore_errors=True)
            except: pass

            cls._driver = None
            cls._proc = None
            cls._shadow_root = None
            cls._profile = None
            raise RuntimeError("DevTools did not start")

        cls._driver = cls.connect_selenium(port)
        time.sleep(1)

        cls._profile = profile
        return cls._driver

    @classmethod
    def driver(cls):
        if cls._driver is None:
            raise RuntimeError("Driver not initialized. Call DriverManager.init(profile)")
        return cls._driver

    @classmethod
    def open_site(cls, href: str):
        cls._driver.get(href)
        return cls.wait().until(lambda d: d.current_url)

    @classmethod
    def _by_value(cls, by):
        return by.value if isinstance(by, By) else by

    @classmethod
    def click_element(cls, by, value, timeout=10):
        return cls.wait(timeout).until(EC.element_to_be_clickable((cls._by_value(by), value)))

    @classmethod
    def all_elements(cls, by, value, timeout=10):
        return cls.wait(timeout).until(EC.presence_of_all_elements_located((cls._by_value(by), value)))

    @classmethod
    def find_element(cls, by, value, parent = None, timeout=10):
        parent = cls._driver if parent is None else parent
        return cls.wait(timeout).until(lambda d: parent.find_element(cls._by_value(by), value))

    @classmethod
    def find_elements(cls, by, value, parent = None, timeout=10):
        parent = cls._driver if parent is None else parent
        return cls.wait(timeout).until(lambda d: parent.find_elements(cls._by_value(by), value))

    @classmethod
    def wait(cls, timeout=10):
        if cls._driver is None:
            raise RuntimeError("Driver not initialized. Call DriverManager.init(profile)")
        return WebDriverWait(cls._driver, timeout)

    @classmethod
    def close(cls):
        try:
            if cls._driver:
                try: cls._driver.quit()
                except: pass

            if cls._proc:
                try: cls._proc.terminate()
                except: pass

            time.sleep(0.5)

            if cls._shadow_root:
                try: shutil.rmtree(cls._shadow_root, ignore_errors=True)
                except: pass
        finally:
            cls._driver = None
            cls._proc = None
            cls._shadow_root = None
            cls._profile = None

    @staticmethod
    def _free_port():
        s = socket.socket()
        s.bind(("", 0))
        port = s.getsockname()[1]
        s.close()
        return port

    @staticmethod
    def _devtools_alive(port, timeout=20):
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
    def _kill_all_chrome():
        for name in ("chrome.exe", "GoogleCrashHandler.exe", "GoogleCrashHandler64.exe"):
            subprocess.run(
                ["taskkill", "/IM", name, "/F", "/T"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        time.sleep(0.6)

    @classmethod
    def _launch_chrome(cls, user_data_root, profile, port, disable_ext=False):
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

    @classmethod
    def connect_selenium(cls, port):
        os.environ["SE_USE_PATH"] = "0"
        opts = Options()
        opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
        opts.set_capability("pageLoadStrategy", "none")
        drv = webdriver.Chrome(service=Service(), options=opts)
        drv.set_page_load_timeout(60)
        return drv
