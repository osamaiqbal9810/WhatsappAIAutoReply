import sys
import os
import speech_recognition as sr
from pydub import AudioSegment
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def transcribe_audio(file_path: str) -> str:
    recognizer = sr.Recognizer()
    wav_path = None
    try:
        logger.info(f"Attempting to transcribe audio file: {file_path}")

        # Convert to WAV if not already WAV
        if not file_path.lower().endswith(".wav"):
            audio = AudioSegment.from_file(file_path)
            wav_path = file_path + ".wav"
            audio.export(wav_path, format="wav")
            logger.info(f"Converted {file_path} to {wav_path}")
        else:
            wav_path = file_path

        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            logger.info(f"Successfully transcribed: {text}")
            return text
    except sr.UnknownValueError:
        logger.warning(f"Google Speech Recognition could not understand audio in {file_path}")
        return "[Transcription failed: Unintelligible audio]"
    except sr.RequestError as e:
        logger.error(f"Could not request results from Google Speech Recognition service for {file_path}; {e}")
        return f"[Transcription failed: API request error: {e}]"
    except Exception as e:
        logger.error(f"Error transcribing audio file {file_path}: {e}")
        return f"[Error transcribing audio: {e}]"
    finally:
        if wav_path and wav_path != file_path and os.path.exists(wav_path):
            os.remove(wav_path)
            logger.info(f"Cleaned up temporary WAV file: {wav_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        audio_file_path = sys.argv[1]
        transcribed_text = transcribe_audio(audio_file_path)
        print(transcribed_text)
    else:
        logger.error("Usage: python p4_transcribe_audio.py <audio_file_path>")
        sys.exit(1)
