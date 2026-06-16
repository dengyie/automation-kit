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


@dataclass(frozen=True)
class ActionBatchResult:
    results: List[ActionResult]
    skipped: List[ActionRequest] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return bool(self.results) and all(result.success for result in self.results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "results": [asdict(result) for result in self.results],
            "skipped": [action.to_dict() for action in self.skipped],
            "success": self.success,
        }


class ActionExecutor:
    def __init__(self, session: DriverSession):
        self.session = session

    def run(self, action: ActionRequest) -> ActionResult:
        try:
            return self.session.execute_action(action.name, **action.parameters)
        except Exception as exc:
            return ActionResult(False, f"{action.name} failed: {exc}")

    def run_batch(self, batch: ActionBatch) -> ActionBatchResult:
        results = []
        skipped = []
        for index, action in enumerate(batch.actions):
            result = self.run(action)
            results.append(result)
            if action.stop_on_failure and not result.success:
                skipped = batch.actions[index + 1 :]
                break
        return ActionBatchResult(results=results, skipped=skipped)
