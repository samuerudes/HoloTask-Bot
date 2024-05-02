import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials
from google.cloud.firestore_v1.base_query import FieldFilter

cred = credentials.Certificate('holotask-888e5-firebase-adminsdk-gdej4-4134ae64e7.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

users_ref = db.collection('Users')

userDiscordName = "sanouh"

query = users_ref.where(filter=FieldFilter("userDiscord", "==", userDiscordName))

documents = query.stream()

for doc in documents:
    print(doc.id)

usertasks_ref = db.collection('UserTasks')

query2 = usertasks_ref.where(filter=FieldFilter("userId", "==", doc.id))

documents2 = query2.stream()


print(f"Tasks for user {doc.id}")
print(f"---------")

for doc2 in documents2:
    usertask_data = doc2.to_dict()
    print(f"Task Name: {usertask_data['taskName']}")
    print(f"Task Description: {usertask_data['taskDescription']}")
    print(f"Task Status: {usertask_data['taskStatus']}")
    print(f"Task End Date & Time: {usertask_data['endDateTime']}")
    print("---")


