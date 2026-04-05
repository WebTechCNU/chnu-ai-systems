import os
from dotenv import load_dotenv
from fastapi import Depends
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from infrastructure.constants import Topic
from infrastructure.models import MathFacultyRequest
from infrastructure.models import MathFacultyRequest
from services.retriever import get_vector_store, get_vector_store_buk, get_vector_store_qa
from infrastructure.prompt_templates import MATH_FACULTY_GENERAL, QA_HELPER, ROMANIAN_CULTURE_HELPER


load_dotenv()

OPEN_API_KEY = os.getenv("OPEN_API_KEY")
os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['LANGCHAIN_ENDPOINT'] = 'https://api.smith.langchain.com'

langchain_api_key = os.getenv("LANGCHAIN_API_KEY")
os.environ['LANGCHAIN_API_KEY'] = langchain_api_key
os.environ['OPENAI_API_KEY'] = OPEN_API_KEY


def query_math_faculty(question: str, chat_history: list[str], vector_store = Depends(get_vector_store)):
    rag_chain = create_rag_chain(MATH_FACULTY_GENERAL, vector_store)
    return rag_chain.invoke(question)

def query_qa(question: str, chat_history: list[str], vector_store = Depends(get_vector_store_qa)):
    rag_chain = create_rag_chain(QA_HELPER, vector_store)
    return rag_chain.invoke(question)

def query_romanian_culture(question: str, chat_history: list[str], vector_store = Depends(get_vector_store_buk)):
    rag_chain = create_rag_chain(ROMANIAN_CULTURE_HELPER, vector_store)
    return rag_chain.invoke(question)

def create_rag_chain(template: ChatPromptTemplate, vector_store = Depends(get_vector_store)):
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0
    )

    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    rag_chain = (
        {
            "context": retriever,
            "question": RunnablePassthrough()
        }
        | MATH_FACULTY_GENERAL
        | llm
        | StrOutputParser()
)

    return rag_chain
