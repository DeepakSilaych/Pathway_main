from langgraph.graph import END, StateGraph, START
import uuid

import state, nodes, edges
from utils import log_message
from nodes.question_decomposer import question_combiner
from .rag_e2e import rag_e2e


def rag1_to_rag2(state: state.InternalRAGState):
    if len(state["question_group"][-1]) == 1:
        return nodes.combine_answers.__name__
    else:
        return rag2.__name__


def rag2_to_rag3(state: state.InternalRAGState):
    if len(state["question_group"][-1]) == 2:
        return nodes.combine_answers.__name__
    else:
        return rag3.__name__


def rag1(state: state.InternalRAGState):
    question_group_id = str(uuid.uuid4())
    res = rag_e2e.invoke(
        {
            "question": state["question_group"][-1][0],
            "question_group_id": question_group_id,
        }
    )
    answer = res["answer"]
    # citations = res["citations"]
    return {
        # "decomposed_questions": [prev_question],
        "decomposed_answers": [answer],
        "combined_documents": res["documents"],
        # "combined_citations": [citations],
        "question_group": [state["question_group"]],
        # "number_of_question" : [len(state["question_group"])]
    }


def rag2(state: state.InternalRAGState):
    # prev_question = None
    # prev_answer = None
    question_group_id = str(uuid.uuid4())
    # for question in state["question_group"]:
    #     # question_group_id=state.get("question_group_id", 1)
    #     if prev_answer:
    question = question_combiner.invoke(
        {
            "next_question": state["question_group"][-1][1],
            "prev_question": state["question_group"][-1][0],
            "prev_answer": state["decomposed_answers"][0],
        }
    ).combined_question
    log_message(f"Combined question:  {question}", f"question_group{question_group_id}")
    res = rag_e2e.invoke({"question": question, "question_group_id": question_group_id})
    answer = res["answer"]
    # citations = res["citations"]

    # decomposed_answers = state["decomposed_answers"][-1].append(answer)

    return {
        # "decomposed_questions": [prev_question],
        "decomposed_answers": [answer],
        "combined_documents": res["documents"],
        # "combined_citations": [citations],
        "question_group": [state["question_group"]],
        # "number_of_question" : [len(state["question_group"])]
    }


def rag3(state: state.InternalRAGState):
    # prev_question = None
    # prev_answer = None
    question_group_id = str(uuid.uuid4())
    # for question in state["question_group"]:
    #     # question_group_id=state.get("question_group_id", 1)
    #     if prev_answer:
    question = question_combiner.invoke(
        {
            "next_question": state["question_group"][-1][2],
            "prev_question": state["question_group"][-1][1],
            "prev_answer": state["decomposed_answers"][1],
        }
    ).combined_question
    log_message(f"Combined question:  {question}", f"question_group{question_group_id}")
    res = rag_e2e.invoke({"question": question, "question_group_id": question_group_id})
    answer = res["answer"]
    # citations = res["citations"]

    # decomposed_answers = state["decomposed_answers"][-1].append(answer)

    return {
        # "decomposed_questions": [prev_question],
        "decomposed_answers": [answer],
        "combined_documents": res["documents"],
        # "combined_citations": [citations],
        # "number_of_question" : [len(state["question_group"])]
        "question_group": [state["question_group"]],
    }


# fmt: off
graph = StateGraph(state.OverallState)
graph.add_node(nodes.process_query.__name__, nodes.process_query)
graph.add_node(nodes.check_safety.__name__, nodes.check_safety)
graph.add_node(nodes.decompose_question_v2.__name__, nodes.decompose_question_v2)
graph.add_node(nodes.ask_clarifying_questions.__name__, nodes.ask_clarifying_questions)
graph.add_node(nodes.refine_query.__name__, nodes.refine_query)
graph.add_node(nodes.expand_question.__name__, nodes.expand_question)
graph.add_node(rag1.__name__, rag1)
graph.add_node(rag2.__name__, rag2)
graph.add_node(rag3.__name__, rag3)
graph.add_node(nodes.combine_answers.__name__, nodes.combine_answers)
graph.add_node(nodes.ask_follow_up_questions.__name__, nodes.ask_follow_up_questions)

graph.add_edge(START, nodes.check_safety.__name__)
graph.add_edge(nodes.check_safety.__name__, nodes.process_query.__name__)
graph.add_conditional_edges(
    nodes.process_query.__name__,
    edges.route_initial_query,
    {
        nodes.ask_clarifying_questions.__name__: nodes.ask_clarifying_questions.__name__,
        "end_workflow": END
    }
)
graph.add_conditional_edges(
    nodes.check_safety.__name__,
    edges.query_modified_or_not,
    {
        nodes.process_query.__name__: nodes.process_query.__name__,
        END:END
    }
)
graph.add_conditional_edges(
        nodes.ask_clarifying_questions.__name__,
        edges.refine_query_or_not,
        {
            nodes.decompose_question_v2.__name__: nodes.decompose_question_v2.__name__,
            nodes.refine_query.__name__: nodes.refine_query.__name__
        }
)
graph.add_edge(nodes.refine_query.__name__, nodes.expand_question.__name__ )
graph.add_edge(nodes.expand_question.__name__, nodes.decompose_question_v2.__name__)
graph.add_conditional_edges(nodes.decompose_question_v2.__name__, edges.send_decomposed_question_groups_with_serial_hack, [rag1.__name__]) # type: ignore
graph.add_conditional_edges(rag1.__name__, rag1_to_rag2,
                                [
                                nodes.combine_answers.__name__,
                                rag2.__name__,
                                ])
graph.add_conditional_edges(rag2.__name__, rag2_to_rag3,
                                [
                                nodes.combine_answers.__name__,
                               rag3.__name__
                                ])
graph.add_edge(rag3.__name__, nodes.combine_answers.__name__)
graph.add_edge(nodes.combine_answers.__name__,nodes.ask_follow_up_questions.__name__)
graph.add_edge(nodes.ask_follow_up_questions.__name__,END)
# fmt: on
# Set up memory
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
series_parallel_with_HITL = graph.compile(
    checkpointer=memory, interrupt_before=[nodes.refine_query.__name__]
)