import sys

model_ids_file = sys.argv[1]

model_ids = []
with open(model_ids_file, "r") as f:
    for l in f:
        l = l.rstrip()
        if l.startswith("eos"):
            model_ids += [l]

for model_id in model_ids:
    print(model_id)
