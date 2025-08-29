function dimLaptopScreenWhenExternalMonitorDetected()
    local screens = hs.screen.allScreens()
    local laptopScreen = nil
    
    -- Find the built-in display
    for _, screen in ipairs(screens) do
        if screen:name():find("Built%-in") or screen:name():find("Color LCD") then
            laptopScreen = screen
            break
        end
    end
    
    if laptopScreen then
        if #screens > 1 then
            laptopScreen:setBrightness(0)
        else
            laptopScreen:setBrightness(0.5)
        end
    end
end

screenWatcher = hs.screen.watcher.new(dimLaptopScreenWhenExternalMonitorDetected)
screenWatcher:start()

-- Run once on startup
dimLaptopScreenWhenExternalMonitorDetected()
