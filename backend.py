import json
import time
import re
from typing import Any, Dict, Optional
from groq import Groq

# ==============================
# Groq Client
# ==============================
client = Groq(api_key="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") #this will expire in 7 days starting from 22/01/2026

# ==============================
# Rule-Based Extraction (Primary)
# ==============================
def extract_phone(text: str) -> Optional[str]:
    """Extract phone number using regex"""
    # Match various phone formats
    patterns = [
        r'\b(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b',  # 123-456-7890 or 1234567890
        r'\b(\d{10})\b',  # 1234567890
        r'\b(\d{3}[-.\s]?\d{4})\b',  # 123-4567
        r'\b(\d{6,})\b'  # Any 6+ digit number
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).replace('-', '').replace('.', '').replace(' ', '')
    return None

def extract_date(text: str) -> Optional[str]:
    """Extract date from text"""
    text_lower = text.lower()
    
    # Match patterns like "3rd of March", "March 3rd", "3/15", "March 15"
    date_patterns = [
        r'\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?))\b',
        r'\b((?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?)\b',
        r'\b(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b',
        r'\b(tomorrow|today|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text_lower)
        if match:
            return match.group(1)
    
    return None

def extract_time(text: str) -> Optional[str]:
    """Extract time from text"""
    text_lower = text.lower()
    
    # Match patterns like "3pm", "3:00 pm", "15:00", "3 o'clock"
    time_patterns = [
        r'\b(\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.))\b',
        r'\b(\d{1,2}\s*(?:am|pm|a\.m\.|p\.m\.))\b',
        r'\b(\d{1,2}:\d{2})\b',
        r'\b(\d{1,2}\s*o\'?clock)\b'
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, text_lower)
        if match:
            return match.group(1)
    
    return None

def extract_name(text: str, user_input: str) -> Optional[str]:
    """Extract name from phrases like 'my name is X' or 'I am X'"""
    text_lower = text.lower()
    
    # Patterns for name extraction
    patterns = [
        r'(?:my name is|i am|this is|name is)\s+([a-zA-Z\s]+?)(?:\.|,|$|\sand\s)',
        r'(?:call me|it\'s)\s+([a-zA-Z\s]+?)(?:\.|,|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            name = match.group(1).strip()
            # Filter out common false positives
            if name and len(name) > 1 and name not in ['calling', 'looking', 'trying', 'going']:
                return name.title()
    
    return None

def extract_reason(text: str) -> Optional[str]:
    """Extract reason/symptoms from text"""
    text_lower = text.lower()
    
    # Common dental/medical reasons
    symptoms = [
        'toothache', 'tooth ache', 'pain', 'cavity', 'cavities', 'cleaning', 'checkup', 
        'check up', 'extraction', 'filling', 'crown', 'root canal', 'gums', 'bleeding',
        'headache', 'fever', 'cough', 'cold', 'flu', 'sore throat', 'earache'
    ]
    
    for symptom in symptoms:
        if symptom in text_lower:
            return symptom
    
    # Phrases like "I have a X" or "reason is X"
    patterns = [
        r'(?:i have|experiencing|suffering from|because of|reason is)\s+(?:a\s+)?([a-zA-Z\s]+?)(?:\.|,|$|and)',
        r'(?:for|regarding)\s+(?:a\s+)?([a-zA-Z\s]+?)(?:\.|,|$|and)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            reason = match.group(1).strip()
            if reason and len(reason) > 2:
                return reason
    
    return None

def smart_extract(user_text: str, current_state: Dict) -> Dict:
    """
    Use rule-based extraction FIRST, then LLM as fallback
    Returns extracted fields
    """
    extracted = {
        "name": None,
        "phone": None,
        "reason": None,
        "date": None,
        "time": None
    }
    
    user_lower = user_text.lower()
    
    # Rule-based extraction
    if not current_state["phone"]:
        extracted["phone"] = extract_phone(user_text)
    
    if not current_state["date"]:
        date = extract_date(user_text)
        # Make sure we're not confusing time with date
        if date and 'pm' not in date.lower() and 'am' not in date.lower() and ':' not in date:
            extracted["date"] = date
    
    if not current_state["time"]:
        time_val = extract_time(user_text)
        if time_val:
            extracted["time"] = time_val
    
    if not current_state["name"]:
        extracted["name"] = extract_name(user_text, user_text)
    
    if not current_state["reason"]:
        extracted["reason"] = extract_reason(user_text)
    
    print(f"RULE-BASED EXTRACTION: {extracted}")
    
    # If we didn't extract anything with rules, try LLM as fallback
    if all(v is None for v in extracted.values()):
        print("No rule-based extraction, trying LLM...")
        llm_extracted = llm_extract(user_text, current_state)
        # Only use LLM results for fields we're currently missing
        for key in extracted.keys():
            if not current_state[key] and llm_extracted.get(key):
                extracted[key] = llm_extracted[key]
    
    return extracted

def llm_extract(user_text: str, current_state: Dict) -> Dict:
    """Fallback LLM-based extraction"""
    prompt = f"""Extract appointment information from: "{user_text}"

Return ONLY valid JSON:
{{
  "name": "extracted name or null",
  "phone": "extracted phone or null",
  "reason": "extracted reason or null",
  "date": "extracted date (NOT time) or null",
  "time": "extracted time (NOT date) or null"
}}

CRITICAL RULES:
- Date examples: "March 3rd", "3/15", "tomorrow"
- Time examples: "3pm", "3:00 pm", "15:00"
- Do NOT put time in date field
- Do NOT put date in time field
- Only extract what user JUST said
- Return null for fields not mentioned"""

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You extract appointment data. Respond ONLY with JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=150
        )
        
        raw = completion.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()
        
        parsed = json.loads(raw)
        
        # Clean nulls
        for k in ["name", "phone", "reason", "date", "time"]:
            val = parsed.get(k)
            if val is None or val == "null" or (isinstance(val, str) and val.lower() == "null") or val == "":
                parsed[k] = None
        
        return parsed
    except:
        return {"name": None, "phone": None, "reason": None, "date": None, "time": None}

# ==============================
# State Management
# ==============================
def update_state(current_state: Dict, extracted: Dict) -> Dict:
    """Update state with extracted values"""
    new_state = current_state.copy()
    
    for key in ["name", "phone", "reason", "date", "time"]:
        new_value = extracted.get(key)
        
        # Only update if we have a valid new value AND field is currently empty
        if new_value and not current_state[key]:
            print(f"  ✓ {key}: '{current_state[key]}' → '{new_value}'")
            new_state[key] = new_value
        elif new_value and current_state[key]:
            # Field already filled, but check if this is better info
            print(f"  ⚠ {key}: already set to '{current_state[key]}', ignoring '{new_value}'")
    
    return new_state

def is_complete(state: Dict) -> bool:
    return all(v is not None and str(v).strip() != "" for v in state.values())

def next_missing_field(state: Dict) -> Optional[str]:
    if not state["name"]:
        return "name"
    if not state["phone"]:
        return "phone"
    if not state["reason"]:
        return "reason"
    if not state["date"]:
        return "date"
    if not state["time"]:
        return "time"
    return None

def generate_question(state: Dict) -> str:
    """Generate clear question for next missing field"""
    missing = next_missing_field(state)
    
    questions = {
        "name": "What's your full name?",
        "phone": "What's your phone number?",
        "reason": "What's the reason for your visit?",
        "date": "What date would you like? For example, March 15th or tomorrow.",
        "time": "What time works for you?"
    }
    
    return questions.get(missing, "Great! Let me confirm your appointment.")

# ==============================
# Response Generation
# ==============================
def generate_response(user_text: str, state: Dict, extracted: Dict) -> str:
    """Generate natural response"""
    
    # What did we just collect?
    just_collected = [k for k, v in extracted.items() if v is not None]
    
    if not just_collected:
        # Didn't understand
        return f"I didn't quite catch that. {generate_question(state)}"
    
    # Brief acknowledgment
    ack = "Got it."
    if "name" in just_collected:
        ack = f"Thank you, {state['name']}."
    elif "phone" in just_collected:
        ack = "Perfect."
    elif "reason" in just_collected:
        ack = "Understood."
    elif "date" in just_collected:
        ack = "Sounds good."
    elif "time" in just_collected:
        ack = "Great."
    
    # Check if we're done
    if is_complete(state):
        return f"{ack} Your appointment is all set!"
    
    # Ask for next field
    next_question = generate_question(state)
    return f"{ack} {next_question}"

# ==============================
# Main Turn Handler
# ==============================
def handle_user_turn(user_text: str, current_state: Dict) -> Dict:
    print(f"\n{'='*60}")
    print(f"USER: {user_text}")
    print(f"STATE: {current_state}")
    
    # Extract information using rules + LLM
    extracted = smart_extract(user_text, current_state)
    
    # Update state
    new_state = update_state(current_state, extracted)
    
    # Generate response
    response = generate_response(user_text, new_state, extracted)
    
    complete = is_complete(new_state)
    
    print(f"NEW STATE: {new_state}")
    print(f"COMPLETE: {complete}")
    print(f"RESPONSE: {response}")
    print(f"{'='*60}\n")
    
    return {
        "assistant_reply": response,
        "state": new_state,
        "is_complete": complete
    }

# ==============================
# TTS - FIXED FOR WINDOWS
# ==============================
def init_tts():
    """This is now just a test function - we reinit on each speak"""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.stop()
        del engine
        print("✓ TTS available")
        return True
    except Exception as e:
        print(f"✗ TTS failed: {e}")
        return False

def speak(tts_available, text):
    """Reinitialize engine each time to avoid Windows pyttsx3 bug"""
    if not text or text.strip() == "":
        return
    
    print(f"\n🔊 SPEAKING: {text}")
    
    if not tts_available:
        print("(TTS not available)")
        return
    
    try:
        import pyttsx3
        # Create fresh engine each time
        engine = pyttsx3.init()
        rate = engine.getProperty('rate')
        engine.setProperty('rate', rate - 30)
        engine.setProperty('volume', 1.0)
        
        engine.say(text)
        engine.runAndWait()
        
        # Clean up
        engine.stop()
        del engine
        
        print("✓ Speech completed")
    except Exception as e:
        print(f"✗ TTS error: {e}")
        import traceback
        traceback.print_exc()

# ==============================
# ASR
# ==============================
def init_asr():
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        r.energy_threshold = 4000
        r.dynamic_energy_threshold = True
        mic = sr.Microphone()
        print("✓ Speech recognition initialized")
        return r, mic
    except Exception as e:
        print(f"✗ ASR failed: {e}")
        return None, None

def listen_once(r, mic):
    import speech_recognition as sr
    print("\n🎤 Listening...")
    
    with mic as source:
        try:
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=10, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            print("(timeout)")
            return None
    
    try:
        text = r.recognize_google(audio)
        print(f"✓ Heard: {text}")
        return text.strip()
    except sr.UnknownValueError:
        print("(couldn't understand)")
        return None
    except Exception as e:
        print(f"(error: {e})")
        return None

# ==============================
# Main Loop
# ==============================
def run_voice_agent():
    state = {
        "name": None,
        "phone": None,
        "reason": None,
        "date": None,
        "time": None
    }
    
    print("\nInitializing...")
    tts_available = init_tts()  # Returns True/False instead of engine
    recognizer, mic = init_asr()
    
    greeting = "Hello! What's your name?"
    print(f"\nAssistant: {greeting}")
    speak(tts_available, greeting)
    
    while True:
        # Get input
        if recognizer and mic:
            user_text = listen_once(recognizer, mic)
            if not user_text:
                continue
        else:
            user_text = input("\nYou: ").strip()
        
        if user_text.lower() in {"stop", "exit", "quit", "cancel"}:
            farewell = "Goodbye!"
            speak(tts_available, farewell)
            break
        
        # Process
        result = handle_user_turn(user_text, state)
        state = result["state"]
        
        # Speak response
        speak(tts_available, result["assistant_reply"])
        
        # Check completion
        if result.get("is_complete", False):
            print("\n" + "="*60)
            print("✓ APPOINTMENT BOOKED!")
            print("="*60)
            print(f"Name:   {state['name']}")
            print(f"Phone:  {state['phone']}")
            print(f"Reason: {state['reason']}")
            print(f"Date:   {state['date']}")
            print(f"Time:   {state['time']}")
            print("="*60)
            
            confirmation = f"Perfect! Your appointment is booked for {state['date']} at {state['time']}. We'll see you then!"
            speak(tts_available, confirmation)
            break
        
        time.sleep(0.3)

# ==============================
# Entry Point
# ==============================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("VOICE AI APPOINTMENT BOOKING")
    print("="*60)
    
    try:
        run_voice_agent()
    except KeyboardInterrupt:
        print("\n\nInterrupted")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()