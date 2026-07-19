from app.indexer import index_repo_files, get_or_create_repo_collection
from app.retriever import get_similar_reference_files

TEST_REPO = "test/fake-repo"

# Fake reference files — deliberately one cluster of similar files,
# one clear outlier
files = [
    {
        "path": "src/routes/users.py",
        "content": "from fastapi import APIRouter\nrouter = APIRouter()\n\n@router.get('/users')\ndef get_users():\n    try:\n        return db.fetch_users()\n    except Exception as e:\n        raise HTTPException(500, str(e))",
        "extension": "py",
    },
    {
        "path": "src/routes/orders.py",
        "content": "from fastapi import APIRouter\nrouter = APIRouter()\n\n@router.get('/orders')\ndef get_orders():\n    try:\n        return db.fetch_orders()\n    except Exception as e:\n        raise HTTPException(500, str(e))",
        "extension": "py",
    },
    {
        "path": "src/utils/math_helpers.py",
        "content": "def add(a, b):\n    return a + b\n\ndef multiply(a, b):\n    return a * b\n\ndef square(x):\n    return x * x",
        "extension": "py",
    },
]

index_repo_files(TEST_REPO, files)

collection = get_or_create_repo_collection(TEST_REPO)
print(f"Indexed count: {collection.count()}")   # expect 3

# Simulate a PR diff that adds another route handler
fake_diff = "+@router.get('/products')\n+def get_products():\n+    try:\n+        return db.fetch_products()\n+    except Exception as e:\n+        raise HTTPException(500, str(e))"

results = get_similar_reference_files(TEST_REPO, fake_diff, top_k=3)

for r in results:
    print(f"{r['path']}  (distance: {r['similarity_distance']:.4f})")