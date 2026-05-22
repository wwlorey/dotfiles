local RESTORE_BRIGHTNESS = 0.5
local previousDocked = nil

function dimLaptopScreenWhenExternalMonitorDetected()
    local screens = hs.screen.allScreens()
    local laptopScreen = nil

    for _, screen in ipairs(screens) do
        if screen:name():find("Built%-in") or screen:name():find("Color LCD") then
            laptopScreen = screen
            break
        end
    end

    if not laptopScreen then return end

    local docked = #screens > 1
    if docked == previousDocked then return end

    if docked then
        laptopScreen:setBrightness(0)
    elseif previousDocked == true then
        laptopScreen:setBrightness(RESTORE_BRIGHTNESS)
    end

    previousDocked = docked
end

screenWatcher = hs.screen.watcher.new(dimLaptopScreenWhenExternalMonitorDetected)
screenWatcher:start()

dimLaptopScreenWhenExternalMonitorDetected()
