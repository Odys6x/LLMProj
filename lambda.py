import json
import boto3
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
bedrock_client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")
s3_client = boto3.client("s3")

# S3 bucket and chat log folder
S3_BUCKET_NAME = "chatloginfo"
CHAT_LOG_FOLDER = "chat_history/"

def load_chat_from_s3(user_id):
    """
    Loads chat history from S3.
    """
    s3_key = f"{CHAT_LOG_FOLDER}{user_id}.json"

    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        chat_history = json.loads(response['Body'].read().decode('utf-8'))
        return chat_history
    except s3_client.exceptions.NoSuchKey:
        return []  # Return empty list if no chat history exists
    except Exception as e:
        logger.error(f"🚨 Error loading chat from S3: {str(e)}")
        return []

def save_chat_to_s3(user_id, chat_data):
    """
    Saves chat history to S3.
    """
    s3_key = f"{CHAT_LOG_FOLDER}{user_id}.json"

    try:
        # Retrieve existing chat history if available
        chat_history = load_chat_from_s3(user_id)
        chat_history.append(chat_data)

        # Save updated chat history back to S3
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=json.dumps(chat_history, indent=4),
            ContentType="application/json"
        )

        logger.info(f"✅ Chat history saved to {s3_key}")

    except Exception as e:
        logger.error(f"🚨 Error saving chat to S3: {str(e)}")

def lambda_handler(event, context):
    try:
        # Parse input event
        body = json.loads(event.get("body", "{}"))
        user_prompt = body.get("prompt", "").strip()
        user_id = "annonymous" # Default user ID

        if not user_prompt:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No input provided"}),
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                }
            }

        # Load existing chat history from S3
        chat_history = load_chat_from_s3(user_id)

        # Prepare Bedrock Flow input (sending entire chat history)
        flow_input = {
            "history": chat_history,
            "new_input": user_prompt
        }

        # Invoke Bedrock Flow with chat history
        response = bedrock_client.invoke_flow(
            flowAliasIdentifier='GS9YAVZBOH',
            flowIdentifier='MLHN89XJ6U',
            inputs=[
                {
                    'content': {
                        'document': json.dumps(flow_input)  # Send full chat history as JSON
                    },
                    'nodeName': 'FlowInputNode',
                    'nodeOutputName': 'document'
                }
            ]
        )
        
        bot_response = ""

        if "responseStream" in response:
            for event in response["responseStream"]:
                if "flowOutputEvent" in event:
                    output_content = event["flowOutputEvent"].get("content", {})
                    bot_response = output_content.get("document", "")

                if "flowCompletionEvent" in event:
                    completion_reason = event["flowCompletionEvent"].get("completionReason", "")
                    if completion_reason != "SUCCESS":
                        logger.error(f"Flow failed with reason: {completion_reason}")
                        bot_response = "Flow execution failed."

        if not bot_response:
            bot_response = "No response received from Bedrock Flow."

        logger.info(f"🤖 Bedrock Flow Response: {bot_response}")

        # Prepare chat data for storage
        chat_data = {
            "user_prompt": user_prompt,
            "bot_response": bot_response
        }

        # Save updated chat history back to S3
        save_chat_to_s3(user_id, chat_data)

        return {
            "statusCode": 200,
            "body": json.dumps({"response": bot_response}),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        }

    except Exception as e:
        logger.error(f"🚨 General Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"An error occurred: {str(e)}"}),
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        }
