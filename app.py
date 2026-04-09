import os

def load_docs(folder="docs"):
    docs = []
    for file in os.listdir(folder):
        path = os.path.join(folder, file)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                docs.append(f.read())
    return "\n".join(docs)

docs_text = load_docs()

questions = [
    "Where is the auth token generated?",
    "Which endpoint returns all users?",
    "How do I connect to the database?"
]

for q in questions:
    print("\nQuestion:", q)
    print("Answer (from docs):")
    print(docs_text)