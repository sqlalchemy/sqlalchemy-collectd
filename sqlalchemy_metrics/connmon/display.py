from __future__ import division

import curses
import functools
import operator
import re
import time

from . import util

COLOR_MAP = {
    "K": curses.COLOR_BLACK,
    "R": curses.COLOR_RED,
    "B": curses.COLOR_BLUE,
    "C": curses.COLOR_CYAN,
    "G": curses.COLOR_GREEN,
    "M": curses.COLOR_MAGENTA,
    "W": curses.COLOR_WHITE,
    "Y": curses.COLOR_YELLOW,
    "D": -1,
}

_TEXT_RE = re.compile(r"(#.+?)&", re.M)


def _text_width(text):
    return max(len(_TEXT_RE.sub("", x)) + 2 for x in text.split("\n"))


def _just(text, width):
    padding = (width - len(text)) / 2
    return (" " * int(padding)) + text


def _justify_rows(text):
    width = _text_width(text)
    return [_just(row, width) for row in text.split("\n")]


def _dash_for_fmt(fmt_frag):
    sample = fmt_frag % 5
    return "".join(" " if char != "5" else "-" for char in sample)


class Layout(object):
    def pre_display(self, display):
        pass

    def press_escape(self, display):
        pass

    def resize(self, display):
        pass


class TextLayout(Layout):
    def render(self, display, now):
        top = 6

        for ypos, line in enumerate(self.get_lines(), top):
            display._render_str(ypos, 5, line)


class KeyLayout(TextLayout):
    def pre_display(self, display):
        self.previous_screen = display.screen

    def press_escape(self, display):
        display._refresh_winsize(self.previous_screen)

    def get_lines(self):
        return [
            "#b&++========++",
            "#b&|| Legend ||",
            "#b&++========++",
            "#b&hostname        - #n&Hostname of source machine, ",
            "                  #G&green#d& if currently sending stats, ",
            "                  #R&red#n& if no stats are being received",
            "#b&progname        - #n&program name reported by client",
            "#b&last msg        - #n&number of seconds since last message / ",
            "                  interval between messages in seconds",
            "#b&processes       - #n&number of processes "
            "(with database stats):",
            "                  current reported / max since monitor started",
            "#b&connections     - #n&number of connections: ",
            "                  current reported / max since monitor started /",
            "                  number since last interval",
            "#b&checkouts       - #n&number of checkouts: ",
            "                  current reported / max since monitor started /",
            "                  number since last interval",
            "#b&checkouts / sec - #n&checkouts per second:",
            "                  based on number of checkouts since last ",
            "                  interval divided by interval",
        ]


