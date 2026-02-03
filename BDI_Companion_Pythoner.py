import ollama
import json
import sqlite3
import time
import sys
import os

# Forzar codificación UTF-8 en Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# --- 1. Definición del StateManager (Núcleo Cognitivo) ---

class StateManager:
    """Gestiona el estado cognitivo y emocional cargando reglas desde JSON."""
    
    def __init__(self, config_path="BDI_Master_Prompt_Elite.json"):
        with open(config_path, "r", encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.dreyfus_levels = self.config["state_management"]["dreyfus_levels"]
        self.python_map = self.config["mastery_maps"]["python"]
        
        self.dreyfus_level = "Novato"
        self.mastery_level = 1
        self.emotional_score = 8 # 1 a 10
        self.history = []

    def update_state(self, user_input, llm_response):
        """Infiere y actualiza el estado basado en la interacción."""
        frustration_keywords = ["bloqueado", "imposible", "no entiendo", "rendirme"]
        if any(keyword in user_input.lower() for keyword in frustration_keywords):
            self.emotional_score = max(1, self.emotional_score - 2)
            
        # Promoción de maestría dinámica
        if len(self.history) > 15 and self.emotional_score > 7:
            if self.mastery_level < 10:
                self.mastery_level += 1
                print(f"\n[MAESTRÍA] Ascenso de nivel: {self.mastery_level}")

        self.history.append({'role': 'user', 'content': user_input})
        self.history.append({'role': 'assistant', 'content': llm_response})

    def get_current_state(self):
        return {
            "dreyfus": self.dreyfus_level,
            "mastery_level": self.mastery_level,
            "mastery_topic": self.python_map[str(self.mastery_level)],
            "flow": self.emotional_score,
            "history_length": len(self.history)
        }

# --- 2. Definición del SocraticPromptGenerator ---

class SocraticPromptGenerator:
    """Genera el System Prompt dinámicamente desde el JSON de Élite."""
    
    def __init__(self, config_path="BDI_Master_Prompt_Elite.json"):
        with open(config_path, "r", encoding='utf-8') as f:
            self.config = json.load(f)

    def generate_prompt(self, state_data, user_query, project_domain):
        identity = self.config["identity"]
        rules = self.config["pedagogy"]["rules"]
        requirements = self.config["pedagogy"]["closing_requirements"]
        
        cog = self.config.get("cognitive_modules", {})
        reasoning = "\n- ".join(cog.get("reasoning_flows", []))
        memory = "\n- ".join(cog.get("memory_techniques", []))
        critical = cog.get("critical_thinking", {})
        biases = ", ".join(critical.get("biases_to_check", []))
        
        rules_str = "\n- ".join(rules)
        req_str = "\n- ".join(requirements)
        
        system_context = (
            f"IDENTIDAD: {identity['role']}. Persona: {identity['persona']}.\n"
            f"META GLOBAL: {identity['goal']}.\n\n"
            f"REGLAS SOCRÁTICAS:\n- {rules_str}\n\n"
            f"MODELOS DE RAZONAMIENTO DE ÉLITE:\n- {reasoning}\n\n"
            f"TÉCNICAS DE MEMORIZACIÓN:\n- {memory}\n\n"
            f"PENSAMIENTO CRÍTICO (Evitar Sesgos): {biases}\n\n"
            f"CONTEXTO DEL APRENDIZ:\n- Nivel Dreyfus: {state_data['dreyfus']}\n"
            f"- Maestría Python: Nivel {state_data['mastery_level']} ({state_data['mastery_topic']})\n"
            f"- Flow Emocional: {state_data['flow']}/10\n\n"
            f"REQUISITOS DE CIERRE DE TURNO:\n- {req_str}"
        )
        
        return system_context

# --- 3. Definición del OllamaClient ---

class OllamaClient:
    """Maneja la comunicación con el modelo LLM local."""
    
    def __init__(self, model_name="gemma3:4b"):
        self.model_name = model_name
    
    def get_socratic_response(self, system_prompt, history):
        messages = [{'role': 'system', 'content': system_prompt}] + history
        
        print("\n" + "="*40)
        print(">>> RESPUESTA DEL ARQUITECTO DE ÉLITE <<<")
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
            return f"ERROR: Asegúrate de que Ollama esté corriendo con el modelo '{self.model_name}'."

# --- 4. Función de Interacción Principal ---

def main_interaction():
    manager = StateManager()
    client = OllamaClient()
    generator = SocraticPromptGenerator()
    
    print("="*60)
    print(" BDI ELITE AGENT: CONFIGURACIÓN DINÁMICA ACTIVADA ")
    print("="*60)
    
    while True:
        state = manager.get_current_state()
        print(f"\n[INFO] Nivel {state['mastery_level']}: {state['mastery_topic']}")
        
        user_input = input("\n> Tu Proceso: ")
        if user_input.lower() in ["salir", "exit"]:
            print("Cierre de sesión de Élite. ¡Sigue optimizando tu arquitectura!")
            break

        system_prompt = generator.generate_prompt(state, user_input, "General Python Mastery")
        llm_output = client.get_socratic_response(system_prompt, manager.history)
        manager.update_state(user_input, llm_output)

if __name__ == "__main__":
    main_interaction()