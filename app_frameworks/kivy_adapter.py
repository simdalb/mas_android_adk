from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Dict, List
import webbrowser

from app.adapters.framework import FrameworkAdapter
from app.domain.models import MediaLink
from app.services.integration_config import load_integration_status
from app.services.storage import LocalMediaRepository
from app.use_cases.media_links import MediaLinkUseCases


class KivyAdapter(FrameworkAdapter):
    def name(self) -> str:
        return "kivy"

    def build_home_screen_model(self, links: List[MediaLink]) -> Dict:
        integrations = load_integration_status().summary()
        return {
            "framework": self.name(),
            "screen": "home",
            "header": "LinkSaver",
            "integration_status": integrations,
            "items": [
                {
                    "link_id": link.link_id,
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
            "Set RUN_KIVY_UI=1 and run `python -m app.main` to launch the local CRUD UI."
        )

    def run_ui(self, links: List[MediaLink]) -> None:
        try:
            from kivy.app import App
            from kivy.uix.boxlayout import BoxLayout
            from kivy.uix.button import Button
            from kivy.uix.checkbox import CheckBox
            from kivy.uix.gridlayout import GridLayout
            from kivy.uix.label import Label
            from kivy.uix.scrollview import ScrollView
            from kivy.uix.textinput import TextInput
        except Exception as exc:
            raise RuntimeError(
                "Kivy is not installed or failed to import. Install it first, then retry."
            ) from exc

        repo = LocalMediaRepository()
        use_cases = MediaLinkUseCases(repository=repo)
        integrations = load_integration_status().summary()

        class LinkSaverApp(App):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.repo = repo
                self.use_cases = use_cases
                self.current_edit_id = None
                self.search_query = ""

            def build(self):
                self.root_layout = BoxLayout(orientation="vertical", padding=12, spacing=8)

                header = Label(
                    text="LinkSaver",
                    size_hint_y=None,
                    height=40,
                )
                self.root_layout.add_widget(header)

                integration_label = Label(
                    text=(
                        "Integrations: "
                        f"Firebase={'ready' if integrations['firebase']['configured'] else 'pending'}, "
                        f"Billing={'ready' if integrations['billing']['configured'] else 'pending'}, "
                        f"AdMob={'ready' if integrations['admob']['configured'] else 'pending'}"
                    ),
                    size_hint_y=None,
                    height=30,
                )
                self.root_layout.add_widget(integration_label)

                self.status_label = Label(
                    text="Ready",
                    size_hint_y=None,
                    height=30,
                )
                self.root_layout.add_widget(self.status_label)

                self.title_input = TextInput(
                    hint_text="Title",
                    multiline=False,
                    size_hint_y=None,
                    height=38,
                )
                self.url_input = TextInput(
                    hint_text="URL or local media path",
                    multiline=False,
                    size_hint_y=None,
                    height=38,
                )
                self.tags_input = TextInput(
                    hint_text="Tags, comma-separated",
                    multiline=False,
                    size_hint_y=None,
                    height=38,
                )
                self.description_input = TextInput(
                    hint_text="Description",
                    multiline=True,
                    size_hint_y=None,
                    height=90,
                )

                local_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=34)
                local_row.add_widget(Label(text="Local file?", size_hint_x=0.7))
                self.local_checkbox = CheckBox(size_hint_x=0.3)
                local_row.add_widget(self.local_checkbox)

                self.root_layout.add_widget(self.title_input)
                self.root_layout.add_widget(self.url_input)
                self.root_layout.add_widget(self.tags_input)
                self.root_layout.add_widget(self.description_input)
                self.root_layout.add_widget(local_row)

                button_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=40, spacing=8)
                add_button = Button(text="Add / Update")
                add_button.bind(on_press=self.on_add_or_update)
                clear_button = Button(text="Clear Form")
                clear_button.bind(on_press=self.on_clear_form)

                button_row.add_widget(add_button)
                button_row.add_widget(clear_button)
                self.root_layout.add_widget(button_row)

                hint_label = Label(
                    text="Tip: duplicate title + URL combinations are blocked to keep your library tidy.",
                    size_hint_y=None,
                    height=34,
                )
                self.root_layout.add_widget(hint_label)

                search_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=40, spacing=8)
                self.search_input = TextInput(
                    hint_text="Search title, URL, description, or tags",
                    multiline=False,
                )
                self.search_input.bind(text=self.on_search_text)
                search_row.add_widget(self.search_input)
                self.root_layout.add_widget(search_row)

                self.scroll = ScrollView()
                self.list_grid = GridLayout(cols=1, spacing=8, size_hint_y=None)
                self.list_grid.bind(minimum_height=self.list_grid.setter("height"))
                self.scroll.add_widget(self.list_grid)
                self.root_layout.add_widget(self.scroll)

                self.refresh_list()
                return self.root_layout

            def set_status(self, text: str) -> None:
                self.status_label.text = text

            def parse_tags(self, raw: str) -> List[str]:
                return [tag.strip() for tag in raw.split(",") if tag.strip()]

            def current_links(self) -> List[MediaLink]:
                return self.use_cases.search_links(self.search_query)

            def refresh_list(self) -> None:
                self.list_grid.clear_widgets()
                items = self.current_links()

                if not items:
                    self.list_grid.add_widget(
                        Label(
                            text="No links found.",
                            size_hint_y=None,
                            height=40,
                        )
                    )
                    return

                for link in items:
                    card = BoxLayout(
                        orientation="vertical",
                        size_hint_y=None,
                        height=150,
                        spacing=4,
                        padding=6,
                    )

                    info_text = (
                        f"[b]{link.title}[/b]\n"
                        f"{link.url}\n"
                        f"Tags: {', '.join(link.tags) if link.tags else '-'}\n"
                        f"Local: {'yes' if link.is_local else 'no'}\n"
                        f"{link.description or ''}"
                    )
                    card.add_widget(
                        Label(
                            text=info_text,
                            markup=True,
                            halign="left",
                            valign="top",
                            text_size=(780, None),
                            size_hint_y=None,
                            height=100,
                        )
                    )

                    action_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=36, spacing=6)
                    edit_button = Button(text="Edit")
                    edit_button.bind(on_press=partial(self.on_edit, link.link_id))
                    delete_button = Button(text="Delete")
                    delete_button.bind(on_press=partial(self.on_delete, link.link_id))
                    open_button = Button(text="Open")
                    open_button.bind(on_press=partial(self.on_open, link))

                    action_row.add_widget(edit_button)
                    action_row.add_widget(delete_button)
                    action_row.add_widget(open_button)
                    card.add_widget(action_row)

                    self.list_grid.add_widget(card)

            def on_search_text(self, _instance, value: str) -> None:
                self.search_query = value or ""
                self.refresh_list()

            def on_add_or_update(self, _instance) -> None:
                title = self.title_input.text.strip()
                url = self.url_input.text.strip()
                tags = self.parse_tags(self.tags_input.text)
                description = self.description_input.text.strip()
                is_local = bool(self.local_checkbox.active)

                if self.current_edit_id:
                    existing = self.use_cases.get_link(self.current_edit_id)
                    if existing is None:
                        self.set_status("Selected item no longer exists.")
                        self.current_edit_id = None
                        return

                    existing.title = title
                    existing.url = url
                    existing.tags = tags
                    existing.is_local = is_local
                    existing.description = description

                    result = self.use_cases.update_link_safe(existing)
                    if not result["ok"]:
                        self.set_status(result["error"])
                        return

                    self.set_status("Link updated.")
                else:
                    result = self.use_cases.create_link_safe(
                        title=title,
                        url=url,
                        tags=tags,
                        is_local=is_local,
                        description=description,
                    )
                    if not result["ok"]:
                        self.set_status(result["error"])
                        return
                    self.set_status("Link added.")

                self.on_clear_form(None)
                self.refresh_list()

            def on_clear_form(self, _instance) -> None:
                self.current_edit_id = None
                self.title_input.text = ""
                self.url_input.text = ""
                self.tags_input.text = ""
                self.description_input.text = ""
                self.local_checkbox.active = False

            def on_edit(self, link_id: str, _instance) -> None:
                link = self.use_cases.get_link(link_id)
                if link is None:
                    self.set_status("Link not found.")
                    self.refresh_list()
                    return

                self.current_edit_id = link.link_id
                self.title_input.text = link.title
                self.url_input.text = link.url
                self.tags_input.text = ", ".join(link.tags)
                self.description_input.text = link.description
                self.local_checkbox.active = bool(link.is_local)
                self.set_status(f"Editing: {link.title}")

            def on_delete(self, link_id: str, _instance) -> None:
                deleted = self.use_cases.delete_link(link_id)
                if deleted:
                    self.set_status("Link deleted.")
                else:
                    self.set_status("Link not found.")
                if self.current_edit_id == link_id:
                    self.on_clear_form(None)
                self.refresh_list()

            def on_open(self, link: MediaLink, _instance) -> None:
                target = link.url.strip()
                if not target:
                    self.set_status("No URL/path to open.")
                    return

                if link.is_local:
                    path = Path(target)
                    if path.exists():
                        webbrowser.open(path.resolve().as_uri())
                        self.set_status("Opened local media path.")
                    else:
                        self.set_status("Local path does not exist.")
                    return

                webbrowser.open(target)
                self.set_status("Opened remote link.")

        LinkSaverApp().run()


def create_adapter() -> KivyAdapter:
    return KivyAdapter()
