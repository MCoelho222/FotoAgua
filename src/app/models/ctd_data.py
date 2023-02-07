def create_collection_ctd(mongo_client):
    # ctd_validator = {
    #     "$jsonSchema": {
    #         "bsonType": "object",
    #         "required": ["date", "temperature", "depth"],
    #         "properties": {
    #             "_id": {
    #                 "bsonType": "objectId",
    #                 "description": "From mongoDB"
    #             },
    #             "date": {
    #                 ""
    #             }
    #         }
    #     }
    # }
    try:
        mongo_client.create_collection("CTD_data")
    except Exception as e:
        print(e)

    mongo_client.command("collMod", "CTD_data")
