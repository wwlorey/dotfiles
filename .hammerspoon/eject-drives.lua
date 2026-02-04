-- Ejects all external physical drives when the lid is closed

local function isLidClosed()
    local output = hs.execute("ioreg -r -k AppleClamshellState | grep AppleClamshellState | head -1")
    return output ~= nil and output:find("Yes") ~= nil
end

local lidWasClosed = isLidClosed()

local function ejectExternalPhysicalDrives()
    -- Get list of external physical disks
    local output, status = hs.execute("/usr/sbin/diskutil list external physical")
    if not status or output == "" then return end

    -- Extract and eject each external physical disk
    for line in output:gmatch("[^\n]+") do
        local disk = line:match("^/dev/(disk%d+)")
        if disk then
            -- Eject silently (fails immediately if busy, no waiting)
            hs.execute("/usr/sbin/diskutil eject " .. disk)
        end
    end

    -- Brief delay to ensure ejection completes before sleep
    hs.timer.usleep(500000) -- 500ms
end

local function checkLidAndEject()
    local lidIsClosed = isLidClosed()

    -- Eject on transition from open to closed
    if lidIsClosed and not lidWasClosed then
        ejectExternalPhysicalDrives()
    end

    lidWasClosed = lidIsClosed
end

-- Screen watcher: detects lid close in clamshell mode (external monitor connected)
lidScreenWatcher = hs.screen.watcher.new(checkLidAndEject)
lidScreenWatcher:start()

-- Caffeinate watcher: detects lid close when it triggers sleep
local function handleCaffeinateEvent(event)
    if event == hs.caffeinate.watcher.screensDidSleep or
       event == hs.caffeinate.watcher.systemWillSleep then
        checkLidAndEject()
    end
end

caffeinateWatcher = hs.caffeinate.watcher.new(handleCaffeinateEvent)
caffeinateWatcher:start()
