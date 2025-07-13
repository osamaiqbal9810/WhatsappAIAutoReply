import sys
import os
from gtts import gTTS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def text_to_speech(text: str, output_filename: str) -> str:
    try:
        tts = gTTS(text=text, lang='en')
        tts.save(output_filename)
        logger.info(f"Successfully converted text to speech and saved to {output_filename}")
        return output_filename
    except Exception as e:
        logger.error(f"Error converting text to speech: {e}")
        return "[Text-to-speech failed]"

if __name__ == "__main__":
    if len(sys.argv) > 2:
        text_to_convert = sys.argv[1]
        output_file = sys.argv[2]
        result = text_to_speech(text_to_convert, output_file)
        print(result)
    else:
        logger.error("Usage: python p5_textToSpeech_audio.py \"<text_to_convert>\" <output_filename>")
        sys.exit(1)