import time
import random

class GreetingManager:
    def __init__(self):
        # Track when we last saw/greeted someone
        # Store: {name: timestamp}
        self.last_greeted = {}
        
        # Configuration
        self.LONG_ABSENCE_THRESHOLD = 1800  # 30 minutes (Full greeting)
        self.SHORT_COOLDOWN = 60            # 1 minute (No greeting at all to avoid spam)
        # Between 1 min and 1 hour -> Short/Casual greeting
        
        self.nicknames = {
            "Vaishnavi": "vaaish",
            "Pooja": "Mam",
            "Sukumaran": "sir",
            "Deva Nandan": "Deva",
            "Rakesh N K": "Rakesh Sir",
        }
        
        # VIP / Special Introductions
        self.special_intros = {
            "Rakesh N K": "Hello Rakesh Sir! It is an honor to welcome a Reporter from Maliyaala Manorama to our school.",
            "S Prateesh": "Welcome Prateesh Sir. Great to have a reporter from Mathrubhumi Daily here.",
            "Ansar Varnana": "Hello Ansar Sir. Welcome. We are glad to see a reporter from Madhyamam.",
            "Abhilash D": "Welcome Abhilash Sir from Kala Kaumudi. Nice to meet you.",
            "Saju P M": "Hello Saju Sir. Welcome to our school. We appreciate the visit from Janmabhumi Daily.",
            "Honey": "Hello Honey Sir. Welcome. It is great to have Asianet News represented here.",
            "Ansari A": "Welcome Ansari Sir. We are honored to have a reporter from Chandrika here.",
            "Babu Rajeev P R": "Hello Babu Rajeev Sir. Welcome to our school. Great to have Mathrubhumi News here.",
            "Saji Nair": "Welcome Saji Sir. We are pleased to have Kerala Kaumudi Daily's Varkala correspondent visiting us."
        }
        
    def should_greet(self, name):
        """Check IF we should greet this person at all."""
        if name == "Unknown":
            # Rate limit unknown greetings to once every 30 seconds
            last = self.last_greeted.get("Unknown", 0)
            return (time.time() - last) > 30

        last = self.last_greeted.get(name, 0)
        # Don't greet if we just saw them less than SHORT_COOLDOWN ago
        return (time.time() - last) > self.SHORT_COOLDOWN

    def get_greeting(self, name):
        """Get the appropriate greeting text based on time since last meeting."""
        if not self.should_greet(name):
            return None
            
        now = time.time()
        last = self.last_greeted.get(name, 0)
        self.last_greeted[name] = now  # Update timestamp
        
        # Scenario 1: New person or Long time no see (Standard Formal Greeting)
        if last == 0 or (now - last) > self.LONG_ABSENCE_THRESHOLD:
            # Check for VIP intro first
            if name in self.special_intros:
                return self.special_intros[name]
            return f"Hello {name}! Welcome to MGM Model School."

        # Scenario 2: Casual re-encounter (Short greeting)
        # Condition: Seen relatively recently (between 1 min and 1 hour)
        return self._get_casual_greeting(name)

    def _get_casual_greeting(self, name):
        """Generate a varied casual greeting."""
        # Priority 1: Explicit nickname
        if name in self.nicknames:
            short_name = self.nicknames[name]
        # Priority 2: First part of a multi-word name (e.g. "Deva Nandan" -> "Deva")
        elif " " in name:
            short_name = name.split()[0]
        # Priority 3: Full name
        else:
            short_name = name
        
        options = [
            f"Hi again {short_name}!",
            f"Welcome back {short_name}.",
            f"Good to see you {short_name}.",
            f"How is it going {short_name}?",
            f"Hello there {short_name}!"
            
        ]
        return random.choice(options)

    def get_unknown_greeting(self):
        """Greeting for unknown people."""
        now = time.time()
        self.last_greeted["Unknown"] = now
        return "Hello! Welcome to M G M Model School."
