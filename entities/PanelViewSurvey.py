
from entities.SurveyHandler import Survey
from driver_manager import DriverManager


class PanelViewSurvey(Survey):
    def __init__(self, driver:DriverManager):
        super().__init__(link_texts=["כאן"], driver=driver)
        self.question_container = "question"
        self.query_location = "question-text"
        self.continue_location = "next"
        self.send_location = "submit"

        self.radio_container = "response"
        self.radio_value_location = "choice-text"
        self.checkbox_input = ""

    def handle_exception(self):
        print("⚠️ PanelView - לא נמצא קישור")
