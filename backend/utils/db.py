import os
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Fetch MongoDB URI from environment variables or default to localhost
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/lms")
client = MongoClient(MONGO_URI)

# Get database instance
# Parses database name from URI if present, otherwise defaults to 'lms'
db_name = MONGO_URI.split("/")[-1].split("?")[0]
if not db_name or db_name == "localhost:27017":
    db_name = "lms"

db = client[db_name]

def parse_id(id_val):
    """
    Safely convert a string representation of ObjectId to bson.ObjectId.
    If already an ObjectId, returns it. If invalid or empty, returns None.
    """
    if not id_val:
        return None
    if isinstance(id_val, ObjectId):
        return id_val
    try:
        return ObjectId(str(id_val))
    except Exception:
        return None

def to_json(doc):
    """
    Recursively converts BSON documents with ObjectIds and datetimes
    to JSON-serializable dictionaries.
    """
    if doc is None:
        return None
    
    if isinstance(doc, list):
        return [to_json(x) for x in doc]
        
    if isinstance(doc, dict):
        new_doc = {}
        for k, v in doc.items():
            if k == "_id" and isinstance(v, ObjectId):
                new_doc["id"] = str(v)
            elif isinstance(v, ObjectId):
                new_doc[k] = str(v)
            elif isinstance(v, datetime):
                new_doc[k] = v.isoformat()
            elif isinstance(v, dict) or isinstance(v, list):
                new_doc[k] = to_json(v)
            else:
                new_doc[k] = v
        return new_doc
        
    return doc

def to_json_list(cursor):
    """
    Converts a MongoDB cursor or list of documents into serializable JSON list.
    """
    return [to_json(doc) for doc in cursor]
