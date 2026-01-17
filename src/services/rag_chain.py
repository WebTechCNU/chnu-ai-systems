from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from retriever import load_vector_store
from models.prompt_templates import MATH_FACULTY_GENERAL


vector_store = load_vector_store()


def create_rag_chain():
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
