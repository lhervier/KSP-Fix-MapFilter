"""Plays the protocols of Map Filter Fix: the map view, the tracking station, and KSP Community Fixes with the
altimeter moved.

It drives KSP through KSP-Util-MCPServer, a mod that answers HTTP requests on 127.0.0.1, and needs nothing but
Python 3: no AI, no package to install. Start KSP with KSP-Util-MCPServer installed, copy map-filter-kerbin.sfs
into a sandbox game, then run:

    python run-filters.py --folder <your sandbox game> --out out

map-filter-kerbin.sfs holds a small capsule on the launch pad, the active vessel, and two rovers landed on
Kerbin; every vessel filter is on in it. Each protocol loads it first, from the space centre: the game is
opened there first when KSP is at its main menu.

The script plays the game as it stands: the mods installed, the size of the window, the interface scale and
the place of KSP Community Fixes' altimeter are set before KSP starts. "all" plays the map view and the
tracking station; the altimeter protocol needs the altimeter moved first, and the other screen sizes and
interface scales are the map view protocol played again in each. The script enters and leaves the map view
with the server's map_view tool, as the M key does, and clicks with its mouse tools, mouse_move and
mouse_click, which move the game's pointer and press its buttons as a mouse does. It finds what it clicks by
moving the pointer over the screen first and reading which interface objects lie under it, so the same
script plays any window size and interface scale:

- the tab of the vessel filters: where it lies on the top row of pixels, its middle being the point of the
  clicks on the top row;
- the tab lower down, while the row is folded: the middle of the rows where the tab, and no hidden filter
  button, is the topmost object under the pointer;
- the tab under the open row: the same, once the row is open;
- a filter of the open row: the middle of its button.

Between two steps, the pointer rests on empty space, away from the top of the screen, where it would
otherwise unfold the altimeter: the altimeter's frame, unfolded, reaches down over the tab.

The map view (--protocol map-view): enter the map view; click the top row of pixels over the middle of the
tab; if the row is still folded, click the tab lower down; click Probes; right-click Ships; click the tab
under the open row.

The tracking station (--protocol tracking-station): go to the space centre, then to the tracking station,
closing a welcome message if one shows; click Probes; right-click Ships.

KSP Community Fixes with the altimeter moved (--protocol altimeter-moved): as the map view up to the row open,
then leave the map view and enter it again, as the M key does; click the top row of pixels and, if the row
is still folded, the tab lower down, again; then click Probes and right-click Ships.

A screenshot is taken at the start, in the flight view, and after every step, as a PNG the size of the
window. With Pillow installed, each is also cropped as the pages show them, 640 pixels wide, as a JPEG: in
the map view, the top of the screen around the tab, 480 by 64 pixels at an interface scale of 100 %, the box
scaled with the interface; in the tracking station, its top left; the flight view whole. The script prints
each point it clicks with the object under it, and writes them to runs.json. KSP is left running at the end.
"""
import argparse
import json
import os
import time
import urllib.request

URL = None

# The width of the folded tab in pixels, at an interface scale of 100 %: the interface scale is the width the
# tab is found at, divided by this one.
TAB_WIDTH_AT_100 = 46

# The crop of the map view, at an interface scale of 100 %: its width and height, and how far right of the
# middle of the tab its middle lies.
CROP_WIDTH, CROP_HEIGHT, CROP_SHIFT = 480, 64, 12

# The crop of the tracking station: the left three quarters of the window, and its top 13 thirty-sixths
# (960 by 260 pixels in a 1280 by 720 window).
STATION_CROP = (0.75, 13 / 36)

# The tab of the vessel filters, as the interface names it.
TAB = "ButtonTabToggle"

# How long the row of filters takes to slide, and a tooltip to go, in seconds.
SETTLE = 1.8


