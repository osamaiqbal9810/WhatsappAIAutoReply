from pymilvus import connections, utility, FieldSchema, CollectionSchema, Collection, DataType
import logging

logger = logging.getLogger(__name__)

class MilvusManager:
    def __init__(self, host, port, databaseName, collectionName, collectionDescription, vectorSize):
        self.host = host
        self.port = port
        self.databaseName = databaseName
        self.collectionName = collectionName
        self.collectionDescription = collectionDescription
        self.vectorSize = vectorSize
        self.collection = None
        if not self.connect_and_setup():
            raise RuntimeError("❌ Failed to connect to or set up Milvus collection.")

    def connect_and_setup(self):
        try:
            connections.connect(self.databaseName, host=self.host, port=self.port)
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")

            if not utility.has_collection(self.collectionName):
                logger.info(f"Creating collection '{self.collectionName}'...")
                self.create_collection()
                self.create_index()

            self.collection = Collection(self.collectionName)
            self.collection.load()
            return True
        except Exception as e:
            logger.error(f"Milvus setup failed: {e}")
            return False

    def create_collection(self):
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=36),
            FieldSchema(name="question", dtype=DataType.VARCHAR, max_length=1024),
            FieldSchema(name="chunk", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.vectorSize)
        ]
        schema = CollectionSchema(fields=fields, description=self.collectionDescription)
        Collection(name=self.collectionName, schema=schema)
        logger.info(f"Collection '{self.collectionName}' created.")

    def create_index(self):
        collection = Collection(self.collectionName)
        collection.create_index(
            field_name="embedding",
            index_params={
                "index_type": "IVF_FLAT",
                "metric_type": "L2",
                "params": {"nlist": 1024}
            }
        )
        logger.info(f"Index created on collection '{self.collectionName}'.")

    def check_connection(self):
        try:
            utility.get_server_version()
            return True
        except Exception as e:
            logger.error(f"Milvus connection check failed: {e}")
            return False

    def insert_data(self, ids, questions, chunk, embeddings):
        if not self.collection:
            self.collection = Collection(self.collectionName)
            self.collection.load()

        try:
            assert len(ids) == len(questions) == len(chunk) == len(embeddings)
            self.collection.insert([ids, questions, chunk, embeddings])
            self.collection.flush()
            logger.info(f"Inserted {len(ids)} records into '{self.collectionName}'")
            return True
        except Exception as e:
            logger.error(f"Insert failed: {e}")
            return False

    def search(self, query_vector, top_k=5):
        if not self.collection:
            self.collection = Collection(self.collectionName)
            self.collection.load()

        try:
            results = self.collection.search(
                data=[query_vector],
                anns_field="embedding",
                param={"metric_type": "L2", "params": {"nprobe": 10}},
                limit=top_k,
                output_fields=["question", "chunk"]
            )
            logger.info(f"Search complete. Top {top_k} results returned.")
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
