import json
from typing import Dict, Optional

from langchain.prompts import ChatPromptTemplate

from llm import llm
from utils import log_message

_system_prompt = """
You are an assistant that takes metadata in the form of a dictionary and converts it into a series of JMESPath expressions that can be used for filtering metadata.

The metadata input is in the form:
{{
    "company_name": "Apple",
    "year": "2022",
}}

You need to generate the corresponding JMESPath expressions that would be used to filter documents based on the metadata fields.

Return the JMESPath expressions as a string according to the exact format below. 
The expressions should be suitable for filtering the metadata keys like 'company_name' and 'year'.

JMESPATH Expression examples : "year == `2022` && company_name == `Alphabet Inc.`"
JMESPATH Expression examples : "year == `2021` || "year == `2022`"
"""

# Define the prompt template for processing metadata to JMESPath expressions
metadata_prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", _system_prompt),
        (
            "human",
            "Metadata: {metadata}\nConvert this metadata into JMESPath expressions for filtering.",
        ),
    ]
)

metadata_converter = metadata_prompt_template | llm.with_structured_output(list)

_extract_parent_system_prompt = """
    1. You are an assistant who knows all about Large scale and small scale parent companies and their sub companies and products. 
    2. From the company name in the metadata provided in the input you need to return the name of the parent company owning that small company or product. 
    3. Make sure to return only the name of the parent company as a word and nothing else . 
    4. Make sure that your output is only 1-2 words containing the name of the parent company. 
    5. Your output should not be a sentence.
"""

extract_parent_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _extract_parent_system_prompt),
        (
            "human",
            "Give the name of the parent company for the company or product mentioned in the metadata: {metadata}.",
        ),
    ]
)

parent_extractor = extract_parent_prompt | llm


# Not working pretty well (output format is not always JMESpath)
def convert_metadata_to_jmespath_llm(metadata: Dict) -> list[str]:
    """
    Convert the input metadata (dictionary) into JMESPath expressions for filtering.

    Args:
        metadata (Dict): The metadata to be converted.

    Returns:
        list[str]: The list of JMESPath expressions that can be used for filtering.
    """

    log_message(metadata)
    result = metadata_converter.invoke({"metadata": json.dumps(metadata)})
    log_message("---FORMATTED METADATA: " + str(result))

    return result  # type: ignore


# def company_to_parent(metadata: dict) -> dict:
#     parent = extract_parent.invoke({"metadata": metadata})
#     metadata["company_name"] = parent.content
#     return metadata

def convert_metadata_to_jmespath(metadata: dict[str, str | list[str]], metadata_filters: list[str] = None) -> str:
    jmespath_parts = []


    # if metadata_filters is None:
    #     metadata_filters = metadata.keys()

    for key, value in metadata.items():
        if key not in metadata_filters:
            continue  

        if value is None :
            continue

        if isinstance(value, list): 
            if key == "company_name": # Not being used currently : company_name is a string 
                for item in value:
                    item = item.lower()
                    if item.endswith(" inc.") or item.endswith(" inc"):
                        item = item[:-4]  # Remove "inc." or "inc"
                    jmespath_parts.append(f"contains({key}, `{item.lower()}`)")

            elif key == "topics": # Being used for topics
                if value:
                    topic_conditions = []
                    for topic in value:
                        topic_conditions.append(f"topics == `{topic}`")
                    jmespath_parts.append(f"({' || '.join(topic_conditions)})")

            else:
                for item in value:
                    if item is None or item.lower() == "none" or item.lower() == "unknown":
                        continue
                    jmespath_parts.append(f"contains({key}, `{item}`)")

        # Handling non-list values (company_name, year, etc.)
        else: # Being used for company_name , year 
            if value == None or value.lower() == "none" or value.lower() == "unknown":
                continue
            if key == "company_name":
                if value.endswith("inc.") or value.endswith("inc"):
                    value = value[:-4]  # Remove "inc." or "inc"
            jmespath_parts.append(f"{key} == `{value}`")

    return " && ".join(jmespath_parts)


# Input 
# metadata = {
#     "company_name": "Tesla Inc",
#     "year": "2023",
#     "topics": ["revenue", "profits", "growth"]
# }

# Output string format 
#  "company_name == `tesla`) && contains(company_name, `motors`) && year == `2023` && (contains(topics, `revenue`) || contains(topics, `profits`) || contains(topics, `growth`))"