class StatLayout(Layout):
    def resize(self, display):
        self._calc_x_positions(display)

    def get_rows(self, display, stat, now):
        raise NotImplementedError()

    def _calc_x_positions(self, display):
        x = 0
        widths = []
        for idx, (cname, _, col_width, just) in enumerate(self.columns):
            text_width = _text_width(cname)
            layout_width = int(display._winsize[1] * col_width)
            charwidth = max(text_width, layout_width)
            if just == "L":
                widths.append((x, charwidth))
                x += charwidth
            else:
                width = sum(
                    max(
                        _text_width(r_cname),
                        int(display._winsize[1] * r_col_width),
                    )
                    for (r_cname, _, r_col_width, _) in self.columns[idx:]
                )
                x = display._winsize[1] - width

                widths.append((x, charwidth))

        self._x_positions = widths

    def _render_row(self, display, row, y):
        x_positions = iter(self._x_positions)
        for elem, col in zip(row, self.columns):
            cname, fmt, width, justify = col

            elem = "  ".join(
                [
                    (fmt_frag % elem_frag)
                    if elem_frag is not None
                    else _dash_for_fmt(fmt_frag)
                    for fmt_frag, elem_frag in zip(fmt.split("/"), elem)
                ]
            )
            x, charwidth = next(x_positions)
            display._render_str(
                y,
                x,
                elem,
                center_within_width=charwidth if justify == "R" else None,
            )

    def render(self, display, now):
        stat = display.stat

        display._render_str(
            2,
            0,
            "#Mb&Hosts: #Dn&[%d curr / %d max]  "
            "#Mb&Processes: #Dn&[%d curr / %d max]  "
            % (
                stat.host_count,
                stat.max_host_count,
                stat.process_count,
                stat.max_process_count,
            ),
            "Wb",
        )
        display._render_str(
            3,
            0,
            "#Mb&Connections: #Dn&[%d curr / %d max]  "
            "#Mb&Checkouts: #Dn&[%d curr / %d max / %s]"
            % (
                stat.connection_count,
                stat.max_connections,
                stat.checkout_count,
                stat.max_checkedout,
                ("%.2f / sec" % stat.checkouts_per_second)
                if stat.checkouts_per_second is not None
                else "<calc>",
            ),
            "Wb",
        )

        top = 6

        x_positions = iter(self._x_positions)
        for col in self.columns:
            cname, fmt, width, justify = col
            x, charwidth = next(x_positions)
            rows = _justify_rows(cname)
            display._render_str(
                top,
                x,
                rows[0],
                "Cb",
                center_within_width=charwidth if justify == "R" else None,
            )
            if len(rows) > 1:
                display._render_str(
                    top + 1,
                    x,
                    rows[1],
                    "Cb",
                    center_within_width=charwidth if justify == "R" else None,
                )

        rows = self.get_rows(display, stat, now)

        for y, row in enumerate(rows, top + 2):
            self._render_row(display, row, y)


class ProgStatsLayout(StatLayout):
    columns = [
        ("hostname\n(#R&[dis]#G&connected#d&)", "%s", 0.18, "L"),
        ("progname", "%s", 0.15, "L"),
        ("last msg\nsecs / int", "%s/%3d", 0.10, "R"),
        ("processes\ncurr / max", "%4d/%4d", 0.15, "R"),
        ("connections\ncurr / max / int", "%4d/%4d/%4d", 0.15, "R"),
        ("checkouts\ncurr / max / int", "%4d/%4d/%4d", 0.15, "R"),
        ("checkouts\n/sec", "%.2f", 0.10, "R"),
    ]

    def row_for_hostprog(self, hostprog, now):
        is_connected = bool(hostprog.process_count)
        last_metric = hostprog.last_metric(now)

        host_row = (
            ("#%s&%s" % ("G" if is_connected else "R", hostprog.hostname),),
        )
        if hostprog.progname is not None:
            host_row += ((hostprog.progname,),)

        host_row += (
            (
                "#%s&%d"
                % (
                    "G" if last_metric <= hostprog.interval + 5 else "R",
                    last_metric,
                ),
                hostprog.interval,
            ),
            (hostprog.process_count, hostprog.max_process_count),
            (
                hostprog.connection_count,
                hostprog.max_connections,
                hostprog.interval_connects,
            ),
            (
                hostprog.checkout_count,
                hostprog.max_checkedout,
                hostprog.interval_checkouts,
            ),
            (hostprog.checkouts_per_second,),
        )
        return host_row

    def get_rows(self, display, stat, now):
        rows = []
        hostprogs = list(stat.hostprogs.values())
        hostprogs.sort(
            key=lambda hostprog: (hostprog.hostname, hostprog.progname)
        )
        for hostprog in hostprogs:
            rows.append(self.row_for_hostprog(hostprog, now))

        return rows


class HostStatsLayout(ProgStatsLayout):
    columns = ProgStatsLayout.columns[0:1] + ProgStatsLayout.columns[2:]

    def get_rows(self, display, stat, now):
        rows = []
        hostprogs = list(stat.hosts.values())
        hostprogs.sort(key=lambda hostprog: (hostprog.hostname,))
        for hostprog in hostprogs:
            rows.append(self.row_for_hostprog(hostprog, now))

        return rows


