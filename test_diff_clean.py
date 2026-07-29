from app.retriever import clean_diff_for_embedding

fake_diff = """diff --git a/utils.py b/utils.py
index abc123..def456 100644
--- a/utils.py
+++ b/utils.py
@@ -1,3 +1,6 @@
 def add_numbers(a, b):
     return a + b
+
+def subtract_numbers(a, b):
+    \"\"\"Subtracts b from a and returns the result.\"\"\"
+    return a - b
"""

print(clean_diff_for_embedding(fake_diff))