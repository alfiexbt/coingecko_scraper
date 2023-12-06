import json

# replace the output.txt name with whatever you'd like, i just set it to output
output_file_path = 'output.txt'

with open(output_file_path, 'r') as txt_file:
    token_data = json.load(txt_file)

new_tokens = []
for token in token_data:
    if "Age_Description" in token and token["Age_Description"] == "Extremely New":
        new_tokens.append(token)

for token in new_tokens:
    print(token)
