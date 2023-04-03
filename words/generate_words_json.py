import json

INPUT_PATH = "words.txt"
OUTPUT_PATH = "words.json"

DELIMITER = "\n"

with open(INPUT_PATH) as in_file:
    raw_file_out = in_file.read()

words = raw_file_out.split(DELIMITER)
words.sort()

with open(OUTPUT_PATH, "w") as out_file:
    json.dump(words, out_file)
