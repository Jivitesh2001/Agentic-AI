import os
import json
import subprocess
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# ─── Tool Definitions (what the LLM sees) ───
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Perform mathematical calculations. Use for any math.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression, e.g. '2 + 3 * 4'"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_scrape",
            "description": "Fetch and extract text content from a URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to scrape"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Execute Python code and return the output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_reader",
            "description": "Read and return the contents of a local file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read (absolute or relative)"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_writer",
            "description": "Write or append content to a local file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to write (absolute or relative)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    },
                    "mode": {
                        "type": "string",
                        "description": "Write mode: 'write' to overwrite or 'append' to add to end. Default is 'write'.",
                        "enum": ["write", "append"]
                    }
                },
                "required": ["file_path", "content"]
            }
        }
    },
]

# ─── Tool Implementations (what actually runs) ───
def calculator(expression: str) -> str:
    try:
        result = eval(expression)  # Use safer eval in production
        return json.dumps({"result": result})
    except Exception as e:
        return json.dumps({"error": str(e)})

def web_scrape(url: str) -> str:
    resp = requests.get(url, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(separator="\n", strip=True)[:2000]
    return json.dumps({"content": text})

def run_python(code: str) -> str:
    try:
        result = subprocess.run(
            f'conda activate aai && python -c "{code}"',
            capture_output=True, text=True, timeout=30, shell=True
        )
        return json.dumps({
            "stdout": result.stdout[:1000],
            "stderr": result.stderr[:500]
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

def file_reader(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Limit content to avoid overwhelming the LLM context
        if len(content) > 5000:
            return json.dumps({
                "content": content[:5000],
                "truncated": True,
                "total_length": len(content),
                "message": "Content truncated to 5000 characters"
            })
        return json.dumps({"content": content, "truncated": False})
    except FileNotFoundError:
        return json.dumps({"error": f"File not found: {file_path}"})
    except PermissionError:
        return json.dumps({"error": f"Permission denied: {file_path}"})
    except UnicodeDecodeError:
        return json.dumps({"error": "File is not a text file or has encoding issues"})
    except Exception as e:
        return json.dumps({"error": str(e)})

def file_writer(file_path: str, content: str, mode: str = "write") -> str:
    try:
        write_mode = 'a' if mode == "append" else 'w'
        with open(file_path, write_mode, encoding='utf-8') as f:
            f.write(content)

        file_size = os.path.getsize(file_path)
        return json.dumps({
            "success": True,
            "message": f"Successfully {'appended to' if mode == 'append' else 'wrote'} {file_path}",
            "bytes_written": len(content.encode('utf-8')),
            "file_size": file_size
        })
    except PermissionError:
        return json.dumps({"error": f"Permission denied: {file_path}"})
    except IsADirectoryError:
        return json.dumps({"error": f"Path is a directory, not a file: {file_path}"})
    except Exception as e:
        return json.dumps({"error": str(e)})

TOOL_MAP = {
    "calculator": calculator,
    "web_scrape": web_scrape,
    "run_python": run_python,
    "file_reader": file_reader,
    "file_writer": file_writer,
}

from openai import OpenAI

client = OpenAI(
    base_url=f"http://{os.getenv('VLLM_HOST')}:{os.getenv('VLLM_PORT')}/v1",
    api_key=os.getenv("VLLM_API_KEY"),
)

def agent_loop(user_query: str, max_iterations: int = 5):
    messages = [
        {"role": "system", "content": (
            "You are a helpful agent with access to tools. "
            "Use tools when needed to answer questions accurately. "
            "Always explain your reasoning before calling a tool."
            "Do not output thinking steps or internal reasoning."
        )},
        {"role": "user", "content": user_query},
    ]
    
    for i in range(max_iterations):
        response = client.chat.completions.create(
            model=os.getenv("VLLM_MODEL"),
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",  # LLM decides whether to use a tool
        )
        
        msg = response.choices[0].message
        messages.append(msg)
        
        # If no tool calls, we have our final answer
        if not msg.tool_calls:
            print(f"\n✅ Final Answer: {msg.content}")
            return msg.content
        
        # Execute each tool call
        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            
            print(f"🔧 Calling {fn_name}({fn_args})")
            result = TOOL_MAP[fn_name](**fn_args)
            print(f"   → Result: {result[:200]}")
            
            # Feed result back to LLM
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })
    
    return "Max iterations reached."

# Test it!
# agent_loop("What is 47 * 89 + 12?")
# agent_loop("Write 'Hello World' to a file called test.txt in my current directory")
# agent_loop("Scrape the title of https://arxiv.org and tell me about it and save the content to a file called arxiv.txt")
# agent_loop("What's in the file .env in my current directory?")
# agent_loop("Read the Epstein article on Wikipedia and summarize it, if you cannot do it use the local file Epstein.txt in my current directory")
agent_loop("Write a Python script that prints the first 15 Fibonacci numbers, save it to fib.py, then execute it and save the output to fib_output.txt and do create the file if it does not exist and save it in the current directory")
# agent_loop("Run this Python code: import os; print(os.getcwd())")
