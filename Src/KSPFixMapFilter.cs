using System;
using HarmonyLib;
using UnityEngine;

namespace com.github.lhervier.ksp.fix.mapfilter
{
    /// <summary>
    /// Installs the fix the settings turn on, once, when KSP starts: from then on, a click at the very top of
    /// the map view reaches the tab that opens the vessel filters, and no longer a hidden filter button.
    /// </summary>
    [KSPAddon(KSPAddon.Startup.Instantly, true)]
    public class KSPFixMapFilter : MonoBehaviour
    {
        private const string HarmonyId = "com.github.lhervier.ksp.fix.mapfilter";

        private void Start()
        {
            Settings.Load();
            Log.Info($"Version {typeof(KSPFixMapFilter).Assembly.GetName().Version}, " +
                $"foldedFiltersIgnoreClicks {Settings.FoldedFiltersIgnoreClicks}, log level {Log.Level}");
            if (!Settings.FoldedFiltersIgnoreClicks)
            {
                return;
            }
            try
            {
                FoldedFilterButtons.Install(new Harmony(HarmonyId));
                Log.Info("Folded filters fix installed");
            }
            catch (Exception e)
            {
                Log.Error($"Could not install the folded filters fix, the filter buttons take clicks as on stock: {e}");
            }
        }
    }
}
