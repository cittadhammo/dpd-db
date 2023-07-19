""" Usage example:

```
import PySimpleGUI
from gui.completion_combo import CompletionCombo

layout = [
    [
        CompletionCombo(
            [
                'Kusalā dhammā',
                'Akusalā dhammā',
                'Abyākatā dhammā'
            ],
            enable_events=True,
            key='combo1'),
        CompletionCombo(
            [
                'Sukhāya vedanāya sampayuttā dhammā',
                'Dukkhāya vedanāya sampayuttā dhammā',
                'Adukkham-asukhāya vedanāya sampayuttā dhammā',
            ],
            enable_events=True,
            key='combo2'),
        CompletionCombo(
            [
                'Vipākā dhammā',
                'Vipākadhammadhammā dhammā',
                'Nevavipākanavipākadhammadhammā dhammā',
            ],
            enable_events=True,
            key='combo3'),
    ]
]

window = PySimpleGUI.Window('CompletionCombo example', layout, finalize=True)

for i in range(1, 4):
    combo = window[f'combo{i}']
    combo.bind('<Return>', '-enter')
    combo.bind('<Key>', '-key')
    combo.bind('<FocusOut>', '-focus_out')

# Mainloop
while True:
    event, values = window.read()
    if event == PySimpleGUI.WIN_CLOSED:
        break
    elif event.endswith('-key') and event.startswith('combo'):
        combo = window[event.rstrip('-key')]
        combo.filter()
    elif event.endswith('-enter') and event.startswith('combo'):
        combo = window[event.rstrip('-enter')]
        combo.complete()
    elif event.endswith('-focus_out') and event.startswith('combo'):
        combo = window[event.rstrip('-focus_out')]
        combo.hide_tooltip()

window.close()
```
"""

import logging

from typing import List, Tuple

import PySimpleGUI

LOGGER = logging.getLogger(__name__)


def count_combo_size(values: List[str]) -> Tuple[int, int]:
    width = max(map(len, values)) + 1
    return (width, 0)


class CompletionCombo(PySimpleGUI.Combo):
    """ Combo box with simplified selection

    TooltipObject member should not be changed after initialization
    """
    def __init__(self, values: List[str], *args, **kwargs) -> None:
        self.__values = values
        size = kwargs.get('size')
        if not size:
            self.__size = count_combo_size(values)
        else:
            self.__size = size
        kwargs['size'] = self.__size
        initial_tooltip = kwargs.get('tooltip')
        # if not initial_tooltip:
        self.__initial_tooltip = '\n'.join(values)
        kwargs['tooltip'] = self.__initial_tooltip
        super().__init__(values, *args, **kwargs)

    def hide_tooltip(self) -> None:
        """ Hide the floating list of values
        """
        self.set_tooltip(self.__initial_tooltip)
        self.TooltipObject.hidetip()

    def reset(self) -> None:
        """ Reset values to initial state
        """
        self.update(values=self.__values, size=self.__size)

    def filter(self) -> None:
        """ Filter values with current value
        """
        value = self.get()
        if value:
            search = value
            new_field_values = [x for x in self.__values if search in x]
            key = self.key or self.__class__.__name__
            LOGGER.debug(
                'New values of %s: %s', key, ', '.join(new_field_values))
            self.update(
                value=search,
                values=new_field_values,
                size=self.__size)
            if new_field_values:
                self.set_tooltip('\n'.join(new_field_values))
                tooltip = self.TooltipObject
                tooltip.y += self._calc_tooltip_offset()[1]
                tooltip.showtip()
            else:
                self.hide_tooltip()
        else:
            self.reset()
            self.hide_tooltip()

    def drop_down(self) -> None:
        """
        Drop the list of values down like as the arrow button has been clicked

        Only Tkinter compatible for now
        """
        # Using Tkinter event
        func = getattr(self.widget, "event_generate")
        if func:
            func("<Down>")

    def complete(self) -> None:
        """ Complete word with first entry of the list
        """
        self.update(set_to_index=0)
        self.hide_tooltip()

    def _calc_tooltip_offset(self) -> Tuple[int, int]:
        tooltip_fontsize = 10
        if PySimpleGUI.TOOLTIP_FONT:
            tooltip_fontsize = PySimpleGUI.TOOLTIP_FONT
        _combo_width, combo_height = self.get_size()
        x = 0
        y = 1.0 * combo_height + 2.0 * tooltip_fontsize
        return (x, y)
