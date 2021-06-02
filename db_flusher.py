import pymongo


def main():
    print("Attempting to flush database")
    client = pymongo.MongoClient("mongodb+srv://ccbot:hugegainz@cluster0.4y4dc.mongodb.net/ccbot?retryWrites=true&w=majority", tls=True, tlsAllowInvalidCertificates=True)
    db = client.indicators_db
    coll = db.indicators_coll
    coll.drop()
    print("Database flush complete")


if __name__ == '__main__':
    main()
