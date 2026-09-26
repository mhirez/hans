"""A small, reusable finite state machine (the 'state classes' pattern from the FSM lecture).

Each State keeps its own enter / update / exit / on_event logic in one class. States are
created once and shared by every enemy of a type; per-agent data lives on the owner, not in the
state. The same StateMachine runs every enemy and the game's own screens.
"""

from collections import deque


class State:
    name = "STATE"

    def enter(self, owner):
        pass

    def update(self, owner, dt: float):
        pass

    def exit(self, owner):
        pass

    def on_event(self, owner, event) -> bool:
        return False


class StateMachine:
    def __init__(self, owner, initial: State, history: int = 12):
        self.owner = owner
        self.current: State | None = None
        self.previous: State | None = None
        self.time_in_state = 0.0
        self.history: deque[str] = deque(maxlen=history)
        self.change(initial)

    @property
    def name(self) -> str:
        return self.current.name if self.current else "-"

    def change(self, new_state: State):
        if self.current is not None:
            self.current.exit(self.owner)
        self.previous, self.current = self.current, new_state
        self.time_in_state = 0.0
        self.history.append(new_state.name)
        new_state.enter(self.owner)

    def update(self, dt: float):
        self.time_in_state += dt
        self.current.update(self.owner, dt)

    def handle(self, event) -> bool:
        return self.current.on_event(self.owner, event)
