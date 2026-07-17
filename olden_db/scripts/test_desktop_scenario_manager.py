import ast, inspect
from olden_db.desktop import scenario_controller
from olden_db.desktop.scenario_controller import ScenarioController

def main():
    source=inspect.getsource(scenario_controller);tree=ast.parse(source)
    forbidden=[]
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or ""]
            forbidden.extend(n for n in names if n=="json" or n.startswith("hashlib"))
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in {"open","uuid4"}:
            forbidden.append(node.func.id)
    assert not forbidden,forbidden
    required={"new","open","save","save_as","rename","duplicate","delete","import_document","export","can_close"}
    assert required.issubset(set(dir(ScenarioController)))
    assert "expected_token=" in source
    assert "export_scenario_document(" in source
    print("Desktop scenario-manager architecture validation completed successfully.")
if __name__=="__main__":main()