def call(tool, **args):
    """Calls one tool of KSP-Util-MCPServer and returns its answer, decoded from JSON when it is JSON."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": tool, "arguments": args}}).encode()
    request = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=900) as response:
        result = json.loads(response.read())["result"]
    text = result["content"][0].get("text", "") if result["content"] else ""
    if result.get("isError"):
        raise RuntimeError(tool + ": " + text)
    try:
        return json.loads(text)
    except ValueError:
        return text


def log(*parts):
    print(time.strftime("%H:%M:%S"), *parts, flush=True)


class Screen:
    """The game's window: its size, where the pointer rests between steps, and what lies under a point."""

    def __init__(self):
        answer = self.move(0, 100)
        self.width, self.height = answer["window"]["width"], answer["window"]["height"]
        # Empty space in the map view and in the tracking station: left of the middle, below the top bar.
        self.rest = (round(self.width * 0.2), round(self.height * 0.42))

    @staticmethod
    def move(x, y):
        return call("mouse_move", x=x, y=y)

    def names(self, x, y):
        """The names of the interface objects under x, y, the topmost first."""
        return [item["name"] for item in self.move(x, y)["ui"]]

    def topmost(self, x, y):
        """The interface object a click at x, y reaches, or None."""
        objects = self.move(x, y)["ui"]
        return objects[0]["clickHandler"] if objects else None

    def park(self, seconds=SETTLE):
        """Rests the pointer on empty space, and lets the interface settle."""
        self.move(*self.rest)
        time.sleep(seconds)

    def run_along_row(self, y, name, x_from, x_to):
        """The first and last x of the first run of pixels of row y, between x_from and x_to, over which an
        object of that name lies under the pointer, or None."""
        first = None
        for x in range(x_from, x_to):
            if name in self.names(x, y):
                if first is None:
                    first = x
            elif first is not None:
                return first, x - 1
        return (first, x_to - 1) if first is not None else None

    def run_down_column(self, x, test, y_from=0, y_to=None):
        """The first and last y of the first run of pixels of column x, from y_from down, for which test holds
        on the names of the objects under the pointer, or None."""
        y_to = self.height if y_to is None else y_to
        first = None
        for y in range(y_from, y_to):
            if test(self.names(x, y)):
                if first is None:
                    first = y
            elif first is not None:
                return first, y - 1
        return (first, y_to - 1) if first is not None else None


