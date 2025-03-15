import re

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

class IntentClassifier:
    def classify(self, query):
        """Classifies the intent as troubleshooting, installation/user guide, or general inquiry."""
        query_lower = query.lower()

        # Detect installation/user guide requests
        if any(keyword in query_lower for keyword in INSTALLATION_KEYWORDS):
            return "installation"

        # Detect troubleshooting issues
        if any(keyword in query_lower for keyword in TROUBLESHOOTING_KEYWORDS):
            return "technical"

        # Detect general queries about routers/WiFi (not troubleshooting)
        if any(keyword in query_lower for keyword in GENERAL_WIFI_KEYWORDS):
            return "general"

        return "general"  # Default to general chatbot