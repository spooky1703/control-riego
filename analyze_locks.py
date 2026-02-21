import ast
import os
import collections

# Map of func_name -> set of functions it calls
calls_map = collections.defaultdict(set)
# Set of functions that open a riegos connection
opens_conn = set()
# Set of functions that open a cuotas connection
opens_cuotas = set()

parsed_files = {}

for fname in ['modules/models.py', 'modules/cuotas.py', 'modules/logic.py', 'modules/reports.py', 'modules/ui_components.py']:
    with open(fname, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())
        parsed_files[fname] = tree

for fname, tree in parsed_files.items():
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_name = node.name
            
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        called_func = child.func.id
                        calls_map[func_name].add(called_func)
                        
                        if called_func == 'get_connection':
                            opens_conn.add(func_name)
                        elif called_func == 'get_cuotas_connection':
                            opens_cuotas.add(func_name)

# Now find nested: A calls B. A opens conn, B opens conn.
print("=== NESTED CONNECTIONS (RIEGOS DB) ===")
for f in opens_conn:
    if f in calls_map:
        for called in calls_map[f]:
            if called in opens_conn:
                print(f"Deadlock Risk: {f} -> {called}")

print("\n=== NESTED CONNECTIONS (CUOTAS DB) ===")
for f in opens_cuotas:
    if f in calls_map:
        for called in calls_map[f]:
            if called in opens_cuotas:
                print(f"Deadlock Risk: {f} -> {called}")

print("\n=== CROSS-DB NESTED (RIEGOS -> CUOTAS) ===")
for f in opens_conn:
    if f in calls_map:
        for called in calls_map[f]:
            if called in opens_cuotas:
                print(f"{f} -> {called}")

print("\n=== CROSS-DB NESTED (CUOTAS -> RIEGOS) ===")
for f in opens_cuotas:
    if f in calls_map:
        for called in calls_map[f]:
            if called in opens_conn:
                print(f"{f} -> {called}")

