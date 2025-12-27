from agent.perception import PerceptionResult
from agent.memory import MemoryItem
from typing import List, Optional
from dotenv import load_dotenv
from google import genai
import os
from agent.logger import logger

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def generate_plan(
    perception: PerceptionResult,
    memory_items: List[MemoryItem],
    tool_descriptions: Optional[str] = None
) -> str:
    """Generates a plan (tool call or final answer) using LLM based on structured perception and memory."""

    memory_texts = "\n".join(f"- {m.text}" for m in memory_items) or "None"

    tool_context = f"\nYou have access to the following tools:\n{tool_descriptions}" if tool_descriptions else ""

    specific_examples = """
    - User asks: "Search the user input 'Shopping ladies bags' to find the top 1 browsing history results of the user"
        - FUNCTION_CALL: search_browser_history|query="Shopping ladies bags"|top_k=1
        - [{"url": "https://bananarepublicfactory.gapfactory.gapfactory.com/browse/product.do?pid=832257011&rrec=true&mlink=5001%2C1%2Cshoppingbag_brcart1_rr_0&clink=1&vid=1#pdp-page-content","title": "Graphic T-Shirt | Banana Republic Factory","description": "Shop Banana Republic Factory's Graphic T-Shirt: In efforts to lower our environmental impact, we consciously crafted this T-shirt using cotton and recycled fibers made from 6 post-consumer plastic bottles., Crew neck. Short sleeves., Straight hem., Made exclusively for Banana Republic Factory., #832257","chunk_text": "cGhpYyBULVNoaXJ0CkdyYXBoaWMgVC1TaGlydApTbGltIEx1eGUgVG91Y2ggUG9sbwpQcmVtaXVtIFdhc2ggVC1TaGlydApSZWNlbnRseSBWaWV3ZWQgJiBSZWxhdGVkIEl0ZW1zClNsaW0gTHV4ZSBUb3VjaCBQb2xvCkdyYXBoaWMgVC1TaGlydApHcmFwaGljIFQtU2hpcnQKR3JhcGhpYyBULVNoaXJ0ClByZW1pdW0gV2FzaCBULVNoaXJ0ClNsaW0gTHV4ZSBUb3VjaCBQb2xvClNsaW0gTHV4ZSBUb3VjaCBQb2xvCkdyYXBoaWMgVC1TaGlydApMdXhlIFRvdWNoIFBvbG8KR3JhcGhpYyBULVNoaXJ0ClJldmlld3MKV3JpdGUgdGhlIEZpcnN0IFJldmlldwpNZW4KLwpULVNoaXJ0cwo1MCUgb2ZmIGV2ZXJ5dGhpbmcKcGx1cywgZXh0cmEgNTAlIG9mZiBzYWxlClNob3AgV29tZW4gU2hvcCBNZW4KTElNSVRFRCBUSU1FLiBFWENMVVNJT05TIEFQUExZLipERVRBSUxTClNob3AgV29tZW4gU2hvcCBNZW4KTElNSVRFRCBUSU1FLiBFWENMVVNJT05TIEFQUExZLipERVRBSUxT","timestamp": "2025-12-27T01:01:18.381Z"}]
        - FINAL_ANSWER: [{"url": "https://bananarepublicfactory.gapfactory.gapfactory.com/browse/product.do?pid=832257011&rrec=true&mlink=5001%2C1%2Cshoppingbag_brcart1_rr_0&clink=1&vid=1#pdp-page-content","title": "Graphic T-Shirt | Banana Republic Factory","description": "Shop Banana Republic Factory's Graphic T-Shirt: In efforts to lower our environmental impact, we consciously crafted this T-shirt using cotton and recycled fibers made from 6 post-consumer plastic bottles., Crew neck. Short sleeves., Straight hem., Made exclusively for Banana Republic Factory., #832257","chunk_text": "cGhpYyBULVNoaXJ0CkdyYXBoaWMgVC1TaGlydApTbGltIEx1eGUgVG91Y2ggUG9sbwpQcmVtaXVtIFdhc2ggVC1TaGlydApSZWNlbnRseSBWaWV3ZWQgJiBSZWxhdGVkIEl0ZW1zClNsaW0gTHV4ZSBUb3VjaCBQb2xvCkdyYXBoaWMgVC1TaGlydApHcmFwaGljIFQtU2hpcnQKR3JhcGhpYyBULVNoaXJ0ClByZW1pdW0gV2FzaCBULVNoaXJ0ClNsaW0gTHV4ZSBUb3VjaCBQb2xvClNsaW0gTHV4ZSBUb3VjaCBQb2xvCkdyYXBoaWMgVC1TaGlydApMdXhlIFRvdWNoIFBvbG8KR3JhcGhpYyBULVNoaXJ0ClJldmlld3MKV3JpdGUgdGhlIEZpcnN0IFJldmlldwpNZW4KLwpULVNoaXJ0cwo1MCUgb2ZmIGV2ZXJ5dGhpbmcKcGx1cywgZXh0cmEgNTAlIG9mZiBzYWxlClNob3AgV29tZW4gU2hvcCBNZW4KTElNSVRFRCBUSU1FLiBFWENMVVNJT05TIEFQUExZLipERVRBSUxTClNob3AgV29tZW4gU2hvcCBNZW4KTElNSVRFRCBUSU1FLiBFWENMVVNJT05TIEFQUExZLipERVRBSUxT","timestamp": "2025-12-27T01:01:18.381Z"}]
    """
    prompt = f"""
You are a reasoning-driven AI agent with access to tools. Your job is to solve the user's request step-by-step by reasoning through the problem, selecting a tool if needed, and continuing until the FINAL_ANSWER is produced.
{tool_context}

Always follow this loop:

1. Think step-by-step about the problem.
2. If a tool is needed, respond using the format:
   FUNCTION_CALL: tool_name|param1=value1|param2=value2
3. When the final answer is known, respond using:
   FINAL_ANSWER: [your final result]

Guidelines:
- Respond using EXACTLY ONE of the formats above per step.
- Do NOT include extra text, explanation, or formatting.
- Use nested keys (e.g., input.string) and square brackets for lists.
- You can reference these relevant memories:
{memory_texts}

Input Summary:
- User input: "{perception.user_input}"
- Intent: {perception.intent}
- Entities: {', '.join(perception.entities)}
- Tool hint: {perception.tool_hint or 'None'}

✅ Examples:
- FUNCTION_CALL: add|a=5|b=3
- FUNCTION_CALL: strings_to_chars_to_int|input.string=INDIA
- FUNCTION_CALL: int_list_to_exponential_sum|input.int_list=[73,78,68,73,65]
- FINAL_ANSWER: [42]

✅ Examples:
{specific_examples}

IMPORTANT:
- 🚫 Do NOT invent tools. Use only the tools listed below.
- 📄 If the question may relate to searching browsing history, use the 'search_browser_history' tool to look for the answer.
- 🧮 If the question is mathematical or needs calculation, use the appropriate math tool.
- 🤖 If the previous tool output already contained the result, do not search again. Instead return the same tool result as is with the same list of dict: FINAL_ANSWER: last tool result in list[dict] format
- ❌ Do NOT repeat function calls with the same parameters.
- ❌ Do NOT output unstructured responses.
- 🧠 Think before each step. Verify intermediate results mentally before proceeding.
- 💥 If unsure or no tool fits, skip to FINAL_ANSWER: [unknown]
- ✅ You have only 3 attempts. Final attempt must be FINAL_ANSWER
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        raw = response.text.strip()
        logger.debug(f"Planner/DecisionMaker - LLM output: {raw}")

        for line in raw.splitlines():
            if line.strip().startswith("FUNCTION_CALL:") or line.strip().startswith("FINAL_ANSWER:"):
                return line.strip()

        return raw.strip()

    except Exception as e:
        logger.error(f"Planner/DecisionMaker - ⚠️ Decision generation failed: {e}")
        return "FINAL_ANSWER: [unknown]"
