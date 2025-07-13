import os
import json
import fitz  # PyMuPDF
from pydub import AudioSegment
import speech_recognition as sr
import re
import logging
import pytesseract
from PIL import Image
import re
# --- Logging Setup ---
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "microservices", "logs", "chat_parser.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
# --- End Logging Setup ---

BASE_PATH = r"E:/EyraTechProjects/Mirchawala Data"
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "processed_chats.json")

def read_text_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as file:
            content = file.read()

            # Clean up any repeated or malformed timestamps first
            content = re.sub(r'(-\d+\s*\n*)+', '-', content)  # Remove "-2\n7/..." patterns

            # Add a real newline before each WhatsApp message
            content = re.sub(r'(?<!\n)\n(?!\d{1,2}/\d{1,2}/\d{2,4})', ' ', content)
            # Strip leading/trailing spaces and return
            return content.strip()

    except FileNotFoundError:
        logging.error(f"Text file not found: {path}")
        return ""
    except Exception as e:
        logging.error(f"Error reading text file {path}: {e}")
        return ""



def transcribe_audio(file_path):
    recognizer = sr.Recognizer()
    wav_path = file_path + ".wav"
    try:
        logging.info(f"Transcribing audio file: {file_path}")
        audio = AudioSegment.from_file(file_path)
        audio.export(wav_path, format="wav")
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            logging.info(f"Transcribed Text: {text}")
            logging.info(f"Successfully transcribed {file_path}")
            return text
    except sr.UnknownValueError:
        logging.warning(f"Google Speech Recognition could not understand audio: {file_path}")
        return "[Transcription failed: Unintelligible audio]"
    except sr.RequestError as e:
        logging.error(f"Could not request results from Google Speech Recognition service for {file_path}; {e}")
        return f"[Transcription failed: API request error]"
    except Exception as e:
        logging.error(f"Error transcribing audio file {file_path}: {e}")
        return f"[Error transcribing audio: {e}]"
    finally:
        # Clean up the temporary WAV file
        if os.path.exists(wav_path):
            os.remove(wav_path)


def extract_pdf_text(pdf_path):
    logging.info(f"Extracting text from PDF: {pdf_path}")
    try:
        doc = fitz.open(pdf_path)
        text = "\n".join([page.get_text() for page in doc])
        logging.info(f"Successfully extracted text from {pdf_path}")
        return text
    except Exception as e:
        logging.error(f"Error reading PDF {pdf_path}: {e}")
        return f"[Error reading PDF: {e}]"

def insert_file_content_inline(chat_text, file_map):
    def replacer(match):
        original_line = match.group(0)
        file_name_from_chat = match.group(2).strip()
        extension = match.group(3).lower()

        # Normalize the filename from the chat by removing date-like patterns
        normalized_chat_filename = re.sub(r'-\d{8}-|--', '-', file_name_from_chat)

        logging.info(f"Attempting to match file: '{file_name_from_chat}' (Normalized: '{normalized_chat_filename}')")
        logging.info(f"Available files in file_map: {list(file_map.keys())}")

        found_content = None
        for map_key, map_value in file_map.items():
            # Normalize the key from the file map as well
            normalized_map_key = re.sub(r'-\d{8}-|--', '-', map_key.strip())
            if normalized_map_key.lower() == normalized_chat_filename.lower():
                found_content = map_value
                logging.info(f"Found match for '{file_name_from_chat}' with key '{map_key}'")
                break

        content = found_content if found_content is not None else "[File content not found]"

        if not isinstance(content, str):
            content = str(content)

        # Special handling for audio files
        if extension in ["opus", "ogg"]:
            return f"{original_line}\n[Transcription]: {content.strip()}"
        else:
            return f"{original_line}\n[File content]\n{content.strip()}\n"

    # Supported extensions for inline processing
    extensions = ["txt", "docx", "doc", "pdf", "opus", "ogg", "vcf", "jpg", "jpeg", "png"]
    ext_pattern = "|".join(extensions)

    # Regex: captures full line, filename, and extension
    pattern = re.compile(
        rf"^(.*?(\S+\.({ext_pattern}))\s*\(file attached\))$", re.MULTILINE
    )

    return re.sub(pattern, replacer, chat_text)



