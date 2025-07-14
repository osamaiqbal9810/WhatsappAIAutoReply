from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
from sentence_transformers import SentenceTransformer
import json
import uuid
import re

def chunk_answer(text, max_len=1000, min_len=200):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) <= max_len:
            current += sentence + " "
        else:
            if len(current.strip()) >= min_len:
                chunks.append(current.strip())
            current = sentence + " "

    if current.strip():
        chunks.append(current.strip())

    return chunks


# --- Milvus Config ---
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
COLLECTION_NAME = "whatsapp_data"
VECTOR_DIM = 384

# --- Load Q&A Pairs ---
with open("../qa_pairs_complete.json", "r", encoding="utf-8") as f:
    qa_pairs = json.load(f)

# --- Step 1: Connect to Milvus ---
connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)

# --- Step 2: Define Schema ---
if utility.has_collection(COLLECTION_NAME):
    print(f"Collection '{COLLECTION_NAME}' already exists. Dropping and recreating...")
    Collection(COLLECTION_NAME).drop()

schema = CollectionSchema(
    fields=[
        FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=36),
        FieldSchema(name="question", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="chunk", dtype=DataType.VARCHAR, max_length=4096),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIM),
        FieldSchema(name="queryType", dtype=DataType.VARCHAR, max_length=256)
    ],
    description="WhatsApp QA chunks embedded by content"
)

collection = Collection(name=COLLECTION_NAME, schema=schema)

# --- Step 3: Sentence Transformer ---
model = SentenceTransformer("all-MiniLM-L6-v2")

ids = []
questions = []
chunks = []
embeddings = []

# --- Step 4: Process Each QA Pair ---
for pair in qa_pairs:
    question = pair["question"]
    answer = pair["answer"]

    # Embed the question ONCE
    question_embedding = model.encode(question).tolist()

    # Chunk the answer
    answer_chunks = chunk_answer(answer)

    # For each chunk, associate the question and question_embedding
    for chunk in answer_chunks:
        ids.append(str(uuid.uuid4()))
        questions.append(question)
        chunks.append(chunk)
        embeddings.append(question_embedding)

# --- Step 5: Insert into Milvus ---
query_types = ["support"] * len(ids)
entities = [ids, questions, chunks, embeddings, query_types]
collection.insert(entities)
collection.flush()

# --- Step 6: Create Index ---
collection.create_index(
    field_name="embedding",
    index_params={
        "index_type": "IVF_FLAT",
        "metric_type": "L2",
        "params": {"nlist": 1024}
    }
)

collection.load()
print(f"✅ Inserted {len(ids)} embedded chunks into Milvus collection '{COLLECTION_NAME}'.")
