# This module handles the expansion of user questions, making them more specific
# and structured to optimize document retrieval. The expanded questions provide
# clear definitions and elaborations of broad terms, improving search effectiveness.

# 1. ExpandedQuestions Class: Defines the structure for the elaborated version of the user query.
# 2. Question Expansion Process: Expands the original question by breaking it down and providing subtopics.
# 3. Database Interaction: Retrieves relevant data from the financial database to aid in expansion.
# 4. Logging: Captures logs related to the question expansion process for auditing and debugging.

from typing import List

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from utils import log_message
from database import FinancialDatabase
from prompt import prompts
import state, nodes
from llm import llm
import uuid

from utils import send_logs
from config import LOGGING_SETTINGS


class ExpandedQuestions(BaseModel):
    """The structure for elaborated question generated by the expanding the original question."""

    elaborated_questions: str = Field(
        description="Contains the elaborated question and sub questions with all terms/topics clearly explained and elaborated as subtopics "
    )


_10k_structure = prompts._10k_structure

_expansion_system_prompt1 = prompts._expansion_system_prompt1


question_expansion_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _expansion_system_prompt1),
        ("human", "Question: {question}"),
    ]
)
question_expander = question_expansion_prompt | llm.with_structured_output(
    ExpandedQuestions
)


def expand_question(state: state.OverallState):
    """
    Expand the user question to specify the broad terms clearly and optimize document retrieval.
    """
    log_message("---QUERY EXPANSION---")

    question = state["question"]
    db = FinancialDatabase()
    db_state = db.get_all_reports()
    state["db_state"] = db_state
    # res = question_expander.invoke(

    res = question_expander.invoke(
        {"structure": _10k_structure, "question": question, "db_state": db_state}
    )
    # expanded_questions = decomposed_questions.decomposed_questions

    log_message(f"Expanded question: {res}")

    expanded_question = res.elaborated_questions

    ###### log_tree part
    # import uuid , nodes
    id = str(uuid.uuid4())
    child_node = nodes.expand_question.__name__ + "//" + id
    parent_node = state.get("prev_node", "START")
    log_tree = {}

    if not LOGGING_SETTINGS["expand_question"]:
        child_node = parent_node

    log_tree[parent_node] = [child_node]
    ######

    ##### Server Logging part

    output_state = {
        "expanded_question": expanded_question,
        "db_state": db_state,
        "prev_node": child_node,
        "log_tree": log_tree,
    }

    send_logs(
        parent_node=parent_node,
        curr_node=child_node,
        child_node=None,
        input_state=state,
        output_state=output_state,
        text=child_node.split("//")[0],
    )

    ######

    return output_state
