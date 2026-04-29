from enum import Enum

class Topic(Enum):
    MATH_FACULTY = "math-faculty"
    ROMANIAN_CULTURE = "romanian-culture"
    QA_HELPER = "qa-helper"
    LOCATIONS_HELPER = "locations-helper"

class TestCase(str, Enum):
    WEB_PAGE = "web_page"
    API_ENDPOINT = "api_endpoint"
    LOGS = "logs"
    UNKNOWN = "unknown"

