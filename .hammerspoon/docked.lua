function dimMacBookScreenWhenExternalMonitorDetected()
    local screens = hs.screen.allScreens()

    if #screens > 1 then
        hs.osascript.applescript([[
            tell application "System Events"
                repeat 20 times
                    key code 107
                end repeat
            end tell
        ]])
    else
        -- First dim all the way down, then bring back up to ~50%
        hs.osascript.applescript([[
            tell application "System Events"
                repeat 20 times
                    key code 107  -- brightness down
                end repeat
                repeat 10 times
                    key code 113  -- brightness up
                end repeat
            end tell
        ]])
    end
end

screenWatcher = hs.screen.watcher.new(dimMacBookScreenWhenExternalMonitorDetected)
screenWatcher:start()

-- Run once on startup
dimMacBookScreenWhenExternalMonitorDetected()
