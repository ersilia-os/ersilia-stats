import sys
from pyairtable import Api

model_ids_file = sys.argv[1]
airtable_api_key = sys.argv[2]
output_file = sys.argv[3]

BASE_ID = "appgxpCzCDNyGjWc8"
TABLE_ID = "tblZGe2a2XeBxrEHP"

model_ids = []
with open(model_ids_file, "r") as f:
    for l in f:
        l = l.rstrip()
        if l.startswith("eos"):
            model_ids += [l]

def get_available_record_ids_from_airtable():
    api = Api(airtable_api_key)
    table = api.table(BASE_ID, TABLE_ID)
    records = table.all()
    data = {}
    for r in records:
        name = r["fields"]["Identifier"]
        data[name] = r["id"]
    return data

model_ids_from_airtable = get_available_record_ids_from_airtable()

nonregistered_model_repos = []
for model_id in model_ids:
    if model_id not in model_ids_from_airtable:
        if model_id == "eos0abc": continue
        nonregistered_model_repos += [model_id]

print("Non-registered model repos")
print(nonregistered_model_repos)

nonexistent_model_registries = []
for model_id in model_ids_from_airtable.keys():
    if model_id.startswith("eos0t"): continue
    if model_id == "eos0abc": continue
    if model_id not in model_ids:
        nonexistent_model_registries += [model_id]

print("Non-existent model registries")
print(nonexistent_model_registries)
