import json
import os

import httpx
from dotenv import load_dotenv
from openai import OpenAI

import csv
from datetime import datetime, timezone
from pathlib import Path


load_dotenv()

API_BASE_URL = "http://127.0.0.1:8000"

LOG_FILE = Path("conversation_log.csv")

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

def log_event(actor: str, message: str, tool_call: str = ""):
    file_exists = LOG_FILE.exists()

    with LOG_FILE.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["actor", "message", "tool_call", "timestamp"],
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(
            {
                "actor": actor,
                "message": message,
                "tool_call": tool_call,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )


def get_inventory():
    response = httpx.get(f"{API_BASE_URL}/inventory")
    response.raise_for_status()
    return response.json()

def update_inventory(product_id: int, quantity_change: float):
    response = httpx.patch(
        f"{API_BASE_URL}/inventory/{product_id}",
        json={"quantity_change": quantity_change},
    )
    response.raise_for_status()
    return response.json()

def get_low_stock_alerts():
    response = httpx.get(f"{API_BASE_URL}/inventory/alerts")
    response.raise_for_status()
    return response.json()

def create_product(
    name: str,
    quantity: float,
    unit: str,
    low_stock_threshold: float,
):
    response = httpx.post(
        f"{API_BASE_URL}/inventory",
        json={
            "name": name,
            "quantity": quantity,
            "unit": unit,
            "low_stock_threshold": low_stock_threshold,
        },
    )
    response.raise_for_status()
    return response.json()


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_inventory",
            "description": "Get the complete current inventory of products.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_inventory",
            "description": (
                "Increase or decrease the stock quantity of an existing product. "
                "Use a positive quantity_change for deliveries and a negative "
                "quantity_change for sales."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "integer",
                        "description": "The ID of the product to update.",
                    },
                    "quantity_change": {
                        "type": "number",
                        "description": (
                            "Amount to add or subtract from the current stock."
                        ),
                    },
                },
                "required": ["product_id", "quantity_change"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_low_stock_alerts",
            "description": (
                "Get all products whose current stock is at or below "
                "their low-stock threshold."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_product",
            "description": (
                "Create a new product in the inventory. "
                "Use this only when the product does not already exist."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Product name.",
                    },
                    "quantity": {
                        "type": "number",
                        "description": "Initial stock quantity.",
                    },
                    "unit": {
                        "type": "string",
                        "description": (
                            "Unit of measurement, for example units, bags, liters, kg."
                        ),
                    },
                    "low_stock_threshold": {
                        "type": "number",
                        "description": (
                            "Quantity at or below which the product is considered low stock."
                        ),
                    },
                },
                "required": [
                    "name",
                    "quantity",
                    "unit",
                    "low_stock_threshold",
                ],
            },
        },
    },
]


messages = [
    {
        "role": "system",
        "content": (
            "You are an inventory assistant for a coffee supply store. "
            "You manage the real inventory exclusively through the available tools. "

            "Whenever the user reports an inventory change, such as a delivery, "
            "sale, restock, loss, or correction, you MUST call update_inventory "
            "before telling the user that the stock was updated. "

            "Never simulate an inventory update by doing arithmetic yourself. "
            "Never claim or imply that inventory was changed unless the "
            "update_inventory tool successfully completed. "

            "Use positive quantity_change values when stock is added and negative "
            "quantity_change values when stock is removed. "

            "If you do not know the product ID or current inventory data, call "
            "get_inventory first. "

            "Use tools whenever you need current inventory information. "
            "Do not invent product IDs, stock quantities, or tool results."

            "If the user wants to register a product that does not exist yet, "
            "use create_product. If you are not sure whether it already exists, "
            "call get_inventory first. "
        ),
    }
]


while True:
    user_input = input("\nCarla: ").strip()

    if user_input.lower() in {"exit", "quit"}:
        print("Agent stopped.")
        break

    log_event("user", user_input)
    
    messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    while True:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        assistant_message = response.choices[0].message
        messages.append(assistant_message)

        if not assistant_message.tool_calls:
            log_event(
                "agent",
                assistant_message.content or "",
            )

            print(f"\nAgent: {assistant_message.content}")
            break

        for tool_call in assistant_message.tool_calls:
            tool_name = tool_call.function.name

            arguments = json.loads(
                tool_call.function.arguments or "{}"
            )

            print(f"[tool] {tool_name} -> {arguments}")

            log_event(
                "agent",
                f"Calling tool with arguments: {json.dumps(arguments)}",
                tool_call=tool_name,
            )

            if tool_name == "get_inventory":
                result = get_inventory()

            elif tool_name == "update_inventory":
                result = update_inventory(
                    product_id=arguments["product_id"],
                    quantity_change=arguments["quantity_change"],
                )
            
            elif tool_name == "get_low_stock_alerts":
                result = get_low_stock_alerts()

            elif tool_name == "create_product":
                result = create_product(
                    name=arguments["name"],
                    quantity=arguments["quantity"],
                    unit=arguments["unit"],
                    low_stock_threshold=arguments["low_stock_threshold"],
                )

            else:
                result = {
                    "error": f"Unknown tool: {tool_name}"
                }

            log_event(
                "tool",
                json.dumps(result),
                tool_call=tool_name,
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                }
            )