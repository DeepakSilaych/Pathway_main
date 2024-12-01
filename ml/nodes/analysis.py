from typing import List,Tuple
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
import state
from llm import llm
from nodes.KPIs import possible_KPIs
from functools import reduce



class ARQuestions(BaseModel):
    """The structure for decomposed question generated by the decomposing the original question."""

    ar_questions: List[str] = Field(
        description="Generated questions about Analysis required by Analysts to solve the original question."
    )
## assumes exact match
def extract_KPIs_from_fields(fields: List[str]) -> Tuple[List[List[str]], List[str]]:
    kpi_list = list(map(lambda k: possible_KPIs.get(k,{}).get("KPIs",[])))
    aggregated = list(reduce(lambda x,y: x|y,kpi_list))
    return kpi_list,aggregated


_ar_questions_prompt_kpi = """
You are an expert assistant that specialises in interacting with a retreival system over financial reports. You are tasked with performing financial analysis of the following types: {analysis_list}

Based on the types of analyses to be performed, you know of the following types of analyses that can be performed: {kpi_list}

Given this information, you are tasked with finding the KPIs that are most relevant to the user's query. 
"""

## TODO ##
def generate_KPI_based_questions(state: state.OverallState):
    """
    Generates questions based on the KPIs for the user to answer. How much should this be LLM dependent?
    
    Currently the LLM decides how to generate the questions based on the KPIs.
    """
    pass
    ### check if you need to 


_ar_questions_prompt = """
You are an expert assistant that specialises in interacting with a retreival system over financial reports. 
Your client is a team of financial analysts who wish to answer the following:{question}

They wish to run the following type of Analyses: {analysis_types}

The team contains the following members: {analyst_info}

Given these conditions, pertaining to all the analyses to be done, generate a list of prerequisite questions that need to be asked to the retrieval engine for the analysts to comprehensively perform their analyses. Note that the analysts absolutely rely on you for any specific factual information related to the companiy(ies).
You may walk through your reasoning for the type of questions chosen before giving your final answer. 

Your questions must be direct enough that it can be directly picked up from the financial report.

"""


def get_relevant_questions(state: state.OverallState) -> state.InternalRAGState:
    """
    Extracts all relevant questions for analysis
    Sends them to the RAG pipeline
    """
    prompt = _ar_questions_prompt.format(
        question=state["question"],
        analysis_types=state["user_response_for_analysis"],
        analyst_info=", ".join(analyst.role for analyst in state["analysts"]),
    )
    generator = llm.with_structured_output(ARQuestions)

    answer = generator.invoke(prompt)
    query_list = answer.ar_questions
    # state["analysis_question_groups"] = query_list
    # return {"decomposed_questions":query_list}
    return {"analysis_question_groups": query_list}


_ar_v2_questions_prompt = """
You are an expert assistant that specialises in interacting with a retreival system over financial reports. 
Your client is a team of financial analysts who wish to answer the following:{question}

They wish to run the following type of Analyses: {analysis_types}.

Write a series of queries to extract Key Performance Indicators (KPIs) from the financial reports that are relevant to the question, which would be required for each analyst to perform their analysis.
"""


def get_relevant_questions_v2(state: state.OverallState) -> state.InternalRAGState:
    """Uses domain knowledge for extracting performance metrics"""
    prompt = _ar_v2_questions_prompt.format(
        question=state["question"],
        analysis_types=state["user_response_for_analysis"],
        analyst_info=", ".join(analyst.role for analyst in state["analysts"]),
    )
    generator = llm.with_structured_output(ARQuestions)

    answer = generator.invoke(prompt)
    query_list = answer.ar_questions
    # state["analysis_question_groups"] = query_list
    # return {"decomposed_questions":query_list}
    return {"analysis_question_groups": query_list}


class FinalAnswer(BaseModel):
    answer: str = Field(
        description="Final answer based on individual analyses of the personas."
    )


_conclusion_prompt = """You are an expert agent tasked with combining the results of multiple financial analysts to answer the following question:
{question}

Your team of analysts has gathered their own data and analyses. You are tasked with combining these analyses so as to comprehensively answer the question.

.
"""


### TODO: @Geet How to combine citations?
## This may be redundant wrt the combiner in persona.py
def combine_analysis_questions(state: state.InternalRAGState) -> state.OverallState:
    """
    Joins RAG responses and asks the LLM to Generate the response
    """
    context_questions = state["analysis_subquestions"]
    context_responses = state["analysis_subresponses"]
    qa_pairs = "####\n".join(
        [f"{quer}:\n{ans}\n" for quer, ans in zip(context_questions, context_responses)]
    )
    prompt = _conclusion_prompt.format(question=state["question"])
    structured_prompt = ChatPromptTemplate.from_messages(
        [("system", prompt), ("human", "Analyses: {context}")]
    )
    answer_generator = structured_prompt | llm.with_structured_output(FinalAnswer)
    answer = answer_generator.invoke({"context": qa_pairs})
    return {"final_answer": answer.answer}


## OLD CODE ###
def append_analysis_questions(state: state.InternalRAGState) -> state.OverallState:
    """
    Collects and joins RAG responses
    """
    context_questions = state["analysis_subquestions"]
    context_responses = state["analysis_subresponses"]

    qa_pairs = "####\n".join(
        [f"{quer}\n{ans}" for quer, ans in zip(context_questions, context_responses)]
    )
    return {"analysis_retrieved_context": qa_pairs}