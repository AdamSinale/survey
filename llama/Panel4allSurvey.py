
from SurveyHandler import Survey

class Panel4allSurvey(Survey):
    def __init__(self, driver):
        super().__init__(link_texts=["למעבר לסקר", "לחצו כאן"],driver=driver)
        self.question_container = "questionContainer"
        self.query_location = "question_text"
        self.continue_location = "nextButton"
        self.send_location = "submit"

        self.radio_container = "answer"
        self.radio_value_location = "span"
        self.checkbox_input = ""
        self.page_container = "questionContainer"

    def handle_exception(self):
        print("⚠️ Panel4all - לא נמצא קישור")
