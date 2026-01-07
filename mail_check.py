import time
from selenium.webdriver.common.by import By

import json

from driver_manager import DriverManager
from email_handler import EmailHandler
from entities.SurveyHandler import Survey
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from queue import Queue
import threading
from selenium.webdriver.common.by import By

MAX_WORKERS: int = 3
with open("emails.json", 'r', encoding='utf-8') as f:
    CHROME_PROFILES = json.load(f)

def get_email_links() -> list[str]:
    email_cons = driver.find_elements(By.CLASS_NAME, "zA")
    if not email_cons:
        raise Exception("No emails found")

    email_links = []
    for email_con in email_cons:
        try:
            email_link_con = driver.find_element(By.CSS_SELECTOR, "span[data-legacy-thread-id]", email_con)
            email_link_id = email_link_con.get_attribute("data-legacy-thread-id")
            email_link = f"https://mail.google.com/mail/u/0/#inbox/{email_link_id}"
            email_links.append(email_link)
        except Exception as e:
            print(f"❌ Failed extracting email link: {e}")

    return email_links

def fill_survey(email_link: str):
    try:
        email_handler = EmailHandler(email_link)
        for i in range(3):
            if email_handler.handle_email():
                break
        email_handler.delete_email()
    except Exception as e:
        print(f"❌ Error processing email: {e}")

def worker_loop(email_links_q, results_q):                        # worker process
    dm = DriverManager()                                          # opens user worker driver
    try:
        dm.open_gmail()                                           # logs in user worker gmail
        while True:                                               # while has more links
            email_link = email_links_q.get()                      # gets link from queue
            if email_link is "STOP":                              # if got stopping flag
                email_links_q.task_done()                         # stops
                break
            try:
                survey_filled = EmailHandler(email_link, dm)      # handles mail (opens,fills,deletes)
                results_q.put((email_link, survey_filled, None))  # saves result (link, is filled)
            except Exception as e:                                # if error accured
                results_q.put((email_link, False, str(e)))        # saves result (link,not filled, why not)
            finally:
                email_links_q.task_done()
    finally:
        dm.close()                                                # worker is done - close worker

def handle_user_emails():
    driver.open_gmail()

    email_links = get_email_links()

    email_links_q = Queue()
    results_q = Queue()
    threads = []
    for _ in range(MAX_WORKERS):
        t = threading.Thread(target=worker_loop, args=(email_links_q, results_q), daemon=True)
        t.start()
        threads.append(t)

    for tid in email_links:
        email_links_q.put(tid)

    for _ in range(MAX_WORKERS):
        email_links_q.put("STOP")

    email_links_q.join()
    for t in threads:
        t.join()

    while not results_q.empty():                   # print failed attempts' reasons
        tid, ok, err = results_q.get()
        if not ok:
            print(f"❌ {tid} failed: {err}")


def process_account(email:str):
    global driver
    print(f"\n🔁 Processing: {email}")
    try:
        driver = DriverManager(email)
        handle_user_emails()
    except Exception as e:
        print(f"❌ Error with {email}: {e}")
    finally:
        if driver:
            driver.close()

if __name__ == "__main__":
    for email in CHROME_PROFILES:
        process_account(email)
        print("—" * 40)
        time.sleep(2)
