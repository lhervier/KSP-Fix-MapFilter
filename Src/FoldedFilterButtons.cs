using System.Collections.Generic;
using HarmonyLib;
using KSP.UI;
using UnityEngine;

namespace com.github.lhervier.ksp.fix.mapfilter
{
    /// <summary>
    /// Keeps the filter buttons of the map view's vessel filter panel from taking clicks while the panel rests
    /// folded, and lets them take clicks again as soon as it moves.
    ///
    /// Folded, the panel sits just above the screen, but the lower edge of its filter buttons still reaches a
    /// few pixels into it. That edge is transparent, so nothing shows, yet it takes the clicks, ahead of the
    /// tab that opens the panel: a click at the very top of the screen toggles a filter instead of opening the
    /// panel.
    /// </summary>
    internal class FoldedFilterButtons : MonoBehaviour
    {
        private MapViewFiltering filtering;

        // The state the panel rests in when folded: of its positions, the highest, out of the screen.
        private int foldedState;

        // One per filter button, added by this fix: turning off its blocksRaycasts makes the button ignore clicks.
        private List<CanvasGroup> groups;

        // Whether the buttons take clicks, as last set; null before the first frame.
        private bool? takeClicks;

        /// <summary>Patches MapViewFiltering.Start with <see cref="Postfix"/>.</summary>
        public static void Install(Harmony harmony)
        {
            var target = AccessTools.Method(typeof(MapViewFiltering), "Start");
            harmony.Patch(target, postfix: new HarmonyMethod(typeof(FoldedFilterButtons), nameof(Postfix)));
        }

        /// <summary>Puts this fix on the filter panel of <paramref name="__instance"/>, once stock has set it up.</summary>
        private static void Postfix(MapViewFiltering __instance)
        {
            if (__instance.GetComponent<FoldedFilterButtons>() == null)
            {
                __instance.gameObject.AddComponent<FoldedFilterButtons>().Init(__instance);
            }
        }

        /// <summary>
        /// Prepares the fix for the filter panel of <paramref name="mapViewFiltering"/>. Removes itself, leaving
        /// the filters as on stock, when they do not fold (the tracking station's) or when the panel does not
        /// have the shape it expects: two positions or more, and filter buttons.
        /// </summary>
        private void Init(MapViewFiltering mapViewFiltering)
        {
            filtering = mapViewFiltering;
            if (filtering.panel == null)
            {
                Log.Debug("These vessel filters do not fold, nothing to fix");
                Destroy(this);
                return;
            }
            UIPanelTransition.PanelPosition[] states = filtering.panel.states;
            if (states == null || states.Length < 2 || filtering.FilterButtons == null)
            {
                Log.Warning("The vessel filter panel does not have the expected positions or buttons, it is left as on stock");
                Destroy(this);
                return;
            }

            // Stock names the folded position "Out" and the open one "In", so UIPanelTransitionToggle.expanded is
            // true while the panel is folded: the folded state is told by its height instead.
            foldedState = 0;
            for (int i = 1; i < states.Length; i++)
            {
                if (states[i].position.y > states[foldedState].position.y)
                {
                    foldedState = i;
                }
            }

            groups = new List<CanvasGroup>();
            foreach (MapViewFiltering.FilterButton filterButton in filtering.FilterButtons)
            {
                if (filterButton == null || filterButton.button == null)
                {
                    continue;
                }
                GameObject buttonObject = filterButton.button.gameObject;
                CanvasGroup group = buttonObject.GetComponent<CanvasGroup>();
                if (group == null)
                {
                    group = buttonObject.AddComponent<CanvasGroup>();
                }
                groups.Add(group);
            }
            Log.Debug($"Watching the vessel filter panel: {groups.Count} filter buttons, folded in its position " +
                $"'{states[foldedState].name}'");
        }

        private void LateUpdate()
        {
            UIPanelTransitionToggle panel = filtering != null ? filtering.panel : null;
            if (panel == null || groups == null)
            {
                return;
            }
            // StateIndex changes when the panel starts to move: while it slides, either way, the buttons stay
            // as on stock.
            bool take = panel.StateIndex != foldedState || panel.Transitioning;
            if (take == takeClicks)
            {
                return;
            }
            takeClicks = take;
            foreach (CanvasGroup group in groups)
            {
                if (group != null)
                {
                    group.blocksRaycasts = take;
                }
            }
            Log.Debug(take ? "Vessel filter panel moving or open, its filter buttons take clicks"
                : "Vessel filter panel folded, its filter buttons ignore clicks");
        }
    }
}
