from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from typing import Optional

import state , nodes
from llm import llm
from utils import log_message


class HallucinationGrade(BaseModel):
    """Binary score for hallucination check on generated answers."""

    binary_score: str = Field(
        description="Answer contains hallucination, 'yes' or 'no'"
    )
    reason : Optional[str] = Field(default = None , description = "Reason for hallucination if binary score is 'Yes'")


class HallucinationGraderInput(BaseModel):
    answer: str
    supporting_documents: str


_system_prompt = """You are a grader assessing if the generated answer contains hallucinations based on the supporting documents.
Your task is to check if the generated answer is consistent with the information present in the supporting documents.

1. Hallucination not present
- Minor paraphrasing, inferred conclusions, or rephrased content should not be flagged as hallucinations as long as the key facts and information align with the documents.
- The answer might contain information that is inferred from multiple lines in the context.
- Be slightly lenient in grading hallucination for answers with numbers when words like 'around' , 'approx' are used in the answer. 

2. Hallucination Present
- Only label the answer as hallucinated if it contains claims that are **completely different**, unsupported, or contradicted by the supporting documents.
- If the answer makes any factual claims or includes details not present in the documents, or if it contradicts the evidence provided, then it should be flagged as hallucinated.


Provide a binary score 'yes' or 'no' to indicate whether the answer contains hallucinations:
- if 'yes' add a reason for the hallucination in the string. 
- 'no' if it aligns well with the supporting documents even if paraphrased."""

hallucination_grade_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _system_prompt),
        (
            "human",
            "Generated answer: \n\n {answer} \n\n Supporting documents: {supporting_documents}",
        ),
    ]
)

hallucination_grader = hallucination_grade_prompt | llm.with_structured_output(
    HallucinationGrade
)


def check_hallucination(state: state.InternalRAGState):
    """
    Determines whether the generated answer contains hallucinations based on supporting documents.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updates answer with a hallucination flag if hallucinations are detected
    """
    question_group_id = state.get("question_group_id",1)
    log_message(
        "---CHECK GENERATED ANSWER FOR HALLUCINATIONS---",
        f"question_group{question_group_id}",
    )
    answer = state["answer"]
    try:
        supporting_documents = " ".join(
            [doc.page_content for doc in state["documents"]]
        )
    except:
        supporting_documents = " ".join([" ".join(doc) for doc in state["documents"]])
    # supporting_documents = " ".join([doc.page_content for doc in state["documents"]])

    # Score the answer
    score = hallucination_grader.invoke(
        {"answer": answer, "supporting_documents": supporting_documents}
    )
    hallucination_flag = score.binary_score  # type: ignore
    hallucination_reason = score.reason

    if hallucination_flag == "yes":
        log_message(
            "---GRADE: ANSWER CONTAINS HALLUCINATIONS---",
            f"question_group{question_group_id}",
        )
        state["answer_contains_hallucinations"] = True
        state["hallucination_reason"] = hallucination_reason
    else:
        log_message(
            "---GRADE: ANSWER DOES NOT CONTAIN HALLUCINATIONS---",
            f"question_group{question_group_id}",
        )
        state["answer_contains_hallucinations"] = False
        state["hallucination_reason"] = "None"

    state["hallucinations_retries"] = state.get("hallucinations_retries", 0)
    state["hallucinations_retries"] += 1

    # ##### log_tree part
    # curr_node = nodes.check_hallucination.__name__
    # prev_node = state.get("prev_node" , "")
    # state["log_tree"][prev_node] = [{"node" : curr_node , "state" : state}]

    # #####

    return state