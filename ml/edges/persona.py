from langgraph.types import Send

import state


def send_personas_and_questions(state: state.OverallState):
    personas = state["personas"]
    persona_specific_questions = state["persona_specific_questions"]

    return [
        Send(
            "agent_with_persona",
            {
                "persona": persona,
                "persona_question": question,
            },
        )
        for persona, question in zip(personas, persona_specific_questions)
    ]