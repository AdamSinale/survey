
from entities.MidgamSurvey import MidgamSurvey
from entities.Panel4allSurvey import Panel4allSurvey
from entities.PanelViewSurvey import PanelViewSurvey
from entities.SekernetSurvey import SekernetSurvey
from entities.SurveyHandler import Survey
from driver_manager import DriverManager

class SurveyHandlerFactory:
    @staticmethod
    def get_survey(sender_key:str, driver:DriverManager) -> Survey:
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
