import time
from entities.SurveyHandlerFactory import SurveyHandlerFactory
from selenium.webdriver.common.by import By
import json

from driver_manager import DriverManager
from email_handler import EmailHandler

with open("emails.json", 'r', encoding='utf-8') as f:
    CHROME_PROFILES = json.load(f)

SURVEY_SENDERS = ["PanelView","Panel4all","Midgam","סקרנט"]

def open_gmail(email = "", url = "https://mail.google.com/mail/u/0/#inbox"):
    url = DriverManager.open_site(url)
    if "accounts.google.com" in url:
        try:
            email_input = DriverManager.click_element(By.ID, "identifierId")
            email_input.clear()
            email_input.send_keys(email)

            next_btn = DriverManager.click_element(By.ID, "identifierNext")
            next_btn.click()

            password_input = DriverManager.click_element(By.NAME, "Passwd")
            password_input.clear()
            password_input.send_keys("Adam1Idan2")

            next_btn = DriverManager.click_element(By.ID, "passwordNext")
            next_btn.click()
        finally: return True
    if "mail.google.com/mail" in url:
        return True

def get_profile_info(email):
    profile = CHROME_PROFILES.get(email)
    if not profile:
        raise Exception(f"No Chrome profile found for {email}")
    profile_num = profile["profile_num"]
    profile = f"Profile {profile_num}"
    return profile

def go_back():
    DriverManager.driver().back()
    time.sleep(2)

def find_survey_emails(email):
    try:
        open_gmail(email)
        email_cons = DriverManager.all_elements(By.CLASS_NAME, "zA")
        if not email_cons: return
    except Exception as e:
        print(f"Error searching for survey emails: {e}")
        return

    for email_con in email_cons:
        try:
            sender = DriverManager.find_element(By.CLASS_NAME, "yX", email_con).text
            sender_keys = [key for key in SURVEY_SENDERS if key in sender]
            if not sender_keys:
                # emails_to_delete.append(email_con)
                continue
            email_con.click()
            survey_handler = SurveyHandlerFactory.get_survey(sender_keys[0])
            link = survey_handler.get_link()

            successfuly_filled = False
            if link:
                href = link.get_attribute("href")
                if not href:
                    return
                print(f"🔗 Survey link found: {href}")
                DriverManager.open_site(href)
                successfuly_filled = survey_handler.fill_survey()

            if not link or successfuly_filled:
                # emails_to_delete.append(email)
                continue
        except Exception as e:
                print(f"❌ Error processing email: {e}")

def process_account(email):
    try:
        print(f"\n🔁 Processing: {email}")
        profile = get_profile_info(email)
        DriverManager.init(profile)
        find_survey_emails(email)
    except Exception as e:
        print(f"❌ Error with {email}: {e}")
    finally:
        DriverManager.close()

if __name__ == "__main__":
    for email in CHROME_PROFILES:
        process_account(email)
        print("—" * 40)
        time.sleep(2)
