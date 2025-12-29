import os
import time
from entities.SurveyHandlerFactory import SurveyHandlerFactory
from selenium.webdriver.common.by import By
import json

from driver_manager import DriverManager

with open("emails.json", 'r', encoding='utf-8') as f:
    CHROME_PROFILES = json.load(f)

SURVEY_SENDERS = ["PanelView","Panel4all","Midgam","סקרנט"]

def open_gmail(email=""):
    DriverManager.driver().get("https://mail.google.com/mail/u/0/#inbox")
    DriverManager.wait().until(lambda d: "mail.google.com" in d.current_url or "accounts.google.com" in d.current_url)
    url = DriverManager.driver().current_url
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

# def delete_email(driver, idx):
#     try:
#         print("📥 חוזר לתיבת הדואר...")
#         open_gmail(driver)
#         time.sleep(2)
#         emails_elements = get_users_emails(driver)
#         email = emails_elements[idx]
#         click_email_survey(email)
#         more_button = driver.find_element(By.XPATH, "//div[@role='button' and @aria-label='More message options']")
#         more_button.click()
#         menu_items = driver.find_elements(By.XPATH, "//div[@role='menuitem' and not(@aria-hidden='true')]")
#         for item in menu_items:
#             text = item.text.strip().lower()
#             if "delete this message" in text:
#                 if item.is_displayed():
#                     item.click()
#                 return
#         print("✅ נלחץ כפתור More message options בהצלחה")
#     except Exception as e:
#         print(f"❌ שגיאה במחיקת מייל: {e}")

def go_back():
    DriverManager.driver().back()
    time.sleep(2)

def find_survey_emails(email):
    try:
        open_gmail(email)
        emails = DriverManager.all_elements(By.CLASS_NAME, "zA")
        if not emails: return
    except Exception as e:
        print(f"Error searching for survey emails: {e}")
        return

    emails_to_delete = []
    emails_to_fill = []

    for email in emails:
        try:
            sender = DriverManager.find_parents_element(email, By.CLASS_NAME, "yX").text
            sender_keys = [key for key in SURVEY_SENDERS if key in sender]
            if not sender_keys:
                emails_to_delete.append(email)
                continue
            email.click()
            surveyHandler = SurveyHandlerFactory.get_survey(sender_keys[0])
            link = surveyHandler.get_link()

            successfuly_filled = False
            if link:
                href = link.get_attribute("href")
                if not href:
                    return
                print(f"🔗 Survey link found: {href}")
                time.sleep(1)
                DriverManager.driver().get(href)
                time.sleep(2)
                successfuly_filled = surveyHandler.fill_survey()

            if not link or successfuly_filled:
                emails_to_delete.append(email)
        except Exception as e:
                print(f"❌ Error processing email: {e}")

def process_account(email):
    try:
        print(f"\n🔁 Processing: {email}")
        profile = get_profile_info(email)
        DriverManager.init(profile)
        try:
            find_survey_emails(email)
        finally:
            DriverManager.close()
    except Exception as e:
        print(f"❌ Error with {email}: {e}")

if __name__ == "__main__":
    for email in CHROME_PROFILES:
        process_account(email)
        print("—" * 40)
        time.sleep(2)
