-- vigil.lua
-- Toggles macOS sleep/hibernation so the lid can be closed without sleeping.
-- All processes keep running; screen locks and dims normally.
-- Automatically re-enables sleep when the lid is opened.
--
-- Required one-time setup (prevents sudo password prompt):
--   echo "$(whoami) ALL=(ALL) NOPASSWD: /usr/bin/pmset" | sudo tee /etc/sudoers.d/pmset

local vigil = {}
local isActive = false

local menubar = hs.menubar.new()
local iconLit = hs.image.imageFromPath(hs.configdir .. "/vigil-lit.png"):setSize({w=16, h=16}):template(true)
local iconUnlit = hs.image.imageFromPath(hs.configdir .. "/vigil-unlit.png"):setSize({w=16, h=16}):template(true)

local function updateMenubar()
    if isActive then
        menubar:setIcon(iconLit)
        menubar:setTooltip("Vigil: On — Mac will stay awake")
    else
        menubar:setIcon(iconUnlit)
        menubar:setTooltip("Vigil: Off — Normal sleep")
    end
end

local function deactivate()
    hs.execute("sudo pmset -a disablesleep 0 && sudo pmset -a hibernatemode 3", true)
    isActive = false
    updateMenubar()
end

local function activate()
    hs.execute("sudo pmset -a disablesleep 1 && sudo pmset -a hibernatemode 0", true)
    isActive = true
    updateMenubar()
end

local watcher = hs.caffeinate.watcher.new(function(event)
    if event == hs.caffeinate.watcher.systemDidWake and isActive then
        deactivate()
    end
end)
watcher:start()

function vigil.toggle()
    if isActive then
        deactivate()
    else
        activate()
    end
end

menubar:setClickCallback(vigil.toggle)
deactivate()

hs.hotkey.bind({"ctrl", "cmd"}, "V", vigil.toggle)
