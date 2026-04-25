from langchain_core.prompts import ChatPromptTemplate

MATH_FACULTY_GENERAL = ChatPromptTemplate.from_template("""
    Ви — експертний радник університету. На основі наданого контексту, дайте персоналізовані рекомендації.
    
    Контекст: {context}
    
    Запитання користувача: {question}
    
    Дайте детальну відповідь з конкретними рекомендаціями, кроками та корисними посиланнями.
    """)

MATH_FACULTY_RECOMMENDATION = "" 

ROMANIAN_CULTURE_HELPER = ""

QA_HELPER =""

LOCATION_RECOMMENDER = """На основі наступних даних, дай відповідь на запитання користувача. 
    Не кажи слово 'опис'! Будь-ласка, дай якомога більше інформації! {description} Запитання: {question}"""

