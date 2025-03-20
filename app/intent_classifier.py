
from app.llm_agent import FOLLOW_UP_QUESTIONS

# Store previous intent per user
if "user_intent_history" not in globals():
    user_intent_history = {}

# Store chat history per user
if "user_chat_history" not in globals():
    user_chat_history = {}

# Keywords that indicate a troubleshooting issue
TROUBLESHOOTING_KEYWORDS = [
    "slow", "disconnect", "not working", "buffering", "reboot", 
    "no signal", "low speed", "unstable", "intermittent", "down"
]

# Keywords for installation & product guide requests
INSTALLATION_KEYWORDS = [
    "install", "setup", "configuration", "installation", "how to set up", 
    "user guide", "manual", "instructions", "setup steps"
]

# Keywords for general router/WiFi inquiries (NOT an issue)
GENERAL_WIFI_KEYWORDS = [
    "StarHub", "SingTel", "router models", "specifications", "coverage", 
    "compare routers", "best routers", "WiFi plans", "ISP"
]

# Keywords for billing and account-related inquiries
BILLING_KEYWORDS = [
    "bill", "billing", "payment", "invoice", "refund", 
    "charges", "subscription", "credit", "overcharge", "discount", "plan upgrade"
]

class IntentClassifier:
    def classify(self, query, user_name):
        """Classifies the intent as troubleshooting, installation/user guide, or general inquiry."""
        query_lower = query.lower()

        # 1️⃣ **Step 1: Check if this is a follow-up question (Keep the current intent)**
        if user_name in user_intent_history:
            if query_lower in {"what's next", "continue", "next step", "go on"}:
                return user_intent_history[user_name]  # Keep the same intent

            # Stay in troubleshooting mode until all follow-up questions are answered
            if user_name in user_chat_history and user_chat_history[user_name][-1].get("follow_up_count", 0) < len(FOLLOW_UP_QUESTIONS):
                return "technical"  # Ensure troubleshooting continues
            if user_name in user_chat_history and user_chat_history[user_name][-1].get("follow_up_count", 0) > len(FOLLOW_UP_QUESTIONS):
                return "installation"  # Ensure troubleshooting continues

            # If all follow-ups are answered, reset intent for new questions
            del user_intent_history[user_name]  # Allow a new intent to be detected


        # 2️⃣ **Step 2: Detect keywords to classify the issue type (PRIORITY)**
        if any(keyword in query_lower for keyword in INSTALLATION_KEYWORDS):
            user_intent_history[user_name] = "installation"
            return "installation"

        if any(keyword in query_lower for keyword in TROUBLESHOOTING_KEYWORDS):
            user_intent_history[user_name] = "technical"
            return "technical"

        if any(keyword in query_lower for keyword in GENERAL_WIFI_KEYWORDS):
            user_intent_history[user_name] = "general"
            return "general"
        
        if any(keyword in query_lower for keyword in BILLING_KEYWORDS):
            user_intent_history[user_name] = "billing"
            return "billing"

        # 3️⃣ **Step 3: If no specific keyword is found, reset to general**
        user_intent_history[user_name] = "general"
        return "general"
