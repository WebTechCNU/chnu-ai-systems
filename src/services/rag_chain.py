import os
from dotenv import load_dotenv
from fastapi import Depends
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from infrastructure.models import MathFacultyRequest
from infrastructure.models import MathFacultyRequest
from services.retriever import get_vector_store, load_vector_store
from infrastructure.prompt_templates import MATH_FACULTY_GENERAL


load_dotenv()

OPEN_API_KEY = os.getenv("OPEN_API_KEY")
os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['LANGCHAIN_ENDPOINT'] = 'https://api.smith.langchain.com'

langchain_api_key = os.getenv("LANGCHAIN_API_KEY")
os.environ['LANGCHAIN_API_KEY'] = langchain_api_key
os.environ['OPENAI_API_KEY'] = OPEN_API_KEY



def query(question: str, chat_history: list[str], vector_store = Depends(get_vector_store)):
    rag_chain = create_rag_chain(vector_store)
    return rag_chain.invoke(question)

def create_rag_chain(vector_store = Depends(get_vector_store)):
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