class Run:
    """One protocol played: its screenshots and the points it clicked."""

    def __init__(self, screen, out):
        self.screen = screen
        self.out = out
        self.steps = []
        # Set once the tab is found: its middle, and the interface scale its width tells.
        self.tab_x = None
        self.scale = None

    def shot(self, name, crop):
        """Rests the pointer, takes a screenshot named after the step, and crops it as the pages show it."""
        self.screen.park()
        path = os.path.abspath(os.path.join(self.out, name + ".png"))
        call("screenshot", path=path, return_image=False)
        self.steps.append({"step": name, "screenshot": name + ".png"})
        log(name)
        crop_image(path, os.path.join(self.out, "cropped", name + ".jpg"), crop)

    def click(self, x, y, button="left", what=""):
        """Clicks at x, y, and records the point and the object that takes the click there."""
        # The pointer goes there first: what lies under it before the click, the click itself changing it.
        under = self.screen.topmost(x, y)
        call("mouse_click", x=x, y=y, button=button)
        self.steps.append({"click": what, "x": x, "y": y, "button": button, "under": under})
        log("%s click at %d, %d (%s), over %s" % (button, x, y, what, under))

    def map_crop(self):
        """The crop box of the map view: the top of the screen around the tab, scaled with the interface."""
        middle = self.tab_x + CROP_SHIFT * self.scale
        half = CROP_WIDTH * self.scale / 2
        return round(middle - half), 0, round(middle + half), round(CROP_HEIGHT * self.scale)

    def find_tab(self):
        """Finds the middle of the tab on the top row of pixels, and the interface scale its width tells.
        Fails when something other than the vessel filters lies on top there."""
        screen = self.screen
        found = screen.run_along_row(0, TAB, screen.width // 4, screen.width * 3 // 4)
        if found is None:
            raise RuntimeError("the tab of the vessel filters is not on the top row of the screen")
        self.tab_x = (found[0] + found[1]) // 2
        # Rounded to the nearest 5 %, which absorbs a pixel more or less at the tab's edges.
        self.scale = round((found[1] - found[0] + 1) / TAB_WIDTH_AT_100 * 20) / 20
        on_top = screen.move(self.tab_x, 0)["ui"][0]
        if "/TrackingFilters/" not in on_top["path"]:
            raise RuntimeError("over the tab, the top row of pixels belongs to " + on_top["path"])
        self.steps.append({"tab": {"from": found[0], "to": found[1], "middle": self.tab_x,
                                   "scale": round(self.scale, 3)}})
        log("tab from x %d to %d, interface scale %.2f" % (found[0], found[1], self.scale))

    def row_is_open(self):
        """Whether the row of filters is open: the folded tab touches the top row of the screen, the open
        one lies under the row."""
        return TAB not in self.screen.names(self.tab_x, 0)

    def tab_point(self):
        """The middle of the rows of the tab's column where the tab is the topmost object under the
        pointer."""
        rows = self.screen.run_down_column(self.tab_x, lambda names: bool(names) and names[0] == TAB)
        if rows is None:
            raise RuntimeError("the tab takes no click in its column")
        return self.tab_x, (rows[0] + rows[1]) // 2

    def filter_points(self, names):
        """The middle of the buttons of the filters named, in a row of filters that is open."""
        screen = self.screen
        wanted = ["Button " + name for name in names]
        # The buttons touch the top of the screen, in its middle half: their runs along the third row of
        # pixels, in one pass.
        runs = {}
        for x in range(screen.width // 4, screen.width * 3 // 4):
            under = screen.names(x, 2)
            for button in wanted:
                if button in under:
                    first, _ = runs.get(button, (x, x))
                    runs[button] = (first, x)
        points = {}
        for name, button in zip(names, wanted):
            if button not in runs:
                raise RuntimeError("no button of the filter " + name)
            x = (runs[button][0] + runs[button][1]) // 2
            # Then the run down the column through the middle of the button.
            rows = screen.run_down_column(x, lambda under: button in under)
            points[name] = (x, (rows[0] + rows[1]) // 2)
        return points

    def click_top_row(self, name):
        """Clicks the top row of pixels over the middle of the tab, then, if the row is still folded, the tab
        lower down; a screenshot after each."""
        self.click(self.tab_x, 0, what="top row, over the tab")
        self.shot(name[0], self.map_crop())
        if self.row_is_open():
            log("the row is open: no click")
        else:
            x, y = self.tab_point()
            self.click(x, y, what="the tab lower down")
        self.shot(name[1], self.map_crop())
        if not self.row_is_open():
            raise RuntimeError("the row of filters did not open")


def crop_image(source, target, box):
    """Crops a screenshot to box (left, top, right, bottom; None for the whole image) and saves it 640 pixels
    wide as a JPEG. Does nothing without Pillow."""
    try:
        from PIL import Image
    except ImportError:
        return
    image = Image.open(source).convert("RGB")
    if box is not None:
        image = image.crop(box)
    image = image.resize((640, round(image.height * 640 / image.width)), Image.LANCZOS)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    image.save(target, quality=88)


def start(options):
    """Loads the save into flight, from the space centre, and rests the pointer. Returns the game's window."""
    scene = call("get_state")["scene"]
    if scene == "MAINMENU":
        call("open_game", folder=options.folder)
    elif scene not in ("SPACECENTER", "FLIGHT"):
        call("go_to_scene", scene="SPACECENTER")
    # Right after the game opens, the server may not take the load yet: try again a few seconds later.
    for attempt in range(3):
        try:
            call("load_save", folder=options.folder, save=options.save)
            break
        except Exception as e:
            if attempt == 2:
                raise
            log("load_save failed, trying again:", e)
            time.sleep(5)
    screen = Screen()
    # The pointer off the top of the screen: there, it unfolds the altimeter.
    screen.park(3)
    return screen


def enter_map_view(run):
    run.screen.park(0)
    call("map_view", enabled=True)
    run.screen.park()


def map_view(options, out):
    run = Run(start(options), out)
    run.shot("0-flight", None)
    enter_map_view(run)
    run.find_tab()
    run.click_top_row(("1-click-top-edge", "2-row-open"))
    points = run.filter_points(("Probes", "Ships"))
    run.click(*points["Probes"], what="Probes")
    run.shot("3-probes-clicked", run.map_crop())
    run.click(*points["Ships"], button="right", what="Ships")
    run.shot("4-ships-right-clicked", run.map_crop())
    x, y = run.tab_point()
    run.click(x, y, what="the tab under the open row")
    run.shot("5-row-folded", run.map_crop())
    if run.row_is_open():
        raise RuntimeError("the row of filters did not fold")
    return run.steps


def tracking_station(options, out):
    screen = start(options)
    run = Run(screen, out)
    call("go_to_scene", scene="SPACECENTER")
    call("go_to_scene", scene="TRACKSTATION")
    # On a first visit, a welcome message: closed by its button.
    closed = call("close_screen", dialogs_only=True)
    run.steps.append({"closed": closed})
    log("closed:", closed)
    # The name of the body the view centres on shows a few seconds at the top of the screen.
    time.sleep(5)
    box = (0, 0, round(screen.width * STATION_CROP[0]), round(screen.height * STATION_CROP[1]))
    run.shot("1-tracking-station", box)
    points = run.filter_points(("Probes", "Ships"))
    run.click(*points["Probes"], what="Probes")
    run.shot("2-probes-clicked", box)
    run.click(*points["Ships"], button="right", what="Ships")
    run.shot("3-ships-right-clicked", box)
    return run.steps


def altimeter_moved(options, out):
    run = Run(start(options), out)
    run.shot("0-flight", None)
    enter_map_view(run)
    run.find_tab()
    run.click_top_row(("1-click-top-edge", "2-row-open"))
    # Out of the map view and back, as the M key does twice.
    run.screen.park(0)
    call("map_view", enabled=False)
    run.screen.park()
    enter_map_view(run)
    run.shot("3-map-view-again", run.map_crop())
    run.click_top_row(("4-click-top-edge-again", "5-row-open"))
    points = run.filter_points(("Probes", "Ships"))
    run.click(*points["Probes"], what="Probes")
    run.screen.park()
    run.click(*points["Ships"], button="right", what="Ships")
    run.shot("6-probes-then-ships", run.map_crop())
    return run.steps


PROTOCOLS = {"map-view": map_view, "tracking-station": tracking_station, "altimeter-moved": altimeter_moved}
# The protocols "all" plays: those that need KSP Community Fixes' altimeter at its stock place.
STOCK_PROTOCOLS = ["map-view", "tracking-station"]


def main():
    global URL
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--folder", required=True, help="the sandbox game under saves/ the save was copied into")
    parser.add_argument("--save", default="map-filter-kerbin", help="the save, without .sfs")
    parser.add_argument("--protocol", choices=list(PROTOCOLS) + ["all"], default="all")
    parser.add_argument("--out", required=True, help="the folder for runs.json and the screenshots")
    parser.add_argument("--port", type=int, default=8770, help="the port of KSP-Util-MCPServer")
    options = parser.parse_args()
    URL = "http://127.0.0.1:%d/mcp/" % options.port

    names = STOCK_PROTOCOLS if options.protocol == "all" else [options.protocol]
    runs = {}
    for name in names:
        out = os.path.join(options.out, name)
        os.makedirs(out, exist_ok=True)
        log("protocol", name)
        runs[name] = PROTOCOLS[name](options, out)
    with open(os.path.join(options.out, "runs.json"), "w", newline="\n") as f:
        json.dump(runs, f, indent=1)
    log("done")


if __name__ == "__main__":
    main()
