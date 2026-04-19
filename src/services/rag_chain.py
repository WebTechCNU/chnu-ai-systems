import os
from dotenv import load_dotenv
from fastapi import Depends
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from src.infrastructure.constants import Topic
from src.infrastructure.models import MathFacultyRequest
from src.services.retriever import get_vector_store, get_vector_store_buk, get_vector_store_qa
from src.infrastructure.prompt_templates import (
    MATH_FACULTY_GENERAL, 
    QA_HELPER, 
    ROMANIAN_CULTURE_HELPER
)

load_dotenv()

OPEN_API_KEY = os.getenv("OPEN_API_KEY")
os.environ['OPENAI_API_KEY'] = OPEN_API_KEY


def query_math_faculty(question: str, chat_history: list[str], vector_store=Depends(get_vector_store)):
    rag_chain = create_rag_chain(MATH_FACULTY_GENERAL, vector_store)
    return rag_chain.invoke(question)


def query_qa(question: str, chat_history: list[str], vector_store=Depends(get_vector_store_qa)):
    rag_chain = create_rag_chain(QA_HELPER, vector_store)
    return rag_chain.invoke(question)


def query_romanian_culture(question: str, chat_history: list[str], vector_store=Depends(get_vector_store_buk)):
    rag_chain = create_rag_chain(ROMANIAN_CULTURE_HELPER, vector_store)
    return rag_chain.invoke(question)


def create_rag_chain(template: ChatPromptTemplate, vector_store):
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0
    )

    # ✅ Simple retriever (stable)
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 10}
    )

    rag_chain = (
        {
            "context": retriever,
            "question": RunnablePassthrough()
        }
        | template
        | llm
        | StrOutputParser()
    )

    return rag_chain