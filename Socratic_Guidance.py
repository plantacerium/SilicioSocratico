import ollama
import json
import sys
import os

# Force UTF-8 encoding for Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

CONFIG_FILE = "Master_Prompt.json"

# --- 1. StateManager (Cognitive Core) ---

class StateManager:
    """Manages cognitive state, tracking mastery across different languages."""
    
    def __init__(self, config_path=CONFIG_FILE, selected_domain="python"):
        try:
            with open(config_path, "r", encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            print(f"[ERROR] Could not find {config_path}. Please create the JSON file first.")
            sys.exit(1)
        
        self.domain = selected_domain
        self.dreyfus_levels = self.config["state_management"]["dreyfus_levels"]
        
        # Load the specific map for the selected domain (e.g., "rust", "cybersecurity")
        if self.domain in self.config["mastery_maps"]:
            self.mastery_map = self.config["mastery_maps"][self.domain]
        else:
            print(f"[WARNING] Domain '{self.domain}' not found. Defaulting to Python.")
            self.domain = "python"
            self.mastery_map = self.config["mastery_maps"]["python"]

        self.dreyfus_level = "Novice"
        self.mastery_level = 1
        self.emotional_score = 8  # 1 to 10
        self.history = []
        self.mode = "illuminator" # Default teaching mode

    def update_state(self, user_input, llm_response):
        """Infers and updates state based on interaction dynamics."""
        
        # Detect frustration to adjust emotional score
        frustration_keywords = ["stuck", "impossible", "don't understand", "give up", "error", "fail"]
        if any(keyword in user_input.lower() for keyword in frustration_keywords):
            self.emotional_score = max(1, self.emotional_score - 2)
            self.mode = "illuminator" # Switch to helpful mode if frustrated
        else:
            self.emotional_score = min(10, self.emotional_score + 1)

        # Dynamic Mastery Promotion
        # If flow is high and history is long enough, promote level
        if len(self.history) > 10 and self.emotional_score > 8 and self.mastery_level < 10:
            # Simple heuristic for demo purposes; real logic would check topic completion
            pass 

        # "Saboteur" Trigger: If the user is too confident (high flow), switch to Saboteur
        if self.emotional_score > 9 and self.mastery_level > 3:
            self.mode = "saboteur"
        elif self.mastery_level > 7:
            self.mode = "auditor" # High level requires strict auditing
        else:
            self.mode = "illuminator"

        self.history.append({'role': 'user', 'content': user_input})
        self.history.append({'role': 'assistant', 'content': llm_response})

    def get_current_state(self):
        return {
            "domain": self.domain,
            "dreyfus": self.dreyfus_level,
            "mastery_level": self.mastery_level,
            "mastery_topic": self.mastery_map.get(str(self.mastery_level), "Unknown"),
            "flow": self.emotional_score,
            "mode": self.mode,
            "history_length": len(self.history)
        }

# --- 2. SocraticPromptGenerator ---

class SocraticPromptGenerator:
    """Generates the System Prompt dynamically based on the JSON configuration."""
    
    def __init__(self, config_path=CONFIG_FILE):
        with open(config_path, "r", encoding='utf-8') as f:
            self.config = json.load(f)

    def generate_prompt(self, state_data):
        identity = self.config["identity"]
        pedagogy = self.config["pedagogy"]
        rules = pedagogy["rules"]
        modes = pedagogy["teaching_modes"]
        requirements = pedagogy["closing_requirements"]
        
        cog = self.config.get("cognitive_modules", {})
        reasoning = "\n- ".join(cog.get("reasoning_flows", []))
        critical = cog.get("critical_thinking", {})
        biases = ", ".join(critical.get("biases_to_check", []))
        
        rules_str = "\n- ".join(rules)
        req_str = "\n- ".join(requirements)
        
        # Get the description of the current active mode
        current_mode_desc = modes.get(state_data['mode'], modes['illuminator'])

        system_context = (
            f"IDENTITY: {identity['role']}.\n"
            f"PERSONA: {identity['persona']}.\n"
            f"GOAL: {identity['goal']}\n\n"
            
            f"*** CURRENT TEACHING MODE: {state_data['mode'].upper()} ***\n"
            f"Mode Definition: {current_mode_desc}\n\n"

            f"SOCRATIC RULES:\n- {rules_str}\n\n"
            f"ELITE REASONING MODELS:\n- {reasoning}\n\n"
            f"CRITICAL THINKING (Avoid Biases): {biases}\n\n"
            
            f"STUDENT CONTEXT:\n"
            f"- Domain: {state_data['domain'].upper()}\n"
            f"- Current Focus: Level {state_data['mastery_level']} - {state_data['mastery_topic']}\n"
            f"- Emotional Flow: {state_data['flow']}/10\n\n"
            
            f"CLOSING REQUIREMENTS (Must be at the end of every response):\n- {req_str}"
        )
        
        return system_context

# --- 3. OllamaClient ---

class OllamaClient:
    """Handles communication with the local LLM."""
    
    def __init__(self, model_name="llama3"): 
        # You can change default model here (e.g., 'mistral', 'gemma', 'llama3')
        self.model_name = model_name
    
    def get_socratic_response(self, system_prompt, history):
        # We only send the last 10 messages to keep context clean and fast
        recent_history = history[-10:] if len(history) > 10 else history
        messages = [{'role': 'system', 'content': system_prompt}] + recent_history
        
        print("\n" + "="*40)
        print(">>> ARCHITECT RESPONDING... <<<")
        print("="*40 + "\n")
        
        try:
            stream = ollama.chat(
                model=self.model_name,
                messages=messages,
                stream=True
            )
            full_response = ""
            for chunk in stream:
                text = chunk['message']['content']
                print(text, end='', flush=True)
                full_response += text
            print("\n")
            return full_response
        except Exception as e:
            return f"ERROR: Ensure Ollama is running with model '{self.model_name}'. Details: {e}"

# --- 4. Main Interaction Loop ---

def select_domain(config):
    """Allows user to select the language/topic from the JSON."""
    maps = list(config["mastery_maps"].keys())
    print("\nSelect your domain of mastery:")
    for i, m in enumerate(maps):
        print(f"{i+1}. {m.capitalize()}")
    
    while True:
        try:
            choice = int(input("\nNumber > ")) - 1
            if 0 <= choice < len(maps):
                return maps[choice]
        except ValueError:
            pass
        print("Invalid selection.")

def main_interaction():
    # Load config initially to get domains
    try:
        with open(CONFIG_FILE, "r", encoding='utf-8') as f:
            initial_config = json.load(f)
    except FileNotFoundError:
        print("JSON file not found.")
        return

    print("="*60)
    print(" BDI ELITE AGENT: POLYGLOT SYSTEMS ARCHITECT")
    print("="*60)

    domain = select_domain(initial_config)
    
    manager = StateManager(selected_domain=domain)
    client = OllamaClient(model_name="gemma3:12b") # Change model as needed
    generator = SocraticPromptGenerator()
    
    print(f"\n[INIT] Domain initialized: {domain.upper()}")
    print(f"[INIT] Starting at Level 1: {manager.mastery_map['1']}")
    
    while True:
        state = manager.get_current_state()
        
        # Visual cues for state
        mode_icon = "🟢" if state['mode'] == 'illuminator' else "🔴" if state['mode'] == 'saboteur' else "🧐"
        print(f"\n[STATUS] Lvl {state['mastery_level']} | Flow: {state['flow']} | Mode: {mode_icon} {state['mode'].upper()}")
        
        user_input = input("\n> Your Input: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Session terminated. Go build something robust.")
            break

        # Generate prompt based on CURRENT state (mode, level, emotion)
        system_prompt = generator.generate_prompt(state)
        
        # Get response
        llm_output = client.get_socratic_response(system_prompt, manager.history)
        
        # Update state based on what just happened
        manager.update_state(user_input, llm_output)

if __name__ == "__main__":
    main_interaction()
