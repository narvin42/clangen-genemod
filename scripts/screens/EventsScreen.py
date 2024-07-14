from math import floor

import pygame
import pygame_gui
from pygame_gui.core import ObjectID

from scripts.cat.cats import Cat
from scripts.event_class import Single_Event
from scripts.events import events_class
from scripts.game_structure import image_cache
from scripts.game_structure.game_essentials import game, MANAGER
from scripts.game_structure.ui_elements import (
    UIImageButton,
    UIModifiedScrollingContainer,
    IDImageButton,
    UISurfaceImageButton,
)
from scripts.game_structure.windows import GameOver
from scripts.screens.Screens import Screens
from scripts.ui.generate_button import get_button_dict, ButtonStyles
from scripts.utility import (
    ui_scale,
    clan_symbol_sprite,
    get_text_box_theme,
    shorten_text_to_fit,
    get_living_clan_cat_count,
    ui_scale_dimensions,
    ui_scale_value,
)


class EventsScreen(Screens):
    current_display = "all"
    selected_display = "all"

    all_events = ""
    ceremony_events = ""
    birth_death_events = ""
    relation_events = ""
    health_events = ""
    other_clans_events = ""
    misc_events = ""
    display_text = (
        "<center>See which events are currently happening in the Clan.</center>"
    )
    display_events = []
    tabs = [
        "all",
        "ceremony",
        "birth_death",
        "relationship",
        "health",
        "other_clans",
        "misc",
    ]

    def __init__(self, name):
        super().__init__(name)

        self.events_thread = None
        self.event_screen_container = None
        self.clan_info = {}
        self.timeskip_button = None

        self.full_event_display_container = None
        self.events_frame = None
        self.event_buttons = {}
        self.alert = {}

        self.event_display = None
        self.event_display_elements = {}
        self.cat_profile_buttons = {}
        self.involved_cat_container = None
        self.involved_cat_buttons = {}

        # Stores the involved cat button that currently has its cat profile buttons open
        self.open_involved_cat_button = None

        self.first_opened = False

    def handle_event(self, event):
        if game.switches["window_open"]:
            return

        # ON HOVER
        if event.type == pygame_gui.UI_BUTTON_ON_HOVERED:
            element = event.ui_element
            if element in self.event_buttons.values():
                for ele in self.event_buttons:
                    if self.event_buttons[ele] == element:
                        x_pos = int(self.alert[ele].get_relative_rect()[0] - 10)
                        y_pos = self.alert[ele].get_relative_rect()[1]
                        self.alert[ele].set_relative_position((x_pos, y_pos))

        # ON UNHOVER
        elif event.type == pygame_gui.UI_BUTTON_ON_UNHOVERED:
            element = event.ui_element
            if element in self.event_buttons.values():
                for ele in self.event_buttons:
                    if self.event_buttons[ele] == element:
                        x_pos = int(self.alert[ele].get_relative_rect()[0] + 10)
                        y_pos = self.alert[ele].get_relative_rect()[1]
                        self.alert[ele].set_relative_position((x_pos, y_pos))

        # ON START BUTTON PRESS
        elif (
            event.type == pygame_gui.UI_BUTTON_START_PRESS
        ):  # this happens on start press to prevent alert movement
            element = event.ui_element
            if element in self.event_buttons.values():
                for ele, val in self.event_buttons.items():
                    if val == element:
                        self.handle_tab_switch(ele)
                        break

        # ON FULL BUTTON PRESS
        elif (
            event.type == pygame_gui.UI_BUTTON_PRESSED
        ):  # everything else on button press to prevent blinking
            element = event.ui_element
            if element == self.timeskip_button:
                self.events_thread = self.loading_screen_start_work(
                    events_class.one_moon
                )
            elif element in self.involved_cat_buttons.values():
                self.make_cat_buttons(element)
            elif element in self.cat_profile_buttons.values():
                self.save_scroll_position()
                game.switches["cat"] = element.ids
                self.change_screen("profile screen")
            else:
                self.save_scroll_position()
                self.menu_button_pressed(event)

        # KEYBIND CONTROLS
        elif game.settings["keybinds"]:
            # ON PRESSING A KEY
            if event.type == pygame.KEYDOWN:
                # LEFT ARROW
                if event.key == pygame.K_LEFT:
                    self.change_screen("patrol screen")
                # RIGHT ARROW
                elif event.key == pygame.K_RIGHT:
                    self.change_screen("camp screen")
                # DOWN AND UP ARROW
                elif event.key == pygame.K_DOWN or event.key == pygame.K_UP:
                    self.handle_tab_select(event.key)
                elif event.key == pygame.K_RETURN:
                    self.handle_tab_switch(self.selected_display)

    def save_scroll_position(self):
        """
        adds current event display vert scroll bar position to game.switches["saved_scroll_positions"] dict
        """
        if self.event_display.vert_scroll_bar:
            game.switches["saved_scroll_positions"][self.current_display] = (
                self.event_display.vert_scroll_bar.scroll_position
                / self.event_display.vert_scroll_bar.scrollable_height
            )

    def handle_tab_select(self, event):

        # find next tab based on current tab
        current_index = self.tabs.index(self.selected_display)
        if event == pygame.K_DOWN:
            next_index = current_index + 1
            wrap_index = 0
        else:
            next_index = current_index - 1
            wrap_index = -1

        # unselect the currently selected display
        # unless it matches the current display, we don't want to mess with the state of that button
        if self.current_display != self.selected_display:
            self.event_buttons[self.selected_display].unselect()
            x_pos = int(self.alert[self.selected_display].get_relative_rect()[0] + 10)
            y_pos = self.alert[self.selected_display].get_relative_rect()[1]
            self.alert[self.selected_display].set_relative_position((x_pos, y_pos))

        # find the new selected display
        try:
            self.selected_display = self.tabs[next_index]
        except IndexError:
            self.selected_display = self.tabs[wrap_index]

        # select the new selected display
        # unless it matches the current display, we don't want to mess with the state of that button
        if self.current_display != self.selected_display:
            self.event_buttons[self.selected_display].select()
            x_pos = int(self.alert[self.selected_display].get_relative_rect()[0] - 10)
            y_pos = self.alert[self.selected_display].get_relative_rect()[1]
            self.alert[self.selected_display].set_relative_position((x_pos, y_pos))

    def handle_tab_switch(self, display_type):
        """
        saves current tab scroll position, removes alert, and then switches to the new tab
        """
        self.save_scroll_position()

        self.current_display = display_type
        self.update_list_buttons()

        if display_type == "all":
            self.display_events = self.all_events
        elif display_type == "ceremony":
            self.display_events = self.ceremony_events
        elif display_type == "birth_death":
            self.display_events = self.birth_death_events
        elif display_type == "relationship":
            self.display_events = self.relation_events
        elif display_type == "health":
            self.display_events = self.health_events
        elif display_type == "other_clans":
            self.display_events = self.other_clans_events
        elif display_type == "misc":
            self.display_events = self.misc_events

        self.alert[display_type].hide()

        self.update_events_display()

    def screen_switches(self):
        super().screen_switches()
        # On first open, update display events list
        if not self.first_opened:
            self.first_opened = True
            self.update_display_events_lists()
            self.display_events = self.all_events

        self.event_screen_container = pygame_gui.core.UIContainer(
            ui_scale(pygame.Rect((0, 0), (800, 700))),
            starting_height=1,
            manager=MANAGER,
        )

        self.clan_info["symbol"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((227, 105), (100, 100))),
            pygame.transform.scale(
                clan_symbol_sprite(game.clan), ui_scale_dimensions((100, 100))
            ),
            object_id=f"clan_symbol",
            starting_height=1,
            container=self.event_screen_container,
            manager=MANAGER,
        )

        self.clan_info["heading"] = pygame_gui.elements.UITextBox(
            "Timeskip to progress your Clan's life.",
            ui_scale(pygame.Rect((340, 155), (250, -1))),
            object_id=get_text_box_theme("#text_box_30_horizleft_spacing_95"),
            starting_height=1,
            container=self.event_screen_container,
            manager=MANAGER,
        )

        self.clan_info["season"] = pygame_gui.elements.UITextBox(
            f"Current season: {game.clan.current_season}",
            ui_scale(pygame.Rect((340, 102), (600, 40))),
            object_id=get_text_box_theme("#text_box_30"),
            starting_height=1,
            container=self.event_screen_container,
            manager=MANAGER,
        )
        self.clan_info["age"] = pygame_gui.elements.UITextBox(
            "",
            ui_scale(pygame.Rect((340, 122), (600, 40))),
            object_id=get_text_box_theme("#text_box_30"),
            starting_height=1,
            container=self.event_screen_container,
            manager=MANAGER,
        )

        # Set text for Clan age
        if game.clan.age == 1:
            self.clan_info["age"].set_text(f"Clan age: {game.clan.age} moon")
        if game.clan.age != 1:
            self.clan_info["age"].set_text(f"Clan age: {game.clan.age} moons")

        self.timeskip_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((310, 218), (180, 30))),
            "Timeskip One Moon",
            get_button_dict(ButtonStyles.ROUNDED_RECT, (180, 30)),
            object_id="@buttonstyles_rounded_rect",
            starting_height=1,
            container=self.event_screen_container,
            manager=MANAGER,
        )

        self.full_event_display_container = pygame_gui.core.UIContainer(
            ui_scale(pygame.Rect((45, 266), (700, 700))),
            starting_height=1,
            container=self.event_screen_container,
            manager=MANAGER,
        )
        self.events_frame = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((161, 0), (534, 370))),
            image_cache.load_image(
                "resources/images/event_page_frame.png"
            ).convert_alpha(),
            object_id="#events_frame",
            starting_height=2,
            container=self.full_event_display_container,
            manager=MANAGER,
        )

        y_pos = 0
        for event_type in self.tabs:
            self.event_buttons[f"{event_type}"] = UIImageButton(
                ui_scale(pygame.Rect((15, 19 + y_pos), (150, 30))),
                "",
                object_id=f"#{event_type}_events_button",
                starting_height=1,
                container=self.full_event_display_container,
                manager=MANAGER,
            )

            if event_type:
                self.alert[f"{event_type}"] = pygame_gui.elements.UIImage(
                    ui_scale(pygame.Rect((10, 24 + y_pos), (4, 22))),
                    pygame.transform.scale(
                        image_cache.load_image("resources/images/alert_mark.png"),
                        ui_scale_dimensions((4, 22)),
                    ),
                    container=self.full_event_display_container,
                    object_id=f"alert_mark_{event_type}",
                    manager=MANAGER,
                    visible=False,
                )

            y_pos += 50

        self.event_buttons[self.current_display].disable()

        self.make_event_scrolling_container()
        self.open_involved_cat_button = None
        self.update_events_display()

        # Draw and disable the correct menu buttons.
        self.set_disabled_menu_buttons(["events_screen"])
        self.update_heading_text(f"{game.clan.name}Clan")
        self.show_menu_buttons()

    def make_event_scrolling_container(self):
        """
        kills and recreates the self.event_display container
        """
        if self.event_display:
            self.event_display.kill()

        self.event_display = UIModifiedScrollingContainer(
            ui_scale(pygame.Rect((211, 275), (540, 350))),
            starting_height=3,
            manager=MANAGER,
            allow_scroll_y=True,
        )

    def make_cat_buttons(self, button_pressed):
        """Makes the buttons that take you to the profile."""

        # How much to increase the panel box size by in order to fit the catbuttons
        size_increase = 26

        # Check if the button you pressed doesn't have its cat profile buttons currently displayed.
        # if it does, clear the cat profile buttons
        if self.open_involved_cat_button == button_pressed:
            self.open_involved_cat_button = None
            if len(self.cat_profile_buttons) > 2:
                button_pressed.parent_element.set_dimensions(
                    (
                        button_pressed.parent_element.get_relative_rect()[2],
                        button_pressed.parent_element.get_relative_rect()[3]
                        - ui_scale_value(size_increase),
                    ),
                )
            for ele in self.cat_profile_buttons:
                self.cat_profile_buttons[ele].kill()
            self.cat_profile_buttons = {}
            return
        # now check if the involved cat display is already open somewhere
        # if so, shrink that back to original size
        elif (
            self.open_involved_cat_button is not None
            and len(self.cat_profile_buttons) > 2
        ):
            self.open_involved_cat_button.parent_element.set_dimensions(
                (
                    self.open_involved_cat_button.parent_element.get_relative_rect()[2],
                    self.open_involved_cat_button.parent_element.get_relative_rect()[3]
                    - ui_scale_value(size_increase),
                ),
            )

        # If it doesn't have its buttons displayed, set the current open involved_cat_button to the pressed button,
        # clear all other buttons, and open the cat profile buttons.
        self.open_involved_cat_button = button_pressed
        if self.involved_cat_container:
            self.involved_cat_container.kill()
        for ele in self.cat_profile_buttons:
            self.cat_profile_buttons[ele].kill()
        self.cat_profile_buttons = {}

        container = button_pressed.parent_element

        if len(button_pressed.ids) > 2:
            container.set_dimensions(
                (
                    container.relative_rect[2],
                    container.relative_rect[3] + ui_scale_value(size_increase),
                )
            )

        involved_cat_rect = ui_scale(
            pygame.Rect((0, 0), (455, 56 if len(button_pressed.ids) > 2 else 36))
        )
        involved_cat_rect.topleft = (
            ui_scale_value(5),
            -button_pressed.get_relative_rect()[3],
        )

        self.involved_cat_container = UIModifiedScrollingContainer(
            involved_cat_rect,
            container=container,
            manager=MANAGER,
            starting_height=2,
            allow_scroll_x=True,
            allow_scroll_y=False,
            anchors={"top_target": button_pressed},
        )
        del involved_cat_rect

        for i, cat_id in enumerate(button_pressed.ids):
            cat_ob = Cat.fetch_cat(cat_id)
            if cat_ob:
                # Shorten name if needed
                name = str(cat_ob.name)
                short_name = shorten_text_to_fit(name, 195, 13)

                self.cat_profile_buttons[f"profile_button{i}"] = IDImageButton(
                    ui_scale(pygame.Rect((0 if i == 0 else 5, 0), (120, 34))),
                    text=short_name,
                    ids=cat_id,
                    container=self.involved_cat_container,
                    object_id="#events_cat_profile_button",
                    layer_starting_height=1,
                    manager=MANAGER,
                    anchors={
                        "left_target": self.cat_profile_buttons[f"profile_button{i-1}"]
                    }
                    if i > 0
                    else {"left": "left"},
                )
        self.involved_cat_container.set_view_container_dimensions(
            (
                self.involved_cat_container.get_relative_rect()[2],
                self.event_display.get_relative_rect()[3],
            )
        )

    def exit_screen(self):
        self.event_display.kill()  # event display isn't put in the screen container due to lag issues
        self.event_screen_container.kill()

    def update_display_events_lists(self):
        """
        Categorize events from game.cur_events_list into display categories for screen
        """

        self.all_events = [
            x for x in game.cur_events_list if "interaction" not in x.types
        ]
        self.ceremony_events = [
            x for x in game.cur_events_list if "ceremony" in x.types
        ]
        self.birth_death_events = [
            x for x in game.cur_events_list if "birth_death" in x.types
        ]
        self.relation_events = [
            x for x in game.cur_events_list if "relation" in x.types
        ]
        self.health_events = [x for x in game.cur_events_list if "health" in x.types]
        self.other_clans_events = [
            x for x in game.cur_events_list if "other_clans" in x.types
        ]
        self.misc_events = [x for x in game.cur_events_list if "misc" in x.types]

    def update_events_display(self):
        """
        Kills and recreates the event display, updates the clan info, sets the event display scroll position if it was
        previously saved
        """

        # UPDATE CLAN INFO
        self.clan_info["season"].set_text(f"Current season: {game.clan.current_season}")
        if game.clan.age == 1:
            self.clan_info["age"].set_text(f"Clan age: {game.clan.age} moon")
        else:
            self.clan_info["age"].set_text(f"Clan age: {game.clan.age} moons")

        self.make_event_scrolling_container()

        for ele in self.event_display_elements:
            self.event_display_elements[ele].kill()
        self.event_display_elements = {}

        for ele in self.cat_profile_buttons:
            self.cat_profile_buttons[ele].kill()
        self.cat_profile_buttons = {}

        for ele in self.involved_cat_buttons:
            self.involved_cat_buttons[ele].kill()
        self.involved_cat_buttons = {}

        # Stop if Clan is new, so that events from previously loaded Clan don't show up
        if game.clan.age == 0:
            return

        for event_object in self.display_events:
            if not isinstance(event_object.text, str):
                print(
                    f"Incorrectly Formatted Event: {event_object.text}, {type(event_object)}"
                )
                self.display_events.remove(event_object)
                continue

        default_rect = ui_scale(
            pygame.Rect(
                (5, 0),
                (
                    self.event_display.get_relative_rect()[2]
                    - 2
                    - self.event_display.scroll_bar_width,
                    300,
                ),
            )
        )
        for i, event_object in enumerate(self.display_events):
            self.event_display_elements[f"container{i}"] = pygame_gui.elements.UIPanel(
                default_rect,
                1,
                MANAGER,
                container=self.event_display,
                element_id="event_panel",
                object_id="#dark" if game.settings["dark mode"] else None,
                margins={"top": 0, "bottom": 0, "left": 0, "right": 0},
                anchors={"top_target": self.event_display_elements[f"container{i-1}"]}
                if i > 0
                else {"top": "top"},
            )
            if i % 2 == 0:
                self.event_display_elements[f"container{i}"].background_colour = (
                    pygame.Color(87, 76, 55)
                    if game.settings["dark mode"]
                    else pygame.Color(167, 148, 111)
                )
                self.event_display_elements[f"container{i}"].rebuild()

        for i, event_object in enumerate(self.display_events):
            # TEXT BOX
            self.event_display_elements[f"event{i}"] = pygame_gui.elements.UITextBox(
                event_object.text,
                ui_scale(pygame.Rect((0, 0), (509, -1))),
                object_id=get_text_box_theme("#text_box_30_horizleft"),
                starting_height=1,
                container=self.event_display_elements[f"container{i}"],
                manager=MANAGER,
                anchors={"left": "left", "right": "right"},
            )

        catbutton_rect = ui_scale(pygame.Rect((0, 0), (34, 34)))
        catbutton_rect.topright = ui_scale_dimensions((-10, 5))
        for i, event_object in enumerate(self.display_events):
            if not event_object.cats_involved:
                continue

            self.involved_cat_buttons[f"cat_button{i}"] = IDImageButton(
                catbutton_rect,
                ids=event_object.cats_involved,
                layer_starting_height=3,
                object_id="#events_cat_button",
                parent_element=self.event_display_elements[f"container{i}"],
                container=self.event_display_elements[f"container{i}"],
                manager=MANAGER,
                anchors={
                    "right": "right",
                    "top_target": self.event_display_elements[f"event{i}"],
                },
            )
        del catbutton_rect

        for i, event_object in enumerate(self.display_events):
            self.event_display_elements[f"container{i}"].set_dimensions(
                (
                    default_rect[2],
                    self.event_display_elements[f"event{i}"].get_relative_rect()[3]
                    + (
                        self.involved_cat_buttons[f"cat_button{i}"].get_relative_rect()[
                            3
                        ]
                        + ui_scale_value(10)
                    )
                    if f"cat_button{i}" in self.involved_cat_buttons
                    else 0,
                )
            )

        # this HAS TO UPDATE before saved scroll position can be set
        self.event_display.scrollable_container.update(1)

        # don't ask me why we have to redefine these dimensions, we just do
        # otherwise the scroll position save will break
        self.event_display.set_dimensions(
            (
                self.event_display.get_relative_rect()[2],
                self.event_display.get_relative_rect()[3],
            )
        )

        # set saved scroll position
        if game.switches["saved_scroll_positions"].get(self.current_display):
            self.event_display.vert_scroll_bar.set_scroll_from_start_percentage(
                game.switches["saved_scroll_positions"][self.current_display]
            )

    def update_list_buttons(self):
        """
        re-enable all event tab buttons, then disable the currently selected tab
        """
        for ele in self.event_buttons:
            self.event_buttons[ele].enable()

        self.event_buttons[self.current_display].disable()

    def on_use(self):
        super().on_use()
        self.loading_screen_on_use(self.events_thread, self.timeskip_done)
        pass

    def timeskip_done(self):
        """Various sorting and other tasks that must be done with the timeskip is over."""

        game.switches["saved_scroll_positions"] = {}

        if get_living_clan_cat_count(Cat) == 0:
            GameOver("events screen")

        self.update_display_events_lists()

        self.current_display = "all"
        self.event_buttons["all"].disable()

        for tab in self.event_buttons:
            if tab != "all":
                self.event_buttons[tab].enable()

        if not self.all_events:
            self.all_events.append(
                Single_Event("Nothing interesting happened this moon.")
            )

        self.display_events = self.all_events

        if self.ceremony_events:
            self.alert["ceremony"].show()
        else:
            self.alert["ceremony"].hide()

        if self.birth_death_events:
            self.alert["birth_death"].show()
        else:
            self.alert["birth_death"].hide()

        if self.relation_events:
            self.alert["relationship"].show()
        else:
            self.alert["relationship"].hide()

        if self.health_events:
            self.alert["health"].show()
        else:
            self.alert["health"].hide()

        if self.other_clans_events:
            self.alert["other_clans"].show()
        else:
            self.alert["other_clans"].hide()

        if self.misc_events:
            self.alert["misc"].show()
        else:
            self.alert["misc"].hide()

        self.update_events_display()
