import firebase_admin
from firebase_admin import credentials, firestore
import grpc
from google.cloud.firestore_v1.client import firestore_client
from google.cloud.firestore_v1.client import firestore_grpc_transport
import os
from datetime import datetime
from pytz import timezone
import pytz

# Use the application default credentials
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
    'projectId': os.environ.get("GCP_PROJECT_ID"),
    'storageBucket': 'data8x-scratch.appspot.com/otter-srv-stdalone'
})

def get_timestamp():
    """
    returns the time stamp in PST Time
    """
    date_format = "%Y-%m-%d %H:%M:%S,%f"
    date = datetime.now(tz=pytz.utc)
    date = date.astimezone(timezone('US/Pacific'))
    return date.strftime(date_format)[:-3]

def write_logs(msg, trace, type, collection):
    if os.getenv("VERBOSE_LOGGING") == "true" or type == "error":
        try:
            db = firestore.client()
            # this redirects FireStore to local emulator when local testing!
            if os.getenv("ENVIRONMENT") == "otter-stdalone-docker-local-test":
                channel = grpc.insecure_channel("host.docker.internal:8080")
                transport = firestore_grpc_transport.FirestoreGrpcTransport(channel=channel)
                db._firestore_api_internal = firestore_client.FirestoreClient(transport=transport)
            data = {
                'message': msg,
                'trace': trace,
                'type': type,
                'timestamp': get_timestamp()
            }
            return db.collection(collection).add(data)
        except Exception as err:
            raise Exception(f"Error inserting {type} log into Google FireStore: {data}") from err
