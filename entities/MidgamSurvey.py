
from entities.SurveyHandler import Survey
from driver_manager import DriverManager

class MidgamSurvey(Survey):
    def __init__(self, driver:DriverManager):
        super().__init__(link_texts=["כניסה מותאמת"], driver=driver)
        self.question_container = "w3-group"
        self.query_location = "w3-text-teal"
        self.continue_location = "continue"
        self.send_location = "submit"

        self.radio_container = "w3-label"
        self.radio_value_location = "span"
        self.checkbox_input = ""

    def handle_exception(self):
        print("⚠️ Midgam - לא נמצא קישור")

