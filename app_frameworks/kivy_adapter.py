from __future__ import annotations

from typing import Dict, List

from app.adapters.framework import FrameworkAdapter
from app.domain.models import MediaLink


class KivyAdapter(FrameworkAdapter):
    def name(self) -> str:
        return "kivy"

    def build_home_screen_model(self, links: List[MediaLink]) -> Dict:
        return {
            "framework": self.name(),
            "screen": "home",
            "header": "LinkSaver",
            "items": [
                {
                    "title": link.title,
                    "url": link.url,
                    "tags": link.tags,
                    "is_local": link.is_local,
                    "description": link.description,
                }
                for link in links
            ],
        }

    def launch(self) -> str:
        return (
            "Kivy adapter ready. "
            "Set RUN_KIVY_UI=1 and run `python -m app.main` to launch the basic Kivy UI."
        )

    def run_ui(self, links: List[MediaLink]) -> None:
        try:
            from kivy.app import App
            from kivy.uix.boxlayout import BoxLayout
            from kivy.uix.label import Label
            from kivy.uix.scrollview import ScrollView
            from kivy.uix.gridlayout import GridLayout
        except Exception as exc:
            raise RuntimeError(
                "Kivy is not installed or failed to import. Install it first, then retry."
            ) from exc

        items = list(links)

        class LinkSaverApp(App):
            def build(self):
                root = BoxLayout(orientation="vertical", padding=12, spacing=12)
                root.add_widget(
                    Label(
                        text="LinkSaver",
                        size_hint_y=None,
                        height=48,
                    )
                )

                scroll = ScrollView()
                grid = GridLayout(cols=1, spacing=8, size_hint_y=None)
                grid.bind(minimum_height=grid.setter("height"))

                for link in items:
                    text = (
                        f"[b]{link.title}[/b]\n"
                        f"{link.url}\n"
                        f"Tags: {', '.join(link.tags) if link.tags else '-'}\n"
                        f"Local: {'yes' if link.is_local else 'no'}"
                    )
                    grid.add_widget(
                        Label(
                            text=text,
                            markup=True,
                            halign="left",
                            valign="middle",
                            size_hint_y=None,
                            height=110,
                            text_size=(800, None),
                        )
                    )

                scroll.add_widget(grid)
                root.add_widget(scroll)
                return root

        LinkSaverApp().run()


def create_adapter() -> KivyAdapter:
    return KivyAdapter()