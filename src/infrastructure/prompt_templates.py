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

LOCATION_RECOMMENDER = """На основі наступних даних, дай відповідь на запитання користувача. 
    Не кажи слово 'опис'! Будь-ласка, дай якомога більше інформації! {description} Запитання: {question}"""

