# VoiceAI
This is a voice AI used by businesses to automate their process of customer services. This one is specifically designed for taking appointments for a dentist office

## Voice Dental Receptionist (ASR + TTS)

This project runs a **voice agent** that:
- Listens to your microphone (ASR)
- Sends the transcript to Gemini for structured appointment booking
- Speaks the assistant reply out loud (TTS)

### Setup (Windows)

1) **Set your API key**

In PowerShell:

```powershell
$env:GROQ_API_KEY="YOUR_API_KEY_HERE"
```

2) **Install dependencies**

```powershell
python -m pip install -U pip
pip install -r requirements.txt
```

If microphone input fails due to `PyAudio`, install it via:

```powershell
pip install pipwin
pipwin install pyaudio
```

3) **Run**

```powershell
python backend.py
```

### Controls

- Say **"stop"** (or type it) to exit.

