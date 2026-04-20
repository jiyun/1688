import tkinter as tk
from dataclasses import dataclass, field
from typing import Optional, Callable, List, Any


@dataclass
class MenuItem:
    label: str
    command: Optional[Callable] = None
    state: str = "normal"
    submenu: Optional[List['MenuItem']] = None
    variable: Optional[Any] = None
    image: Optional[Any] = None
    compound: str = "none"


SEPARATOR = MenuItem(label="__SEPARATOR__")


class ContextMenuManager:
    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self._current_menu: Optional[tk.Menu] = None

    def show(self, event: tk.Event, items: List[MenuItem],
             title: Optional[str] = None, menu_kwargs: Optional[dict] = None):
        self._destroy_current()
        self._current_menu = self._build(items, title, menu_kwargs)
        try:
            self._current_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._current_menu.grab_release()

    def show_at(self, x: int, y: int, items: List[MenuItem],
                title: Optional[str] = None, menu_kwargs: Optional[dict] = None):
        self._destroy_current()
        self._current_menu = self._build(items, title, menu_kwargs)
        try:
            self._current_menu.tk_popup(x, y)
        finally:
            self._current_menu.grab_release()

    def _build(self, items: List[MenuItem], title: Optional[str],
               menu_kwargs: Optional[dict] = None) -> tk.Menu:
        kwargs = {"tearoff": 0}
        if menu_kwargs:
            kwargs.update(menu_kwargs)
        menu = tk.Menu(self.parent, **kwargs)

        if title:
            menu.add_command(label=title, state="disabled")
            menu.add_separator()

        for item in items:
            self._add_item(menu, item, menu_kwargs)

        return menu

    def _add_item(self, menu: tk.Menu, item: MenuItem, menu_kwargs: Optional[dict] = None):
        if item.label == "__SEPARATOR__":
            menu.add_separator()
            return

        if item.submenu is not None:
            kwargs = {"tearoff": 0}
            if menu_kwargs:
                kwargs.update(menu_kwargs)
            sub = tk.Menu(menu, **kwargs)
            for sub_item in item.submenu:
                self._add_item(sub, sub_item, menu_kwargs)
            menu.add_cascade(label=item.label, menu=sub, state=item.state)
            return

        if item.variable is not None:
            menu.add_checkbutton(label=item.label, variable=item.variable, state=item.state)
            return

        cmd_kwargs = {"label": item.label, "command": item.command, "state": item.state}
        if item.image is not None:
            cmd_kwargs["image"] = item.image
            cmd_kwargs["compound"] = item.compound
        menu.add_command(**cmd_kwargs)

    def _destroy_current(self):
        if self._current_menu:
            try:
                self._current_menu.destroy()
            except tk.TclError:
                pass
            self._current_menu = None


def build_column_menu_items(all_columns: dict, visible_columns: list,
                            toggle_callback: Callable) -> List[MenuItem]:
    items = [MenuItem(label="显示/隐藏列", state="disabled"), SEPARATOR]
    for col_name, cfg in all_columns.items():
        is_visible = col_name in visible_columns
        label = f"{'✓ ' if is_visible else '   '}{cfg['text']}"
        items.append(MenuItem(label=label, command=lambda c=col_name: toggle_callback(c)))
    return items
