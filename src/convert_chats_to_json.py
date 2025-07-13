import re
import json

# === Step 1: Load the chat file ===
with open("../processed_chats.json", "r", encoding="utf-8") as f:
    lines = f.readlines()

# === Step 2: Parse raw lines into structured messages ===
messages = []
pattern = r'^(\d{2}/\d{2}/\d{4}), (\d{1,2}:\d{2}\s?[ap]m) - ([^:]+): (.+)$'
current = None

for line in lines:
    line = line.strip()
    match = re.match(pattern, line)
    if match:
        date, time, sender, text = match.groups()
        if current:
            messages.append(current)
        current = {
            "datetime": f"{date} {time}",
            "sender": sender.strip(),
            "text": text.strip()
        }
    elif current:
        # Append multiline messages
        current["text"] += " " + line.strip()

if current:
    messages.append(current)

# === Step 3: Extract Q&A pairs ===
qa_pairs = []
i = 0

while i < len(messages):
    msg = messages[i]
    sender = msg["sender"].lower()

    # Look for student questions
    if sender.startswith("student") or "?" in msg["text"]:
        question = msg["text"]
        answer_parts = []

        # Look ahead for teacher responses
        j = i + 1
        while j < len(messages) and len(answer_parts) < 5:
            next_msg = messages[j]
            next_sender = next_msg["sender"].lower()

            if next_sender == "teacher":
                answer_parts.append(next_msg["text"])
            elif next_sender.startswith("student"):
                break  # Stop if another student message appears
            j += 1

        if answer_parts:
            qa_pairs.append({
                "question": question,
                "answer": " ".join(answer_parts)
            })

    i += 1

# === Step 4: Save output to file ===
output_file = "qa_pairs_complete.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(qa_pairs, f, ensure_ascii=False, indent=2)

print(f"✅ Extracted {len(qa_pairs)} question-answer pairs to {output_file}")