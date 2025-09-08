# mail_setup.py — Shadow User Data launch (fixed)
# יוצר עותק זמני של ה-User Data לפרופיל (בלי קאש/Service Worker וכו'), מריץ כרום עם דיבאגר,
# נצמד עם Selenium, ונכנס ל-Gmail. לא שולח מיילים.

import os, time, subprocess, shutil, glob, socket, urllib.request, tempfile
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PAGELOAD_TIMEOUT  = 60

USER_DATA_DIR = os.path.join(os.getenv("LOCALAPPDATA"), r"Google\Chrome\User Data")
LOCAL_STATE   = os.path.join(USER_DATA_DIR, "Local State")

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    shutil.which("chrome"),
    shutil.which("chrome.exe"),
]
CHROME_EXE = next((p for p in CHROME_CANDIDATES if p and os.path.exists(p)), None)
if not CHROME_EXE:
    raise RuntimeError("chrome.exe לא נמצא.")

def free_port():
    s = socket.socket(); s.bind(('', 0)); port = s.getsockname()[1]; s.close(); return port
def devtools_alive(port, timeout=20):
    url = f"http://127.0.0.1:{port}/json/version"
    t0 = time.time()
    while time.time()-t0 < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                r.read(); return True
        except Exception:
            time.sleep(0.25)
    return False
def copy_profile_shadow(root_dst, profile_name):
    os.makedirs(root_dst, exist_ok=True)
    if os.path.exists(LOCAL_STATE):
        shutil.copy2(LOCAL_STATE, os.path.join(root_dst, "Local State"))
    src = os.path.join(USER_DATA_DIR, profile_name)
    dst = os.path.join(root_dst, profile_name)
    os.makedirs(dst, exist_ok=True)
    patterns = [
        "Cache", "Cache*", "Code Cache", "Code Cache*", "GPUCache", "GPUCache*",
        "Media Cache", "Media Cache*", "GrShaderCache*", "ShaderCache*",
        "Crashpad*", "Network", "Network*", "blob_storage*", "databases*", "IndexedDB*",
        "Service Worker*", "Storage*", "File System*", "OptimizationGuide*", "TransportSecurity",
        "*.log", "Visited Links", "History Provider Cache", "QuotaManager*"
    ]
    ignore = shutil.ignore_patterns(*patterns)
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore)
    return dst  # נתיב הפרופיל בתוך ה-shadow

def kill_all_chrome():
    for name in ("chrome.exe","GoogleCrashHandler.exe","GoogleCrashHandler64.exe"):
        subprocess.run(["taskkill","/IM",name,"/F","/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.6)
def launch_chrome(user_data_root, profile_name, port, disable_ext=False):
    cmd = [
        CHROME_EXE,
        f'--user-data-dir={user_data_root}',
        f'--profile-directory={profile_name}',
        '--remote-debugging-address=127.0.0.1',
        f'--remote-debugging-port={port}',
        '--remote-allow-origins=*',
        '--no-first-run', '--no-default-browser-check',
        '--disable-session-crashed-bubble',
        'about:blank'
    ]
    if disable_ext:
        cmd.insert(-1, '--disable-extensions')
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def connect_selenium(port):
    os.environ["SE_USE_PATH"] = "0"
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
    opts.set_capability("pageLoadStrategy", "none")
    drv = webdriver.Chrome(service=Service(), options=opts)
    drv.set_page_load_timeout(PAGELOAD_TIMEOUT)
    return drv

def open_gmail(driver,email=""):
    driver.get("https://mail.google.com/mail/u/0/#inbox")
    time.sleep(4)
    url = driver.current_url
    if "accounts.google.com" in url:
        try:
            driver.find_element(By.ID, "identifierId").send_keys(email)
            time.sleep(0.6)
            driver.find_element(By.XPATH, "//span[text()='Next']").click()
            time.sleep(4)
            driver.find_element(By.XPATH, '//input[@name="Passwd"]').send_keys("Adam1Idan2")
            time.sleep(0.6)
            driver.find_element(By.XPATH, "//span[text()='Next']").click()
            time.sleep(4)
        finally: return True
    if "mail.google.com/mail" in url:
        return True

def get_mail_driver(profile):
    kill_all_chrome()
    shadow_root = tempfile.mkdtemp(prefix="ChromeShadow_")
    copy_profile_shadow(shadow_root, profile)
    port = free_port()
    proc = launch_chrome(shadow_root, profile, port, disable_ext=False)
    time.sleep(0.8)
    if proc.poll() is not None:
        proc = launch_chrome(shadow_root, profile, port, disable_ext=True)
        time.sleep(0.8)
    if not devtools_alive(port, 25):
        try: proc.terminate()
        except: pass
        cleanup_driver(None, None, shadow_root)
        raise RuntimeError("DevTools לא קם גם על ה-shadow.")
    driver = connect_selenium(port)
    time.sleep(3)
    return driver, (lambda: cleanup_driver(driver, proc, shadow_root))

def cleanup_driver(driver, proc, shadow_root):
    try:
        if driver: driver.quit()
    except: pass
    try:
        if proc: proc.terminate()
    except: pass
    time.sleep(0.5)
    try:
        if shadow_root: shutil.rmtree(shadow_root, ignore_errors=True)
    except: pass