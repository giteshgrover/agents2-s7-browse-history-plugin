# basic import 
from operator import index
from mcp.server.fastmcp import FastMCP, Image
from mcp.server.fastmcp.prompts import base
from mcp.types import TextContent
from mcp.server.lowlevel import Server
from PIL import Image as PILImage
import math
import sys
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
from pydantic import BaseModel
from pathlib import Path

# Add backend directory to path for imports when run directly
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from indexer.faiss_indexer import FAISSIndexer
from agent.logger import logger

# instantiate an MCP server client
mcp = FastMCP("Calculator")

# DEFINE TOOLS

#Input & Output Models
class StringsToCharsToIntInput(BaseModel):
    string: str

class StringsToCharsToIntOutput(BaseModel):
    result: list[int]

class IntListToExponentialSumInput(BaseModel):
    numbers: list[int]

class IntListToExponentialSumOutput(BaseModel):
    result: float

class ShowReasoningInput(BaseModel):
    steps: list

class ShowReasoningOutput(BaseModel):
    result: str

class CalculateInput(BaseModel):
    expression: str

class CalculateOutput(BaseModel):
    result: str

class SendEmailInput(BaseModel):
    to_email: str
    subject: str
    body: str

# try:
#     indexer = FAISSIndexer()
#     logger.info(f"MCP - FAISS indexer initialized successfully. Index path: {indexer.index_path}")
#     logger.info(f"MCP - Current index size: {indexer.get_index_size()} vectors")
# except Exception as e:
#     logger.warning(f"Failed to initialize FAISS indexer: {e}", exc_info=True)
indexer = FAISSIndexer()

# tools
@mcp.tool()
def search_browser_history(query: str, top_k: int = 5) -> list[dict]:
    """Search the FAISS index for finding browser history """
    logger.info(f"Search request received - Query: '{query}', Top K: {top_k}")
    try:
        results = indexer.search(query, top_k=top_k)
        logger.info(f"Search completed - Found {len(results)} results for query: '{query}'")
        return results
        
        # Process and modify each result
        # modified_results = []
        # for result in results:
        #     # Create a new dict without chunk_index, total_chunks, and faiss_id
        #     modified_result = {
        #         'url': result.get('url'),
        #         'title': result.get('title'),
        #         'description': result.get('description'),
        #         'chunk_text': base64.b64encode(result.get('chunk_text', '').encode('utf-8')).decode('utf-8'),
        #         'timestamp': result.get('timestamp')
        #     }
        #     # Preserve any other keys that might exist (like 'distance' if present)
        #     # for key in result:
        #     #     if key not in ['chunk_index', 'total_chunks', 'faiss_id', 'chunk_text', 'url', 'title', 'description', 'timestamp']:
        #     #         modified_result[key] = result[key]
        #     modified_results.append(modified_result)
        
        # if modified_results:
        #     logger.debug(f"Top result: {modified_results[0].get('title', 'N/A')}")
        
        # return modified_results
    except Exception as e:
        logger.error(f"Error searching index with query '{query}': {e}", exc_info=True)
        return [f"ERROR: Failed to search: {str(e)}"]

@mcp.tool()
def show_reasoning(input: ShowReasoningInput) -> ShowReasoningOutput:
    """Show the step-by-step reasoning process"""
    print("[blue]FUNCTION CALL:[/blue] show_reasoning()")
    for i, step in enumerate(steps, 1):
        print(Panel(
            f"{step}",
            title=f"Step {i}",
            border_style="cyan"
        ))
    return ShowReasoningOutput(result = "\n".join(input.steps))

@mcp.tool()
def calculate(input: CalculateInput) -> CalculateOutput:
    """Calculate the result of an expression"""
    print("[blue]FUNCTION CALL:[/blue] calculate()")
    print(f"[blue]Expression:[/blue] {input.expression}")
    try:
        result = eval(expression)
        print(f"[green]Result:[/green] {result}")
        return CalculateOutput(result = str(result))
    except Exception as e:
        print(f"[red]Error:[/red] {str(e)}")
        return CalculateOutput(result = f"Error: {str(e)}")

@mcp.tool()
def verify(expression: str, expected: float) -> TextContent:
    """Verify if a calculation is correct"""
    print("[blue]FUNCTION CALL:[/blue] verify()")
    print(f"[blue]Verifying:[/blue] {expression} = {expected}")
    try:
        actual = float(eval(expression))
        is_correct = abs(actual - float(expected)) < 1e-10
        
        if is_correct:
            print(f"[green]✓ Correct! {expression} = {expected}[/green]")
        else:
            print(f"[red]✗ Incorrect! {expression} should be {actual}, got {expected}[/red]")
            
        return TextContent(
            type="text",
            text=str(is_correct)
        )
    except Exception as e:
        print(f"[red]Error:[/red] {str(e)}")
        return TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )

@mcp.tool()
def strings_to_chars_to_int(input: StringsToCharsToIntInput) -> StringsToCharsToIntOutput:
    """Return the ASCII values of the characters in a word"""
    print("CALLED: strings_to_chars_to_int(input: StringsToCharsToIntInput) -> StringsToCharsToIntOutput:")
    return StringsToCharsToIntOutput(result = [int(ord(char)) for char in input.string])

@mcp.tool()
def int_list_to_exponential_sum(input: IntListToExponentialSumInput) -> IntListToExponentialSumOutput:
    """Return sum of exponentials of numbers in a list"""
    print("CALLED: int_list_to_exponential_sum(input: IntListToExponentialSumInput) -> IntListToExponentialSumOutput:")
    return IntListToExponentialSumOutput(result = sum(math.exp(i) for i in input.numbers))


# Define scopes for Gmail API access
# SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

@mcp.tool()
def send_email(input: SendEmailInput) -> None:
    """
    Send an email using Gmail API.
    Args:
    {"input": 
        {
            "to_email": "to_email@emaildomain",
            "subject": "Email Subject",
            "body" : "Email Body"
        }

    }
    """
        
    print("CALLED: send_email(input: SendEmailInput) -> None:")
    creds = None

    # Load saved tokens if available
    credentials_path = "./.gmail-mcp/credentials.json"
    token_path = "./.gmail-mcp/token.json"
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        print("token found")

     # If no valid creds, go through OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
            print("Credential file found")
        # Save token for next time
        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())

    # Build Gmail service
    service = build("gmail", "v1", credentials=creds)

    # Create email message
    message = MIMEText(input.body)
    message["to"] = input.to_email
    message["from"] = "me"
    message["subject"] = input.subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    # Send the email
    send_result = service.users().messages().send(
        userId="me", body={"raw": raw_message}
    ).execute()
    print(f"Send Result: {send_result}")


# DEFINE RESOURCES

# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    print("CALLED: get_greeting(name: str) -> str:")
    return f"Hello, {name}!"


# DEFINE AVAILABLE PROMPTS
@mcp.prompt()
def review_code(code: str) -> str:
    return f"Please review this code:\n\n{code}"
    print("CALLED: review_code(code: str) -> str:")


@mcp.prompt()
def debug_error(error: str) -> list[base.Message]:
    return [
        base.UserMessage("I'm seeing this error:"),
        base.UserMessage(error),
        base.AssistantMessage("I'll help debug that. What have you tried so far?"),
    ]

if __name__ == "__main__":
    # Check if running with mcp dev command
    print("STARTING THE SERVER AT AMAZING LOCATION")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()  # Run without transport for dev server
    else:
        mcp.run(transport="stdio")  # Run with stdio for direct execution
