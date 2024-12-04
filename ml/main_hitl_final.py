from dotenv import load_dotenv
import os

load_dotenv()

from utils import log_message
import config
# from workflows.repeater_with_HITL import repeater_with_HITL as app
from workflows.e2e import e2e as app

# ques = "if i had 3 firearms and you had 4 firearms, how many firearms would we have in total? "
# ques = "jp morgan ceo? " #input("User: ") 
# ques = "Analyse google's revenue in 2021"
ques = "What is google's total revenue progression year by year from 2021 to 2023? Only consider google."
# ques = "What is Apple's total revenue for the fourth quarter of 2022 in USD?"
initial_input = {
    "question": ques,
}  

# Initialize clarifications list
clarifications = []

# Thread
thread = {"configurable": {"thread_id": "1"}}

# Run the graph until the first interruption
for event in app.stream(initial_input, thread, stream_mode="values"):
    print(event)

while True:
    # Get the latest state
    state = app.get_state(thread).values
    clarifying_questions = state.get("clarifying_questions", [])

    # Check if the last clarifying question exists and requires clarification
    if clarifying_questions and clarifying_questions[-1]["question_type"] != "none":
        log_message("---ASKING USER FOR CLARIFICATION---")
        question = clarifying_questions[-1]
        question_text = question.get("question", "")
        question_options = question.get("options", None)
        question_type = question.get("question_type", "direct-answer")

        # Display the question and handle response based on the type
        if question_type in ["multiple-choice", "single-choice"] and question_options:
            idx = list(range(1,len(question['options'])+1))
            options = '\n'.join([f"({i}) {option}" for i, option in zip(idx, question['options'])])
            user_response = input(f"{question['question']}\nOptions:\n{options}\nChoose any option: ").replace(" ", "").split(',')
            answers = "; ".join([question['options'][int(i)-1] for i in user_response])
            clarifications.append(answers)
        else:
            user_response = input(f"{question['question']}: ")
            clarifications.append(user_response)

        # Update the state with the user's clarifications
        app.update_state(thread, {"clarifications": clarifications})
    else:
        log_message("No further clarifications required.")
        break

    # Run the graph to geenerate subsequent clarifying questions
    for event in app.stream(None, thread, stream_mode="values", subgraphs=True):
        print(event)

for event in app.stream(None, thread, stream_mode="values", subgraphs=True):
    print(event)

state = app.get_state(thread).values
print(state)
print("FINAL ANSWER:", state.get("final_answer",state.get("answer",None)))

with open("pipeline_log.txt", "w") as file:
    pass

