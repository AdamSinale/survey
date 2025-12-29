
from entities.SurveyHandler import Survey

class Panel4allSurvey(Survey):
    def __init__(self):
        super().__init__(link_texts=["למעבר לסקר", "לחצו כאן"])
        self.question_container = "questionContainer"
        self.query_location = "question_text"
        self.continue_location = "nextButton"
        self.send_location = "submit"
        self.radio_container = "answer"
        self.radio_value_location = "span"
        self.table_question_title = "title"
        self.table_options_containers = "headers"

    def handle_exception(self):
        print("⚠️ Panel4all - לא נמצא קישור")
