# Map Filter Fix

**⚠️ Work in progress.** This is a new fix, not a finished mod. The code and the conclusions on this page can still change, and what is still to be checked is listed in [Work in progress](#work-in-progress).

A fix for stock KSP 1.12, kept as small as possible: one Harmony patch, in one short source file. It is a
mod of its own, built on top of
[KSP Community Fixes](https://github.com/KSPModdingLibs/KSPCommunityFixes), the base most players run.
Here is what it fixes:

> **In the map view, a click at the very top of the screen, on the tab that opens the vessel filters,
> does not open them: it toggles one of the filters instead, without showing anything.** The tab only
> opens when aimed at a few pixels lower.

**How this was made.** The investigation and the code were written with Claude, Anthropic's AI
assistant. Everything here was reviewed and validated by a human — me. I am saying so up front, because
contributions made with an AI deserve a closer look than others, and because some people would rather
stop reading here. That look should be quick: the stock code involved is named on this page, and the fix
is one short file you can read in a few minutes.

## Why a click at the top of the screen matters

In the map view, the small tab with an arrow, at the top of the screen in the middle, opens a row of
buttons that choose which types of vessels the map shows: probes, stations, debris, and so on. The tab
touches the top edge of the screen, so the natural gesture is to throw the mouse up against the edge and
click.

<img src="imgs/why-a-click-at-the-top-matters/map-view.jpg" width="640" alt="The map view, the tab that opens the vessel filters ringed at the top of the screen">

On stock, the mouse on the top row of pixels does not reach the tab: the tab does not light up, and its
tooltip does not show. Ten pixels lower, both do.

<img src="imgs/why-a-click-at-the-top-matters/cursor-top-row.jpg" width="640" alt="The mouse on the top row of pixels, over the tab: no highlight, no tooltip">

<img src="imgs/why-a-click-at-the-top-matters/cursor-10-px-lower.jpg" width="640" alt="The mouse ten pixels lower, over the tab: the arrow lights up and the tooltip shows">

So a click on the top row does not open the row of filters. Worse, it toggles the filter whose hidden
button sits above the cursor, along the whole width of the row. Nothing on screen says so; those vessels
leave the map, and the player only finds out later, from the unchecked button, the next time the row is
open. Below, a click on the top row, left of the tab, then the row opened: the landers filter is off.

<img src="imgs/why-a-click-at-the-top-matters/click-top-row.jpg" width="640" alt="A click on the top row of pixels, left of the tab: the row of filters stays folded">

<img src="imgs/why-a-click-at-the-top-matters/row-opened-after.jpg" width="640" alt="The row of filters opened afterwards: the landers filter, right under the click, is off">

*KSP 1.12.5 without this mod, with [KSP Community Fixes](https://github.com/KSPModdingLibs/KSPCommunityFixes),
in French, in a 1280 × 720 window, in the map view of a flight on the launch pad. Screenshots do not show
the mouse cursor: it is drawn where it was. The four close-ups are cropped from the top of the screen and
zoomed twice. First, the mouse rests on the top row of pixels over the tab, then ten pixels lower, a
couple of seconds each. Then it is moved to the top row, 106 pixels left of the tab's centre, and clicked;
the row of filters is opened afterwards, the mouse away from it.*

## The culprit: the folded row keeps its buttons just above the screen

The row is a panel driven by `MapViewFiltering`, which slides between two positions with a
`UIPanelTransitionToggle`. Folded, the panel sits just above the screen, and its filter buttons
(`TrackingStationObjectButton`) stay where they are in it. The panel does not go quite far enough: the
lower edge of those buttons still reaches a few pixels into the screen. That edge is transparent, so
nothing shows, but a button takes clicks on its whole rectangle.

The tab is a sibling of those buttons, placed before them, so they are drawn over it and the user
interface hands them the click first. Over the tab and on either side of it, along the whole width of
the row, the top few pixels of the screen belong to filter buttons nobody can see.

## The fix: hidden buttons ignore clicks

One patch, with its own switch in [Settings](#settings), on by default. Nothing is saved; removing the
mod gives the stock behaviour back at once.

- **`foldedFiltersIgnoreClicks`.** After `MapViewFiltering.Start`, the mod gives each filter button a
  `CanvasGroup`, and turns off its `blocksRaycasts` while the panel rests folded. As soon as the panel
  moves, either way, the buttons take clicks again, as on stock. The tab itself is left alone: its
  clickable area already reaches the top edge of the screen.
- **How "folded" is told.** The panel's two positions are named `Out` for the folded one and `In` for the
  open one, so `UIPanelTransitionToggle.expanded` is true while the panel is folded. The mod does not use
  it: the folded position is the higher of the two, the one that hides the panel above the screen.
- **Why not move the panel further up.** It would change where the panel sits and how it slides, which
  other mods may rely on: KSP Community Fixes' `AltimeterHorizontalPosition` hides and shows this panel
  around the map view. Turning off the clicks of hidden buttons changes nothing that can be seen.

## Work in progress

The patch acts on the vessel filter panel wherever `MapViewFiltering` runs. Each point below is a place
where it changes what stock does, and so where it could break something. What you would see, and how to
check it by hand:

- **The tab and the filters, in the flight scene's map view.** The tab would not open, or a filter button
  of the open row would not respond. In the map view, throw the mouse against the top edge of the screen
  over the tab and click: the row opens, and every filter is as it was. Then click a filter of the open
  row, and right-click another (which shows that type alone): both respond. Close the row, and do it
  again without this mod: the click at the edge leaves the row folded, and the next time it is opened, a
  filter has changed.
- **The tracking station.** Its vessel filters may use the same panel. A filter button that would not
  respond there, or a click at the top edge that would still toggle a filter: open the tracking station,
  and play the same checks as in the map view, without this mod and with it.
- **KSP Community Fixes with the altimeter moved.** `AltimeterHorizontalPosition` hides the panel outside
  the map view when the altimeter is not at its stock position, and shows it again in the map view. A row
  that would not open, or a filter button that would not respond, after leaving the map view and coming
  back: move the altimeter in the pause menu settings, then play the map view checks again, leaving the
  map view and coming back between them.
- **Other screen sizes and interface scales.** How far the hidden buttons reach into the screen follows
  the size of the interface. Play the map view checks at another resolution, and with another interface
  scale in the settings.

## Install

Copy the `GameData\KSPFixMapFilter` folder into the `GameData` folder of KSP. It needs
[Harmony](https://github.com/KSPModdingLibs/HarmonyKSP), as KSP Community Fixes does.

## Settings

`GameData\KSPFixMapFilter\PluginData\settings.cfg` is read once, when KSP starts:

```
// Keeps the filter buttons of the map view's vessel filter panel from taking clicks while the panel is
// folded.
foldedFiltersIgnoreClicks = True

// How much the mod writes to KSP.log: Error, Warning, Info or Debug.
logLevel = Info
```

- With `foldedFiltersIgnoreClicks = False`, the filter buttons take clicks as on stock.
- At `Debug`, the mod writes one line to `KSP.log` every time the filter buttons start or stop ignoring
  clicks.

## Build

Set `KSPDIR` to the folder of a KSP install with Harmony in its `GameData`, then run `build.bat`: it
compiles `GameData\KSPFixMapFilter\KSPFixMapFilter.dll`. Installing is up to you.

## License

[MIT](LICENSE).
