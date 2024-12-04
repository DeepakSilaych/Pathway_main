from langchain_core.prompts import ChatPromptTemplate
from utils import log_message
from database import FinancialDatabase
from pydantic import BaseModel
from typing import List
from llm import llm

# ----------------- prompts -----------------#

auto_completion_prompt = """
You are an Auto-Completion Agent responsible for completing user queries based on financial information and dataset given to you. Your task is to analyze the user’s query, infer the specific information requested (such as financial metrics, events, or trends), and auto-complete it using our database of company names and corresponding years.

#### Important ####
Data Source: Use only company names and years from the provided database. Do not invent or include data not present in the user's query.
You will be penalised if you generate a lot of suggestions which are not helpful for a financial analyst. If you can't generate a good suggestion for user return {{Suggestions:""]}}
Avoid: Unnecessary or unhelpful text. Do not compare between same companies.
DO NOT create similar suggestions for the user.
Note: Do not retrieve data from examples; they are solely for understanding.
#####################

Database:
{companies_set}

Examples:

Example 1:
Input: "Compare the net income of Microsoft and" <Assume dataset has Microsoft and Apple data for 2022>
Output: {{
    Suggestions: [
        "Compare the net income of Microsoft and Apple in 2022",
        "Compare the net income of Microsoft and Google in 2022",
        "Compare the net income of Microsoft and Amazon in 2022"
    ]
}}

Example 2:
Input: "What was the operating margin for Tesla in" <Assume dataset has Tesla data for 2021, 2022, 2023>
Output: {{
    Suggestions: [
        "What was the operating margin for Tesla in 2023?",
        "What was the operating margin for Tesla in 2022?",
        "What was the operating margin for Tesla in 2021?"
    ]
}}

Example 3:
Input: "Analyze the debt-to-equity ratio of" <Assume dataset has various companies>
Output: {{
    Suggestions: [
        "Analyze the debt-to-equity ratio of Amazon for 2023",
        "Analyze the debt-to-equity ratio of Facebook for 2022",
        "Analyze the debt-to-equity ratio of Netflix for 2021"
    ]
}}
Task: Analyze the input query and auto-complete it based on the database. Ensure the query is clear and specific.

Output Format: Always return the output in the following format:yy

{{
    Suggestions: ["<Completed query 1>", "<Completed query 2>", "<Completed query 3>"]
}}

"""
# ----------------- llm -----------------#

class Auto_Complete(BaseModel):
    Suggestions: List[str]

## FOR STRUCTURED OUTPUT
llm_ = llm.with_structured_output(Auto_Complete)

#-------------------database---------------#

## Extracting this for db state
db = FinancialDatabase()
companies_set = db.get_all_company_year_pairs()

# Reformatting the data 
formatted_data = []
for entry in companies_set:
    try:
        company_name = entry.get('company_name', 'N/A')  # Default to 'N/A' if None
        filing_year = entry.get('filing_year', 'N/A')  # Default to 'N/A' if None
        formatted_data.append(f"Company: {company_name.capitalize()}, Filing Year: {filing_year}")
    except:
        pass
formatted_data = "\n".join(formatted_data)


# ----------------- nodes -----------------#

def auto_completion(query : str):
    log_message("--- Auto Completion ---")
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", auto_completion_prompt),
            ("user", "Here is the query of user: {input}"),
        ]
    )
    generator = prompt | llm_
    response = generator.invoke({"input": query, "companies_set": formatted_data})
    response = (response.Suggestions)[:min(len(response.Suggestions), 4)]
    return response

#### Testing with these queries ####

# query = ["Hii, I want to know", "Hii, I want to know the revenue of", "Hii, I want to know the revenue of apple and ", "Hii, I want to know the revenue of apple and microsoft", "Hii, I want to know the revenue and ", "Hii, I want to know the profit of tesla",  "Hii, I want to compare the profit of tesla and microsoft"]
# query = ["Compare google and "]
# query = ["I want to know about my home in "]

print(auto_completion("Compare google and "))