def sanitize_chat_text(chat_text, folderIndex):
    # Replace full name (case-insensitive)
    chat_text = re.sub(r'\bMustafa Mirchawala\b', 'Teacher', chat_text, flags=re.IGNORECASE)

    # Replace mobile numbers with "Student"
    # Handles formats like 03001234567, +923001234567, 923001234567, 3001234567
    chat_text = re.sub(r'(?<!\w)(\+?\d[\d\s\-\(\)]{7,}\d)(?!\w)', f'Student{folderIndex + 1}', chat_text)

    return chat_text

def extract_text_from_image(image_path):
    try:
        image = Image.open(image_path)
        logging.info(f"image: {image}")
        text = pytesseract.image_to_string(image, lang='eng')
        logging.info(f"OCR Text: {text}")
        return text.strip()
    except Exception as e:
        return f"[OCR failed: {e}]"


def process_folder(folder_path, folderIndex):
    logging.info(f"Processing folder: {folder_path}")
    folder_name = os.path.basename(folder_path)
    data = ""
    file_map = {}
    chat_file_path = None

    # First, find the main chat text file
    for file in os.listdir(folder_path):
        if file.lower().endswith(".txt"):
            chat_file_path = os.path.join(folder_path, file)
            logging.info(f"Found chat file: {chat_file_path}")
            data += read_text_file(chat_file_path)
            break  # Assume one chat text file per folder

    if not chat_file_path:
        logging.warning(f"No .txt chat file found in {folder_path}. Skipping.")
        return None

    # Then, process all other files and map their content
    for file in os.listdir(folder_path):
        full_path = os.path.join(folder_path, file)
        lower_file = file.lower()

        if lower_file.endswith(".txt"):
            continue  # Already processed

        elif lower_file.endswith(".pdf"):
            file_map[file] = extract_pdf_text(full_path)

        elif lower_file.endswith(".opus") or lower_file.endswith(".ogg"):
            file_map[file] = transcribe_audio(full_path)

        elif lower_file.endswith(".vcf"):
            logging.info(f"Reading VCF file as text: {full_path}")
            file_map[file] = read_text_file(full_path)
        elif lower_file.endswith((".jpg", ".jpeg", ".png")):
            logging.info(f"Disabled For Now.Extracting text from image: {full_path}")
            file_map[file] = extract_text_from_image(full_path)
        else:
            logging.info(f"Skipping unsupported file type: {file}")

    # Finally, insert the content of the processed files into the chat text
    if file_map:
        logging.info(f"Inserting content for {len(file_map)} files into the chat text for {folder_name}.")
        data = insert_file_content_inline(data, file_map)
    else:
        logging.info(f"No attached files found or processed for {folder_name}.")
    # 🔒 Sanitize chat text
    data = sanitize_chat_text(data, folderIndex)
    return data

# json.dump( all_chats_combined.strip(), out_file, ensure_ascii=False, indent=4)
def main():
    logging.info("Starting chat processing script.")
    all_chats_combined = ""
    folders = sorted([f for f in os.listdir(BASE_PATH) if os.path.isdir(os.path.join(BASE_PATH, f))])

    for index, folder in  enumerate(folders):
        folder_path = os.path.join(BASE_PATH, folder)
        try:
            folder_text = process_folder(folder_path, index)
            if folder_text:
                all_chats_combined += folder_text+"\n\n"  # optional spacing
        except Exception as e:
            logging.critical(f"A critical error occurred while processing {folder_path}: {e}", exc_info=True)

        try:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as out_file:
                out_file.write(all_chats_combined.strip())
            logging.info(f"Successfully processed all folders into one chat block.")
            print(f"\nDone! Output saved to: {OUTPUT_FILE}")
            logging.info(f"Log file saved to: {LOG_FILE}")
        except Exception as e:
            logging.error(f"Failed to write the final output to {OUTPUT_FILE}: {e}")
            print(f"\nError! Could not write output to file. See {LOG_FILE} for details.")



if __name__ == "__main__":
    main()
