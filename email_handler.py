from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from entities.SurveyHandlerFactory import SurveyHandlerFactory
from entities.SurveyHandler import Survey
from driver_manager import DriverManager

SURVEY_SENDERS = ["PanelView","Panel4all","Midgam","סקרנט"]

class EmailHandler:
    def __init__(self, email_link:str, driver:DriverManager):
        self.email_link = email_link
        self.driver = driver

        self.driver.open_gmail()
        url = self.driver.open_site(self.email_link)
        print(f"###### Opened mail: {url}")

        self.handle_email()


    def handle_email(self)-> bool:
        survey_filled = False
        for _ in range(3):
            survey_filled = self.handle_email_try()
            if survey_filled:
                break
        self.delete_email()
        return survey_filled

    def handle_email_try(self) -> bool:
        survey_handler: Survey = self.get_survey_handler()
        if not survey_handler:
            return False

        link = survey_handler.get_link()
        if not link:
            return False

        href = link.get_attribute("href")
        if not href:
            return False

        survey_filled = survey_handler.fill_survey(href)
        return survey_filled

    def get_survey_handler(self) -> Survey|None:
        sender = self.get_sender()
        sender_key = self.survey_sender(sender)
        if not sender_key:
            return None

        survey_handler = SurveyHandlerFactory.get_survey(sender_key, self.driver)
        return survey_handler


    def get_sender(self) -> str:
        return self.driver.find_element(By.CLASS_NAME, "gD").text

    def survey_sender(self, sender:str) -> str:
        for key in SURVEY_SENDERS:
            if  key in sender:
                return key
        return ""

    def delete_email(self):
        url = self.driver.open_site(self.email_link)
        delete_email = self.driver.click_element(By.CLASS_NAME, "nX")
        self.driver.close()