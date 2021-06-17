import pymongo

# Set the variables here, then run the script to an initial population of the database
USER = "malcolm"
COIN = "eth"
conditions = {"LTF": "short", "MTF": "long", "HTF": "long", "VTL": True}


def main():
    print("Populating database")
    client = pymongo.MongoClient(
        "mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority",
        tls=True,
        tlsAllowInvalidCertificates=True,
    )
    db = client.indicators_db
    coll = db.indicators_coll
    for key in conditions:
        coll.update_one(
            {"_id": USER}, {"$set": {f"{COIN}.{key}": conditions[key]}}, upsert=True
        )
    print("Database population complete")


if __name__ == "__main__":
    main()
