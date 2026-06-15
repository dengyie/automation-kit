from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from automation_core.drivers import ActionResult, DriverSession


@dataclass(frozen=True)
class ActionRequest:
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    stop_on_failure: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActionBatch:
    actions: List[ActionRequest]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actions": [action.to_dict() for action in self.actions],
        }


class ActionExecutor:
    def __init__(self, session: DriverSession):
        self.session = session

    def run(self, action: ActionRequest) -> ActionResult:
        return self.session.execute_action(action.name, **action.parameters)

    def run_batch(self, batch: ActionBatch) -> List[ActionResult]:
        results = []
        for action in batch.actions:
            result = self.run(action)
            results.append(result)
            if action.stop_on_failure and not result.success:
                break
        return results