class Display(object):
    def __init__(self, stat, service_str):
        self.stat = stat
        self.service_str = service_str

        self._winsize = None

    def _refresh_winsize(self, screen=None):
        old_winsize = self._winsize

        self._winsize = self.window.getmaxyx()
        if (
            screen is not None
            or old_winsize != self._winsize
            or curses.is_term_resized(*old_winsize)
        ):
            curses.resize_term(*self._winsize)
            if screen:
                screen.pre_display(self)
                self.screen = screen

            self.screen.resize(self)

            if screen:
                self._render(time.time())

    def start(self):
        self.enabled = True
        window = curses.initscr()

        curses.noecho()
        window.erase()
        window.nodelay(1)
        curses.start_color()
        curses.use_default_colors()
        self._color_pairs = {}
        for i, (k, v) in enumerate(COLOR_MAP.items(), 1):
            curses.init_pair(i, v, -1)
            self._color_pairs[k] = curses.color_pair(i)
        self._color_pairs["b"] = curses.A_BOLD
        self._color_pairs["n"] = curses.A_NORMAL
        window.refresh()
        self.window = window
        self._refresh_winsize(ProgStatsLayout())

        try:
            with util.stop_on_keyinterrupt():
                self._redraw()
        finally:
            self.stop()

    def _redraw(self):
        render_timer = util.periodic_timer(0.5)
        while self.enabled:
            time.sleep(0.1)
            now = time.time()
            if render_timer(now):
                self._render(now)
            self._handle_cmds()

    def _handle_cmds(self):
        char = self.window.getch()
        if char in (ord("Q"), ord("q")):
            self.stop()
        elif char in (ord("P"), ord("p")):
            self._refresh_winsize(ProgStatsLayout())
        elif char in (ord("H"), ord("h")):
            self._refresh_winsize(HostStatsLayout())
        elif char in (ord("?"),):
            self._refresh_winsize(KeyLayout())
        elif char in (27,):
            self.screen.press_escape(self)
        elif char == curses.KEY_RESIZE:
            # NOTE: this char breaks if you import readline, which
            # is implicit if you use Python cmd.Cmd() in its default
            # mode
            self._refresh_winsize()

    def stop(self):
        self.enabled = False
        curses.endwin()

    def _get_color(self, color):
        try:
            return self._color_pairs[color]
        except KeyError:
            assert len(color) > 1
            mapped = functools.reduce(
                operator.or_, [self._color_pairs[char] for char in color]
            )
            self._color_pairs[color] = mapped
            return mapped

    def _render_str(
        self,
        y,
        x,
        text,
        default_color="D",
        max_=None,
        center_within_width=None,
    ):
        text_width = _text_width(text)
        if x < 0:
            x = self._winsize[1] - text_width
        elif (
            center_within_width is not None
            and center_within_width > text_width
        ):
            x += (center_within_width - text_width) // 2

        current_color = dflt = self._get_color(default_color)
        if max_:
            max_x = x + max_
        else:
            max_x = self._winsize[1]
        for token in _TEXT_RE.split(text):
            if token.startswith("#"):
                ccode = token[1:]
                if ccode == "d":
                    current_color = dflt
                else:
                    current_color = self._get_color(ccode)
            else:
                try:
                    self.window.addstr(y, x, token[: max_x - x], current_color)
                except curses.error:
                    pass

                x += len(token)
                if x > max_x:
                    break

    def _render(self, now):
        self.window.erase()

        service_str = self.service_str

        self._render_str(0, 0, "#Bb&[Connmon]#Dn& %s" % (service_str,))
        self._render_str(
            0,
            -1,
            "#D&Commands: #Y&(H)#D&ost stats #Y&(P)#D&rogram stats "
            "#Y&(?)#D&Legend #Y&(Q)#D&uit",
        )

        self.screen.render(self, now)

        self.window.refresh()
