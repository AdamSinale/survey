
from MidgamSurvey import MidgamSurvey
from Panel4allSurvey import Panel4allSurvey
from PanelViewSurvey import PanelViewSurvey
from SekernetSurvey import SekernetSurvey
from SurveyHandler import Survey

class SurveyHandlerFactory:
    @staticmethod
    def get_survey(sender_key: str, driver) -> Survey:
        if sender_key == "PanelView":
            return PanelViewSurvey(driver)
        elif sender_key == "Panel4all":
            return Panel4allSurvey(driver)
        elif sender_key == "Midgam":
            return MidgamSurvey(driver)
        elif sender_key == "סקרנט":
            return SekernetSurvey(driver)
        else:
            raise ValueError(f"Unsupported sender: {sender_key}")
