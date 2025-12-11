local lockHotkey = nil
local sleepPreventionActive = false

local function notify(msg)
    hs.alert.show(msg, 1.8)
end

local function toggleLockAndKeepAwake()
    -- === CANCEL MODE (pressed again) ===
    if sleepPreventionActive then
        hs.caffeinate.set("system", false)
        sleepPreventionActive = false
        notify("Cancelled Lock & Keep Awake")
        return
    end

    -- === ACTIVATE MODE ===
    hs.caffeinate.set("system", true) -- prevent full system sleep
    sleepPreventionActive = true

    notify("Activating Lock & Keep Awake")

    hs.timer.doAfter(1.9, function()
        if sleepPreventionActive then
            hs.caffeinate.lockScreen() -- require password
        end
    end)
end

-- Hotkey
lockHotkey = hs.hotkey.new({"alt", "cmd"}, "Q", toggleLockAndKeepAwake)
lockHotkey:enable()

-- When you unlock with your password → restore brightness + normal sleep behaviour
local watcher = hs.caffeinate.watcher.new(function(event)
    if event == hs.caffeinate.watcher.screensDidUnlock and sleepPreventionActive then
        hs.caffeinate.set("system", false)
        sleepPreventionActive = false
        notify("Deactivated Lock & Keep Awake")
    end
end)
watcher:start()

-- Safety on reload
hs.caffeinate.set("system", false)
if sleepPreventionActive then displayRestore() end

print("Lock & Keep Awake loaded")
