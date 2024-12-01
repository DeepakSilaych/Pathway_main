from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
import state
from llm import llm
from nodes.KPIs import possible_KPIs

















def agent_node_v1(state: state.OverallState):
    """Node for the Agent to answer"""
    analyst_info = ", ".join(analyst.role for analyst in state["analysts"])
    context = state.get("messages", "<<This is the start of conversation>>")
    retrieved = state.get("analysis_retrieved_context", "None")

    prompt = _agent_answer_prompt.format(
        goals=state["analyst"], question=state["question"], analyst_info=analyst_info
    )
    structured_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt),
            (
                "human",
                "Relevant Information fetched:{retrieved} \n\n Discussion till now is: {context}",
            ),
        ]
    )
    agent_answer_generator = structured_prompt | llm.with_structured_output(
        AnalystResponse
    )
    answer = agent_answer_generator.invoke({"context": context, "retrieved": retrieved})
    message = answer.current_analyst + ":\n" + answer.response
    return {
        "messages": [message],
        "analyst": answer.next_analyst,
        "num_discussion": state["num_discussion"] + 1,
    }





class ARQuestions(BaseModel):
    """The structure for decomposed question generated by the decomposing the original question."""

    ar_questions: List[str] = Field(
        description="Generated questions about Analysis required by Analysts to solve the original question."
    )


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


def combine_analysis_questions(state: state.InternalRAGState) -> state.OverallState:
    """
    Collects and joins RAG responses
    """
    context_questions = state["analysis_subquestions"]
    context_responses = state["analysis_subresponses"]

    qa_pairs = "####\n".join(
        [f"{quer}\n{ans}" for quer, ans in zip(context_questions, context_responses)]
    )
    return {"analysis_retrieved_context": qa_pairs}


class AnalystResponseV2(BaseModel):
    current_analyst: str = Field(description="Role of the current analyst.")
    response: str = Field(
        description="Response provided by current analyst which adds information to the discussion."
    )
    tool_input: Optional[str] = Field(
        description="If the next step corresponds to a tool, the input to the tool."
    )
    next_step: str = Field(
        description="Next step in the conversation, role of analyst or name of tool."
    )


_agent_answer_prompt_v2 = """You are an expert analyst with the following background {goals}.\n
You are part of a discussion about solving a question with these analysts (including yourself): {analyst_info}.\n
The question about which we are discussing is:
{question}.

You also have access to the following tools: a retrieval query engine over a set of financial report and the web (next_step = "retrieve"), 
and a calculator tool for calculations involving mathematical quantities (next_step = "calculate"). The calculator must be supplies the necessary input numbers, while the retrieval engine must be supplied a query.\n

Provide your response in a concise manner (max 1 statement) that continues the discussion with the goal of reaching a conclusive answer to the question.\n
Output the next step of the conversation, which may be another analyst or a tool. Note that an analyst may be called any number of times till a conclusion is reached.

You may even ask some query to another analyst if needed (provide their role as the next_step). Be precise and to the point.\n

If the discussion has reached to a conclusion that sufficiently responds to the question, the next_step should be "None".
"""


def agent_node_v2(state: state.OverallState):
    "Node with additional tools for Agent"
    analyst_info = ", ".join(analyst.role for analyst in state["analysts"])
    context = state.get("messages", "<<This is the start of conversation>>")
    retrieved = state.get("analysis_retrieved_context", "None")

    prompt = _agent_answer_prompt_v2.format(
        goals=state["analyst"], question=state["question"], analyst_info=analyst_info
    )
    structured_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", prompt),
            (
                "human",
                "Relevant Information fetched:{retrieved} \n\n Discussion till now is: {context}",
            ),
        ]
    )

    agent_answer_generator = structured_prompt | llm.with_structured_output(
        AnalystResponseV2
    )
    answer = agent_answer_generator.invoke({"context": context, "retrieved": retrieved})
    message = answer.current_analyst + ":\n" + answer.response

    if answer.tool_input:
        new_dict = {"tool_query": answer.tool_input, "next_step": answer.next_step}
        message += f"\n Tool Query: {answer.tool_input}"
    else:
        new_dict = {"next_step": answer.next_step, "analyst": answer.next_step}

    return {
        "messages": [message],
        "num_discussion": state["num_discussion"] + 1,
    } | new_dict


def update_conversation(state: state.OverallState) -> state.OverallState:
    """
    Updates the conversation with the latest message
    """

    return {"messages": [f"\nTool: {state['tool_response']}"]}