from langchain_core.prompts import ChatPromptTemplate

MATH_FACULTY_GENERAL = ChatPromptTemplate.from_template("""Дай відповідь на наступне запитання, використовуючи 
    даний контекст:
    {context}

    Будь-ласка, дай якомога більше інформації!
    Не кажи слово 'контекст'
    Запитання: {question};
    """)

MATH_FACULTY_RECOMMENDATION = "" 

ROMANIAN_CULTURE_HELPER = ""

QA_HELPER =""

LOCATION_RECOMMENDER =""

