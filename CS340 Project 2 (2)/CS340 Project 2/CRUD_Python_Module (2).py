# Example Python Code to Insert a Document 

from pymongo import MongoClient 
from bson.objectid import ObjectId 

class AnimalShelter(object): 
    """ CRUD operations for Animal collection in MongoDB """ 

    def __init__(self, USER, PASS, HOST="127.0.0.1", PORT=27017,DB="aac", COL="animals"): 
        # Initializing the MongoClient. This helps to access the MongoDB 
        # databases and collections. This is hard-wired to use the aac 
        # database, the animals collection, and the aac user. 
        # 
        # You must edit the password below for your environment. 
        # 
        # Connection Variables 
        # 
        uri = f"mongodb://{USER}:{PASS}@{HOST}:{int(PORT)}/{DB}"
        # 
        # Initialize Connection 
        # 
        self.client=MongoClinet(uri)
        self.client = MongoClient('mongodb://%s:%s@%s:%d' % (USER,PASS,HOST,PORT)) 
        self.database = self.client['%s' % (DB)] 
        self.collection = self.database['%s' % (COL)] 

    # Create a method to return the next available record number for use in the create method
    def nextRecord(self):
        lastDoc = self.collection.find_one(sort = [("rec_num", -1)])
        if lastDoc and "rec_num" in lastDoc:
            return lastDoc ["rec_num"] + 1
        else:
            return 1
        
    # Complete this create method to implement the C in CRUD. 
    def create(self, data):
        if data is not None:  
            # data should be dictionary
            if "rec_num" not in data:
                data["rec_num"] = self.nextRecord()
            result = self.collection.insert_one(data)
            if result.acknowledged:
                print("Inseration Successful, Document added.")
                return True 
            else:
                print("Inseration Failed, Document has not been added.")
                return False
        else: 
            raise Exception("Nothing to save, because data parameter is empty") 
            
    # Read method to implement the R in CRUD.
    def read(self, data): 
        result = self.database.animals.find(data)
        if result:
            print("Documents found")
            return list(self.collection.find(data))
        else: 
            raise Exception("Documents not found or data parameter is empty")
            return False
        
    #Update method to implement the U in CRUD.
    def update(self, data, newData):
        result = self.database.animals.update_many(data, {"$set" : newData})
        if result:
            print( result.modified_count, "Documents found and updated.")
            return result
        else:
            raise Exception("Document not found or data paramenter is empty")
        
    #Delete method to implement the D in CRUD
    def delete(self, data):
        result = self.database.animals.delete_many(data)
        if result:
            print(result.deleted_count, "Documents deleted")
        else:
            raise Exception("Documents not found or data parameter is empty")