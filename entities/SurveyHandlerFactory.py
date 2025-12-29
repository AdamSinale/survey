
from entities.MidgamSurvey import MidgamSurvey
from entities.Panel4allSurvey import Panel4allSurvey
from entities.PanelViewSurvey import PanelViewSurvey
from entities.SekernetSurvey import SekernetSurvey
from entities.SurveyHandler import Survey

class SurveyHandlerFactory:
    @staticmethod
    def get_survey(sender_key: str) -> Survey:
        if sender_key == "PanelView":
            return PanelViewSurvey()
        elif sender_key == "Panel4all":
            return Panel4allSurvey()
        elif sender_key == "Midgam":
            return MidgamSurvey()
        elif sender_key == "סקרנט":
            return SekernetSurvey()
        else:
            raise ValueError(f"Unsupported sender: {sender_key}")
