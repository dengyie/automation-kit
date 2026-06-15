from typing import Callable, TypeVar, Union

from automation_core.drivers import DriverSession, DriverSessionFactory


T = TypeVar("T")


class WorkflowRunner:
    def __init__(
        self,
        session_factory: Union[Callable[[], DriverSession], DriverSessionFactory],
        workflow: Callable[[DriverSession], T],
    ):
        self.session_factory = session_factory
        self.workflow = workflow

    def run(self) -> T:
        create = getattr(self.session_factory, "create", None)
        if callable(create):
            session = create()
        else:
            session = self.session_factory()
        return self.workflow(session)
