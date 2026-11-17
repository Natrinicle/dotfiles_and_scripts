var windows = workspace.windowList();
var rows = [];
for (var i = 0; i < windows.length; i++) {
    var w = windows[i];
    var uuid = "";
    try {
        uuid = String(w.internalId);
    } catch (e) {
        uuid = "";
    }
    rows.push({
        uuid: uuid,
        caption: String(w.caption),
        resourceClass: String(w.resourceClass),
        resourceName: String(w.resourceName),
        desktopFileName: String(w.desktopFileName || ""),
        skipTaskbar: !!w.skipTaskbar,
        minimized: !!w.minimized,
        fullscreen: !!w.fullScreen,
        width: w.width,
        height: w.height
    });
}
callDBus("BUS_NAME_PLACEHOLDER", "/Dump", "org.screenshotwindow.dump", "Push", JSON.stringify(rows));
