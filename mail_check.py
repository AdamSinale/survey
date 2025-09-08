import os
import time
from SurveyHandlerFactory import SurveyHandlerFactory
from selenium.webdriver.common.by import By
from mail_setup import get_mail_driver, open_gmail  # את זה נשתמש גם בתוך find/delete
import json

try:
    with open("emails.json", 'r', encoding='utf-8') as f:
        CHROME_PROFILES = json.load(f)
except Exception as e:
    print(f"❌ שגיאה בטעינת קובץ פרופילים: {e}")
    CHROME_PROFILES = {}
SURVEY_SENDERS = ["PanelView","Panel4all","Midgam","סקרנט"]

def get_profile_info(email):
    profile = CHROME_PROFILES.get(email)
    if not profile:
        raise Exception(f"No Chrome profile found for {email}")
    profile_num = profile["profile_num"]
    profile = f"Profile {profile_num}"
    return profile

def get_users_emails(driver):
    emails = driver.find_elements(By.CLASS_NAME, "zA")
    return emails
def get_email_sender(email):
    sender = email.find_element(By.CLASS_NAME, "yX").text
    return sender
def get_sender_key(sender):
    for key in SURVEY_SENDERS:
        if key in sender:
            return key
    return None

def delete_email(driver, idx):
    try:
        print("📥 חוזר לתיבת הדואר...")
        open_gmail(driver)
        time.sleep(2)
        emails_elements = get_users_emails(driver)
        email = emails_elements[idx]
        click_email_survey(email)
        more_button = driver.find_element(By.XPATH, "//div[@role='button' and @aria-label='More message options']")
        more_button.click()
        menu_items = driver.find_elements(By.XPATH, "//div[@role='menuitem' and not(@aria-hidden='true')]")
        for item in menu_items:
            text = item.text.strip().lower()
            if "delete this message" in text:
                if item.is_displayed():
                    item.click()
                return
        print("✅ נלחץ כפתור More message options בהצלחה")
    except Exception as e:
        print(f"❌ שגיאה במחיקת מייל: {e}")
def click_email_survey(email):
    email.click()
    time.sleep(1.3)
def go_back(driver):
    driver.back()
    time.sleep(2)

def find_survey_emails(driver,email):
    """ מחפש מיילים עם סקרים בתיבת הדואר """
    try:
        while True:
            open_gmail(driver,email)
            emails_elements = get_users_emails(driver)
            if not emails_elements: break
            try:
                email = emails_elements[0]
                sender = get_email_sender(email)
                sender_key = get_sender_key(sender)
                if not sender_key:
                    delete_email(driver,0)
                    continue
                time.sleep(1)
                click_email_survey(email)
                surveyHhandler = SurveyHandlerFactory.get_survey(sender_key, driver)
                link = surveyHhandler.get_link()
                if link:
                    href = link.get_attribute("href")
                    print(f"🔗 Survey link found: {href}")
                    time.sleep(1)
                    driver.get(href)
                    time.sleep(2)
                    if(surveyHhandler.fill_survey()): delete_email(driver,0)
                else:  delete_email(driver,0)
            except Exception as e:
                print(f"❌ Error processing email: {e}")
                continue
    except Exception as e:
        print(f"Error searching for survey emails: {e}")

def process_account(email):
    """ מטפל בחשבון אחד מהתחלה עד הסוף """
    try:
        print(f"\n🔁 Processing: {email}")
        profile = get_profile_info(email)
        driver, cleanup = get_mail_driver(profile)
        try:
            find_survey_emails(driver,email)
        finally:
            cleanup()
    except Exception as e:
        print(f"❌ Error with {email}: {e}")

if __name__ == "__main__":
    for email in CHROME_PROFILES:
        process_account(email)
        print("—" * 40)
        time.sleep(2)
