from pymongo import MongoClient

class MongoDB:
    def __init__(self, uri, db_name):
        self.uri = uri
        self.db_name = db_name
        self.client = MongoClient(self.uri)
        self.db = self.client[self.db_name]

    def connect(self):
        try:
            self.client.server_info()
            print("Connected to MongoDB")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")

    def disconnect(self):
        self.client.close()
        print("Disconnected from MongoDB")

    def write_data(self, collection_name, data):
        try:
            collection = self.db[collection_name]
            collection.insert_one(data)
        except Exception as e:
            print(f"Error writing data to MongoDB: {e}")

    def read_data(self, collection_name, query):
        try:
            collection = self.db[collection_name]
            result = collection.find(query)
            return list(result)
        except Exception as e:
            print(f"Error reading data from MongoDB: {e}")