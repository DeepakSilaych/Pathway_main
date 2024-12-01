from langgraph.graph import END, StateGraph, START
import state, nodes, edges

# fmt: off
graph = StateGraph(state.InternalRAGState)
graph.add_node(nodes.retrieve_documents.__name__ , nodes.retrieve_documents)
graph.add_node(nodes.generate_answer.__name__ , nodes.generate_answer)
graph.add_node(nodes.check_hallucination.__name__ , nodes.check_hallucination)
graph.add_node(nodes.search_web.__name__ , nodes.search_web)

graph.add_edge(START , nodes.retrieve_documents.__name__)
graph.add_edge(nodes.retrieve_documents.__name__ , nodes.generate_answer.__name__)
graph.add_edge(nodes.generate_answer.__name__ , nodes.check_hallucination.__name__)
graph.add_conditional_edges(
    nodes.check_hallucination.__name__, 
    edges.assess_hallucination,
    {
        "end_workflow" : END , 
        nodes.generate_answer.__name__: nodes.generate_answer.__name__,
        nodes.search_web.__name__: nodes.search_web.__name__,
    },
)
graph.add_edge(nodes.generate_answer.__name__ , nodes.check_hallucination.__name__)
graph.add_edge(nodes.search_web.__name__ , END)
# fmt: on


with_hallucination_checker = graph.compile()