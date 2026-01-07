
from selenium.webdriver.common.by import By
import re
from entities.SurveyHandler import Survey
from driver_manager import DriverManager

class SekernetSurvey(Survey):
    def __init__(self, driver:DriverManager):
        super().__init__(link_texts=["סקרנט"], driver=driver)
        self.question_container = "w3-group"
        self.query_location = "w3-text-teal"
        self.continue_location = "continue"
        self.send_location = "submit"

        self.radio_container = "w3-label"
        self.radio_value_location = "span"
        self.checkbox_input = ""

    def handle_exception(self):
        try:
            divs = self.driver.find_elements(By.XPATH, "//div[contains(text(),'₪')]")
            for div in divs:
                text = div.text
                match = re.search(r"(\d[\d,]*)\s*₪", text)
                if match:
                    amount = match.group(1)
                    print(f"🔎 נמצא סכום: {amount} ₪")
        except:
            print("🔍 פגישת סקרנט.")
        print("⚠️ סקרנט - לא נמצא קישור")
