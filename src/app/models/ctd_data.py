def create_collection_ctd(mongo_client):
    ctd_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["date", "data"],
            "properties": {
                "_id": {
                    "bsonType": "objectId",
                    "description": "From mongoDB"
                },
                "date": {
                    "bsonType": "string",
                    "description": "date in the csv file"
                },
                "data": {
                    "bsonType": "object",
                    "description": "values in the csv file"
                }
            }
        }
    }
    try:
        mongo_client.create_collection("ctd_data")
    except Exception as e:
        print(e)

    mongo_client.command("collMod", "ctd_data", validator=ctd_validator)