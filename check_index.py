from app.indexer import get_or_create_repo_collection

REPO = "krishnakr05/test"  # match exactly what prints in your terminal

collection = get_or_create_repo_collection(REPO)
print(f"Total indexed items: {collection.count()}")

# Pull everything back out to see what's actually stored
all_items = collection.get()
for path in all_items["ids"]:
    print(f" - {path}")

result = collection.get(ids=["utils.py"])
print("\n--- Stored content for utils.py ---")
print(result["documents"][0])