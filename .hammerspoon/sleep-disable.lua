-- sleep-disable.lua
-- Toggles macOS sleep/hibernation so the lid can be closed without sleeping.
-- All processes keep running; screen locks and dims normally.
-- Automatically re-enables sleep when the lid is opened.
--
-- Required one-time setup (prevents sudo password prompt):
--   echo "$(whoami) ALL=(ALL) NOPASSWD: /usr/bin/pmset" | sudo tee /etc/sudoers.d/pmset

local sleepDisable = {}
local isEnabled = false

local function disable()
    hs.execute("sudo pmset -a disablesleep 0 && sudo pmset -a hibernatemode 3", true)
    hs.notify.new({title="Sleep Disable", informativeText="Disabled (NORMAL)"}):send()
    isEnabled = false
end

local function enable()
    hs.execute("sudo pmset -a disablesleep 1 && sudo pmset -a hibernatemode 0", true)
    hs.notify.new({title="Sleep Disable", informativeText="Enabled (WILL NOT SLEEP)"}):send()
    isEnabled = true
end

local watcher = hs.caffeinate.watcher.new(function(event)
    if event == hs.caffeinate.watcher.systemDidWake and isEnabled then
        disable()
    end
end)
watcher:start()

function sleepDisable.toggle()
    if isEnabled then
        disable()
    else
        enable()
    end
end

hs.hotkey.bind({"ctrl", "cmd"}, "S", sleepDisable.toggle)
